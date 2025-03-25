from iacgenius.config_handler import read_config, ConfigError
from iacgenius.llm_integration import generate_with_deepseek, generate_with_provider
from iacgenius.infrastructure import create_prompt_template, get_infrastructure_types
import json
import os

def generate_infrastructure(description, iac_type, cloud_provider=None, llm_provider=None, model=None, 
                           api_key=None, temperature=0.2, max_tokens=2048, region=None, tags=None):
    """Core infrastructure generation logic shared by CLI and Streamlit"""
    config = read_config()
    
    # Use defaults from config if not provided
    llm_provider = llm_provider or config.get("defaults", {}).get("provider", "deepseek")
    model = model or config.get("defaults", {}).get("model")
    
    # Set default model for DeepSeek if not specified
    if llm_provider == "deepseek" and not model:
        model = "deepseek-coder-33b-instruct"
    cloud_provider = cloud_provider or "AWS"
    
    # Get API key from environment if not provided
    if not api_key and llm_provider:
        api_key = os.environ.get(f"{llm_provider.upper()}_API_KEY")
    
    # Create a detailed prompt using the infrastructure module
    prompt = create_prompt_template(iac_type, description, cloud_provider, region, tags)
    
    try:
        # Use the new provider-based generation if provider is specified
        if llm_provider and llm_provider != "deepseek":
            generated_code = generate_with_provider(llm_provider, prompt, model, api_key, temperature, max_tokens)
        else:
            # Use deepseek as the default provider
            generated_code = generate_with_deepseek(prompt, model or "deepseek-coder-33b-instruct", temperature, max_tokens)
        
        return json.dumps({
            "description": description,
            "type": iac_type,
            "cloud_provider": cloud_provider,
            "llm_provider": llm_provider,
            "model": model,
            "code": generated_code
        }, indent=2)
    except Exception as e:
        raise ConfigError(f"Generation failed: {str(e)}")
