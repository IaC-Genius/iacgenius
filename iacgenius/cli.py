import click
import json
import os
from iacgenius.config_handler import update_defaults, get_default, ConfigError, read_config
from iacgenius.generator import generate_infrastructure
from iacgenius.infrastructure import get_infrastructure_types, get_file_extension, create_prompt_template
from iacgenius.llm_integration import get_available_providers, get_available_models

@click.group()
def cli():
    """IACGenius CLI - Infrastructure as Code Generation Tool"""
    pass

@cli.group()
def config():
    """Manage configuration settings"""
    pass

@config.command()
@click.option('--provider', help='Default LLM provider (deepseek/openai/anthropic/openrouter)')
@click.option('--model', help='Model name for the provider')
@click.option('--api-key', prompt=True, hide_input=True, help='API key for the LLM provider (or set DEEPSEEK_API_KEY environment variable)')
def set(provider, model, api_key):
    """Set configuration values"""
    try:
        updates = {}
        if provider:
            provider_lower = provider.lower()
            available_providers = get_available_providers()
            if provider_lower not in available_providers:
                raise ConfigError(f"Invalid provider: {provider}. Available providers: {', '.join(available_providers)}")
            updates['provider'] = provider_lower
        if model:
            updates['model'] = model
        if api_key:
            updates['api_key'] = api_key

        update_defaults(**updates)
        click.echo("Configuration updated successfully!")
    except ConfigError as e:
        click.echo(f"Error updating config: {str(e)}", err=True)

@config.command()
@click.argument('key', required=False)
def get(key):
    """Get configuration values"""
    try:
        if key:
            value = get_default(key)
            click.echo(f"{key}: {value or 'Not set'}")
        else:
            config = get_default(None) or {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": None
            }
            for k, v in config.items():
                click.echo(f"{k}: {v}")
    except ConfigError as e:
        click.echo(f"Error reading config: {str(e)}", err=True)

@cli.command()
@click.option('--description', '-d', help='Description of the infrastructure to generate')
@click.option('--type', '-t', 'infra_type', help='Infrastructure type (Terraform, CloudFormation, Kubernetes, etc.)')
@click.option('--provider', '-p', help='Cloud provider (AWS, Azure, GCP, etc.)', default='AWS')
@click.option('--output', '-o', help='Output file path')
@click.option('--advanced', is_flag=True, help='Show advanced options')
def generate(description, infra_type, provider, output, advanced):
    """Generate infrastructure as code

    Examples:
      iacgenius generate -d "Create an S3 bucket with versioning enabled" -t Terraform
      iacgenius generate  # Interactive mode with prompts
    """
    try:
        # Get configuration
        config = read_config()

        # Use defaults from config
        llm_provider = config.get("defaults", {}).get("provider", "deepseek")
        model = config.get("defaults", {}).get("model")

        # Set default model for DeepSeek if not specified
        if llm_provider == "deepseek" and not model:
            model = "deepseek-chat"

        # Interactive mode if required parameters are missing
        if not description:
            description = click.prompt("Describe the infrastructure you want to generate")

        if not infra_type:
            # Get available infrastructure types
            infra_types = get_infrastructure_types()
            # Display available types with numbers
            click.echo("Available infrastructure types:")
            for i, type_name in enumerate(infra_types, 1):
                click.echo(f"{i}. {type_name}")
            # Prompt for selection
            type_choice = click.prompt("Select infrastructure type (number)", type=int, default=1)
            # Validate choice
            if 1 <= type_choice <= len(infra_types):
                infra_type = infra_types[type_choice-1]
            else:
                click.echo("Invalid selection, using default (Terraform)")
                infra_type = "Terraform"

        # Advanced options
        region = None
        tags = None
        temperature = 0.2
        max_tokens = 2048

        if advanced:
            # Show advanced options if requested
            click.echo("\nAdvanced Options:")

            # LLM provider selection
            providers = get_available_providers()
            click.echo("\nAvailable LLM providers:")
            for i, provider_name in enumerate(providers, 1):
                click.echo(f"{i}. {provider_name}")
            provider_choice = click.prompt("Select LLM provider (number)", type=int, default=providers.index(llm_provider)+1 if llm_provider in providers else 1)
            if 1 <= provider_choice <= len(providers):
                llm_provider = providers[provider_choice-1]

            # Model selection based on provider
            models = get_available_models(llm_provider)
            if models:
                click.echo(f"\nAvailable models for {llm_provider}:")
                for i, model_name in enumerate(models, 1):
                    click.echo(f"{i}. {model_name}")
                model_choice = click.prompt("Select model (number)", type=int, default=1)
                if 1 <= model_choice <= len(models):
                    model = models[model_choice-1]

            # Additional parameters
            region = click.prompt("Cloud region (e.g., us-east-1, eastus)", default="")
            if not region:
                region = None

            tags_input = click.prompt("Resource tags (key=value format, separated by commas)", default="")
            if tags_input:
                tags = '\n'.join(tags_input.split(','))

            temperature = click.prompt("Temperature (0.0-1.0)", type=float, default=0.2)
            max_tokens = click.prompt("Max tokens", type=int, default=2048)

        # Get API key from environment
        api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY") if llm_provider else None

        click.echo(f"\nGenerating {infra_type} for cloud provider {provider} using {llm_provider}...")

        # Generate the infrastructure code
        result = generate_infrastructure(
            description,
            iac_type=infra_type,
            cloud_provider=provider,
            llm_provider=llm_provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            region=region,
            tags=tags
        )
        result_json = json.loads(result)

        # Store the generated code and metadata for potential regeneration
        generated_code = result_json['code']
        # Metadata kept for potential future use
        _ = {
            "description": description,
            "iac_type": infra_type,
            "cloud_provider": provider,
            "llm_provider": llm_provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "region": region,
            "tags": tags
        }

        # Output the generated code
        if not output:
            click.echo("\nGenerated Code:")
            click.echo("---------------")
            click.echo(generated_code)
        else:
            # Use appropriate file extension based on infrastructure type
            if not any(output.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                output = f"{output}{get_file_extension(infra_type)}"

            with open(output, 'w') as f:
                f.write(generated_code)
            click.echo(f"Code written to {output}")

        # Provide post-generation options
        click.echo("\nWhat would you like to do next?")
        click.echo("1. Save code to a file")
        click.echo("2. Modify code with feedback")
        click.echo("3. Quit")

        choice = click.prompt("Enter your choice (1-3)", type=int, default=3)

        if choice == 1:
            # Option 1: Save to file
            if output:
                click.echo(f"Code already saved to {output}")
            else:
                suggested_filename = f"iacgenius_{infra_type.lower().replace(' ', '_')}{get_file_extension(infra_type)}"
                output_path = click.prompt("Enter filename", default=suggested_filename)

                # Use appropriate file extension based on infrastructure type
                if not any(output_path.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                    output_path = f"{output_path}{get_file_extension(infra_type)}"

                with open(output_path, 'w') as f:
                    f.write(generated_code)
                click.echo(f"Code written to {output_path}")

        elif choice == 2:
            # Option 2: Modify with feedback
            feedback = click.prompt("Please provide feedback on what to modify in the generated code")

            # Create a new prompt that includes the original code and feedback
            feedback_prompt = f"""
{create_prompt_template(infra_type, description, provider, region, tags)}

Previously generated code:
```
{generated_code}
```

User feedback for modifications:
{feedback}

Please provide an updated version of the code that addresses this feedback.
"""

            click.echo(f"\nRegenerating {infra_type} code based on your feedback...")

            # Generate updated code using the same parameters but with feedback
            updated_result = generate_infrastructure(
                feedback_prompt,
                iac_type=infra_type,
                cloud_provider=provider,
                llm_provider=llm_provider,
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                region=region,
                tags=tags
            )
            updated_result_json = json.loads(updated_result)
            updated_code = updated_result_json['code']

            click.echo("\nUpdated Code:")
            click.echo("---------------")
            click.echo(updated_code)

            # Ask if they want to save the updated code
            if click.confirm("Would you like to save this updated code?", default=True):
                suggested_filename = f"iacgenius_{infra_type.lower().replace(' ', '_')}_updated{get_file_extension(infra_type)}"
                output_path = click.prompt("Enter filename", default=suggested_filename)

                # Use appropriate file extension based on infrastructure type
                if not any(output_path.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                    output_path = f"{output_path}{get_file_extension(infra_type)}"

                with open(output_path, 'w') as f:
                    f.write(updated_code)
                click.echo(f"Updated code written to {output_path}")

        # Option 3: Quit (default, no action needed)

    except Exception as e:
        click.echo(f"Error generating infrastructure: {str(e)}", err=True)

@cli.command()
def run():
    """Run the Streamlit web interface"""
    import subprocess
    subprocess.run(["streamlit", "run", "streamlit_app.py"])

@cli.command()
def help():
    """Show detailed help and examples"""
    help_text = """
IACGenius - AI-Powered Infrastructure as Code Generator

Getting Started:
  1. Set your API key:     iacgenius config set --api-key YOUR_API_KEY
  2. Quick generation:     iacgenius quick "Create an S3 bucket with versioning"
  3. Interactive mode:     iacgenius generate
  4. Web interface:        iacgenius run

Commands:
  quick DESCRIPTION        Generate code with minimal parameters
  generate                 Generate code with interactive prompts
  config set               Configure default settings
  config get               View current configuration
  list-types               List supported infrastructure types
  run                      Launch the web interface
  help                     Show this help message

Examples:
  # Quick generation with default settings (Terraform/AWS)
  iacgenius quick "Create a Lambda function that processes S3 events"

  # Generate with specific infrastructure type
  iacgenius quick "Create a web application deployment" --type "Kubernetes (Manifests)"

  # Interactive generation with advanced options
  iacgenius generate --advanced

  # Save output to file
  iacgenius quick "Create an EC2 instance with security groups" --output my-infra

  # Set default LLM provider
  iacgenius config set --provider openai --model gpt-4-turbo

Environment Variables:
  DEEPSEEK_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY, OPENROUTER_API_KEY
  Set these to avoid entering API keys manually
"""
    click.echo(help_text)

@cli.command()
def list_types():
    """List supported infrastructure types"""
    try:
        infra_types = get_infrastructure_types()
        click.echo("Supported infrastructure types:")
        for infra_type in infra_types:
            click.echo(f"- {infra_type}")
    except Exception as e:
        click.echo(f"Error listing infrastructure types: {str(e)}", err=True)

@cli.command()
@click.argument('description')
@click.option('--type', '-t', default='Terraform', help='Infrastructure type (default: Terraform)')
@click.option('--output', '-o', help='Output file path')
def quick(description, type, output):
    """Quick generation with minimal parameters

    Example: iacgenius quick "Create an S3 bucket with versioning enabled"
    """
    try:
        # Get configuration
        config = read_config()

        # Use defaults for everything except description and type
        llm_provider = config.get("defaults", {}).get("provider", "deepseek")
        model = config.get("defaults", {}).get("model")
        provider = "AWS"  # Default cloud provider

        # Set default model if not specified
        if llm_provider == "deepseek" and not model:
            model = "deepseek-coder-33b-instruct"

        # Get API key from environment
        api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY") if llm_provider else None

        click.echo(f"Generating {type} for cloud provider {provider} using {llm_provider}...")

        # Default values for advanced parameters
        region = None
        tags = None
        temperature = 0.2
        max_tokens = 2048

        # Generate the infrastructure code with minimal parameters
        result = generate_infrastructure(
            description,
            iac_type=type,
            cloud_provider=provider,
            llm_provider=llm_provider,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens
        )
        result_json = json.loads(result)

        # Store the generated code and metadata for potential regeneration
        generated_code = result_json['code']
        # Metadata kept for potential future use
        _ = {
            "description": description,
            "iac_type": type,
            "cloud_provider": provider,
            "llm_provider": llm_provider,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "region": region,
            "tags": tags
        }

        # Output the generated code
        if not output:
            click.echo("\nGenerated Code:")
            click.echo("---------------")
            click.echo(generated_code)
        else:
            # Use appropriate file extension based on infrastructure type
            if not any(output.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                output = f"{output}{get_file_extension(type)}"

            with open(output, 'w') as f:
                f.write(generated_code)
            click.echo(f"Code written to {output}")

        # Provide post-generation options
        click.echo("\nWhat would you like to do next?")
        click.echo("1. Save code to a file")
        click.echo("2. Modify code with feedback")
        click.echo("3. Quit")

        choice = click.prompt("Enter your choice (1-3)", type=int, default=3)

        if choice == 1:
            # Option 1: Save to file
            if output:
                click.echo(f"Code already saved to {output}")
            else:
                suggested_filename = f"iacgenius_{type.lower().replace(' ', '_')}{get_file_extension(type)}"
                output_path = click.prompt("Enter filename", default=suggested_filename)

                # Use appropriate file extension based on infrastructure type
                if not any(output_path.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                    output_path = f"{output_path}{get_file_extension(type)}"

                with open(output_path, 'w') as f:
                    f.write(generated_code)
                click.echo(f"Code written to {output_path}")

        elif choice == 2:
            # Option 2: Modify with feedback
            feedback = click.prompt("Please provide feedback on what to modify in the generated code")

            # Create a new prompt that includes the original code and feedback
            feedback_prompt = f"""
{create_prompt_template(type, description, provider, region, tags)}

Previously generated code:
```
{generated_code}
```

User feedback for modifications:
{feedback}

Please provide an updated version of the code that addresses this feedback.
"""

            click.echo(f"\nRegenerating {type} code based on your feedback...")

            # Generate updated code using the same parameters but with feedback
            updated_result = generate_infrastructure(
                feedback_prompt,
                iac_type=type,
                cloud_provider=provider,
                llm_provider=llm_provider,
                model=model,
                api_key=api_key,
                temperature=temperature,
                max_tokens=max_tokens,
                region=region,
                tags=tags
            )
            updated_result_json = json.loads(updated_result)
            updated_code = updated_result_json['code']

            click.echo("\nUpdated Code:")
            click.echo("---------------")
            click.echo(updated_code)

            # Ask if they want to save the updated code
            if click.confirm("Would you like to save this updated code?", default=True):
                suggested_filename = f"iacgenius_{type.lower().replace(' ', '_')}_updated{get_file_extension(type)}"
                output_path = click.prompt("Enter filename", default=suggested_filename)

                # Use appropriate file extension based on infrastructure type
                if not any(output_path.endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego']):
                    output_path = f"{output_path}{get_file_extension(type)}"

                with open(output_path, 'w') as f:
                    f.write(updated_code)
                click.echo(f"Updated code written to {output_path}")

        # Option 3: Quit (default, no action needed)

    except Exception as e:
        click.echo(f"Error generating infrastructure: {str(e)}", err=True)

if __name__ == "__main__":
    cli()
