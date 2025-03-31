from iacgenius.config_handler import read_config
from iacgenius.exceptions import ConfigError # Import from exceptions module
from iacgenius.llm_integration import generate_with_provider
from iacgenius.infrastructure import create_prompt_template
import json
import os
from typing import Optional # Import Optional

def generate_infrastructure(description: str, iac_type: str, cloud_provider: Optional[str] = None,
                           llm_provider: Optional[str] = None, model: Optional[str] = None,
                           api_key: Optional[str] = None, temperature: float = 0.2, max_tokens: int = 2048,
                           region: Optional[str] = None, tags: Optional[str] = None,
                           target_versions: Optional[str] = None): # Added target_versions parameter
    """Core infrastructure generation logic shared by CLI and Streamlit"""
    # Read config which handles defaults, env vars, and decryption
    config = read_config()
    defaults = config.get("defaults", {})

    # Determine parameters, prioritizing function args > config defaults
    final_llm_provider = llm_provider or defaults.get("provider", "deepseek")
    # Use model from args, or config, or specific default if provider is deepseek and no model found
    final_model = model or defaults.get("model")
    if final_llm_provider == "deepseek" and not final_model:
        final_model = "deepseek-chat" # Match default in config_handler
    elif not final_model:
         # If no model specified via arg or config, raise error? Or let the API handle it?
         # For now, let llm_integration handle potential errors if model is None for other providers
         pass

    final_cloud_provider = cloud_provider or "AWS" # Default cloud provider if not specified

    # API key is now handled by read_config(), use the value from there
    final_api_key = api_key if api_key is not None else defaults.get("api_key") # Prioritize passed key

    # Validate that we have an API key if the provider requires one
    # (llm_integration might also do this, but good to check early)
    providers_requiring_keys = ["openai", "anthropic", "deepseek", "openrouter"] # Add others as needed
    if final_llm_provider in providers_requiring_keys and not final_api_key:
        raise ConfigError(f"API key for provider '{final_llm_provider}' is required but not found in arguments, config, or environment variables.")

    # Create a detailed prompt using the infrastructure module, passing target_versions
    prompt = create_prompt_template(iac_type, description, final_cloud_provider, region, tags, target_versions)

    try:
        # Always use the provider-based generation function
        generated_code = generate_with_provider(
            provider_name=final_llm_provider,
            prompt=prompt,
            model=final_model,
            api_key=final_api_key, # Use the key determined above
            temperature=temperature,
            max_tokens=max_tokens
        )

        # Basic validation: Check if generated code is empty or just whitespace
        if not generated_code or generated_code.isspace():
             # Consider raising an error or returning a specific status
             print(f"Warning: LLM provider '{final_llm_provider}' returned empty code for the prompt.")
             # Optionally, return an error structure or raise exception
             # For now, return the empty code as received

        return json.dumps({
            "description": description,
            "type": iac_type,
            "cloud_provider": final_cloud_provider,
            "llm_provider": final_llm_provider,
            "model": final_model,
            "code": generated_code.strip() # Strip potential leading/trailing whitespace from LLM output
        }, indent=2)
    except Exception as e:
        # Catch specific exceptions from generate_with_provider if possible
        # Re-raise as ConfigError or a more specific GenerationError
        raise ConfigError(f"Generation failed using {final_llm_provider}: {str(e)}") from e

def explain_iac_finding(check_id: str, check_name: str, resource: str, iac_type: str,
                         llm_provider: Optional[str] = None, model: Optional[str] = None,
                         api_key: Optional[str] = None, temperature: float = 0.1): # Lower temp for factual explanation
    """Generate an explanation for a given IaC finding using an LLM."""
    config = read_config()

    # Use defaults from config if not provided
    llm_provider = llm_provider or config.get("defaults", {}).get("provider", "deepseek")
    model = model or config.get("defaults", {}).get("model")

    # Get API key from environment if not provided
    if not api_key and llm_provider:
        api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY")

    explanation_prompt = f"""
You are an expert DevOps and Cloud Security engineer. Explain the following Infrastructure as Code security finding identified by checkov in simple terms. Describe the potential risk and suggest common remediation steps for {iac_type}.

Finding Details:
- Check ID: {check_id}
- Check Name: {check_name}
- Affected Resource: {resource}

Explanation:
"""
    try:
        explanation = generate_with_provider(
            provider_name=llm_provider,
            prompt=explanation_prompt,
            model=model,
            api_key=api_key,
            temperature=temperature, # Use lower temperature for more factual explanation
            max_tokens=500 # Limit explanation length
        )
        return explanation
    except Exception as e:
        print(f"Error generating explanation for {check_id}: {e}")
        return f"Could not generate AI explanation for {check_id}: {e}"
