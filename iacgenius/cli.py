import click
import json
import os
import sys
from iacgenius.config_handler import update_defaults, get_default, read_config
from iacgenius.exceptions import ConfigError # Import from exceptions module
from iacgenius.generator import generate_infrastructure
# Corrected imports based on usage
from iacgenius.infrastructure import get_infrastructure_types, get_file_extension
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
@click.option('--provider', help='Default LLM provider (deepseek/openai/anthropic)')
@click.option('--model', help='Model name for the provider')
@click.option('--api-key', prompt=True, hide_input=True,
              help='API key for the LLM provider (or set DEEPSEEK_API_KEY environment variable)')
def set(provider, model, api_key):
    """Set configuration values"""
    try:
        updates = {}
        if provider:
            updates['provider'] = provider
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
            # Read the actual config instead of hardcoding defaults here
            config_data = read_config()
            defaults = config_data.get("defaults", {})
            # Ensure essential keys exist even if not in config
            defaults['provider'] = defaults.get('provider', 'deepseek')
            defaults['model'] = defaults.get('model', 'deepseek-chat')
            defaults['api_key'] = defaults.get('api_key', None) # Display None if not set

            for k, v in defaults.items():
                # Display API key securely if needed, or just indicate if set
                display_v = '********' if k == 'api_key' and v else v
                click.echo(f"{k}: {display_v}")
    except ConfigError as e:
        click.echo(f"Error reading config: {str(e)}", err=True)
    except Exception as e: # Catch potential errors during read_config itself
        click.echo(f"An unexpected error occurred reading config: {str(e)}", err=True)


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

        # Set default model for DeepSeek if not specified (adjust if needed based on config structure)
        if llm_provider == "deepseek" and not model:
             # Check config.toml structure if this default is still appropriate
             # Assuming config_handler provides a sensible default if model is None
             # Let generate_infrastructure handle model defaults if None
             pass # Keep pass for now as placeholder, but could be removed if no logic needed

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
                infra_type = infra_types[type_choice - 1]
            elif infra_types: # Check if list is not empty
                click.echo(f"Invalid selection. Please enter a number between 1 and {len(infra_types)}.", err=True)
                # Exit or re-prompt? For now, default to Terraform.
                click.echo("Defaulting to Terraform.")
                infra_type = "Terraform" # Or handle error more strictly
            else:
                click.echo("Error: No infrastructure types found.", err=True)
                return # Exit if no types are available

        # Advanced options handling
        region = None
        tags = None
        temperature = 0.2 # Default temperature
        max_tokens = 2048 # Default max tokens

        if advanced:
            # Show advanced options if requested
            click.echo("\nAdvanced Options:")

            # LLM provider selection
            providers = get_available_providers() # Use backend function
            click.echo("\nAvailable LLM providers:")
            for i, provider_name in enumerate(providers, 1):
                click.echo(f"{i}. {provider_name}")
            # Try to find current default provider in list for prompt default
            current_provider_index = providers.index(llm_provider) + 1 if llm_provider in providers else 1
            provider_choice_str = click.prompt("Select LLM provider (number)", type=str, default=str(current_provider_index))
            try:
                provider_choice = int(provider_choice_str)
                if 1 <= provider_choice <= len(providers):
                    llm_provider = providers[provider_choice - 1] # Update llm_provider based on choice
                else:
                    click.echo(f"Invalid provider number. Using default: {llm_provider}", err=True)
            except ValueError:
                 click.echo(f"Invalid input. Using default provider: {llm_provider}", err=True)

            # Model selection based on chosen provider
            models = get_available_models(llm_provider) # Use backend function
            if models:
                click.echo(f"\nAvailable models for {llm_provider}:")
                for i, model_name in enumerate(models, 1):
                    click.echo(f"{i}. {model_name}")
                # Try to find current model in list for default prompt index
                # If the chosen provider changed, the old 'model' might be invalid, default to first
                current_model_index = models.index(model) + 1 if model and model in models else 1 # Check if model exists before indexing
                model_choice_str = click.prompt("Select model (number)", type=str, default=str(current_model_index))
                try:
                    model_choice = int(model_choice_str)
                    if 1 <= model_choice <= len(models):
                        model = models[model_choice - 1] # Update model based on choice
                    else:
                        click.echo(f"Invalid model number. Using previously determined model: {model}", err=True)
                except ValueError:
                    click.echo(f"Invalid input. Using previously determined model: {model}", err=True)
            else:
                 click.echo(f"No specific models listed for {llm_provider}. Using default or configured model.")
                 # Model remains as determined from config or default logic

            # Additional parameters
            region = click.prompt("Cloud region (e.g., us-east-1, eastus)", default="", show_default=False)
            if not region:
                region = None

            tags_input = click.prompt("Resource tags (key=value format, separated by commas)", default="", show_default=False)
            if tags_input:
                # Simple split, assumes user provides comma-separated key=value pairs
                # More robust parsing could be added if needed
                tags = '\n'.join(tag.strip() for tag in tags_input.split(','))
            else:
                tags = None

            temperature = click.prompt("Temperature (0.0-1.0)", type=float, default=temperature)
            max_tokens = click.prompt("Max tokens", type=int, default=max_tokens)

        # Get API key from environment (generate_infrastructure also checks this)
        # We pass None here and let generate_infrastructure handle API key logic
        api_key = None

        click.echo(f"\nGenerating {infra_type} for cloud provider {provider} using {llm_provider}...")

        # Call the central generator function
        result_json_str = generate_infrastructure(
            description=description,
            iac_type=infra_type,
            cloud_provider=provider, # Original 'provider' variable from click option
            llm_provider=llm_provider, # Determined provider (default or from advanced prompt)
            model=model,               # Determined model (default or from advanced prompt)
            api_key=api_key,           # Pass None, let backend handle env vars/config
            temperature=temperature,
            max_tokens=max_tokens,
            region=region,
            tags=tags
        )
        result_data = json.loads(result_json_str)
        generated_code = result_data.get("code", "")

        # Output the generated code
        if not output:
            click.echo("\nGenerated Code:")
            click.echo("---------------")
            click.echo(generated_code)
        else:
            # Use appropriate file extension based on infrastructure type
            final_output_path = output
            if not any(output.lower().endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego', 'dockerfile']):
                final_output_path = f"{output}{get_file_extension(infra_type)}" # Use backend function

            with open(final_output_path, 'w') as f:
                f.write(generated_code)
            click.echo(f"Code written to {final_output_path}")

        # --- Interactive Modification Loop ---
        while True:
            click.echo("\nWhat would you like to do next?")
            click.echo("1. Modify the code")
            click.echo("2. Save code to a file") # Only prompts if not saved via -o
            click.echo("3. Quit")
            choice = click.prompt("Enter your choice (1-3)", type=int, default=3)

            if choice == 1: # Modify
                modification_request = click.prompt("Describe the modifications you want")
                description += f"\n\nModification request: {modification_request}" # Append modification to description
                click.echo(f"\nRegenerating {infra_type} with modifications...")
                # Call the generator again with the updated description
                result_json_str = generate_infrastructure(
                    description=description,
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
                result_data = json.loads(result_json_str)
                generated_code = result_data.get("code", "")

                # Display the newly generated code
                click.echo("\nUpdated Generated Code:")
                click.echo("---------------")
                click.echo(generated_code)
                # Reset output flag so saving is possible again if needed
                output = None # Allow saving the modified code
                final_output_path = None # Reset path

            elif choice == 2: # Save
                if output: # If -o was used initially
                     click.echo(f"Code was already saved to {final_output_path}. Use 'Modify' to regenerate if needed.")
                     continue # Go back to prompt

                # Prompt for filename if not saved via -o or after modification
                suggested_filename = f"iacgenius_{infra_type.lower().replace(' ', '_').replace('(', '').replace(')', '')}{get_file_extension(infra_type)}"
                output_path_save = click.prompt("Enter filename to save", default=suggested_filename)
                if not any(output_path_save.lower().endswith(ext) for ext in ['.tf', '.yaml', '.yml', '.json', '.rego', 'dockerfile']):
                     output_path_save = f"{output_path_save}{get_file_extension(infra_type)}"
                with open(output_path_save, 'w') as f:
                     f.write(generated_code)
                click.echo(f"Code written to {output_path_save}")
                output = output_path_save # Mark as saved
                final_output_path = output_path_save # Update path

            elif choice == 3: # Quit
                break # Exit the loop
            else:
                click.echo("Invalid choice. Please enter a number between 1 and 3.", err=True)
        # --- End Interactive Modification Loop ---

    except ConfigError as e:
         click.echo(f"Configuration Error: {e}", err=True)
    except Exception as e:
        click.echo(f"Error generating infrastructure: {str(e)}", err=True)
        # Consider adding more specific exception handling or logging if needed


@cli.command()
def run():
    """Run the Streamlit web interface"""
    import subprocess
    # Ensure streamlit_app.py is found relative to the script or package
    script_dir = os.path.dirname(__file__)
    app_path = os.path.join(script_dir, '..', 'streamlit_app.py') # Go up one level from iacgenius dir
    if not os.path.exists(app_path):
         # Fallback if running from a different structure
         app_path = 'streamlit_app.py'
         if not os.path.exists(app_path):
              click.echo("Error: streamlit_app.py not found.", err=True)
              sys.exit(1)

    subprocess.run([sys.executable, "-m", "streamlit", "run", app_path])

# Removed custom help command to rely on Click's default help generation
# Users can now run `iacgenius --help`, `iacgenius generate --help`, etc.

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

# Removed the 'quick' command as 'generate' handles its functionality

if __name__ == "__main__":
    cli()
