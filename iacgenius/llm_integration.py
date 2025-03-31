from .exceptions import ConfigError # Import from exceptions module
# Added AWSBedrockProvider, OllamaProvider
from .llm_providers import DeepseekProvider, OpenAIProvider, AnthropicProvider, OpenRouterProvider, AWSBedrockProvider, OllamaProvider

# Define providers dictionary accessible by get_available_providers
_providers_map = {
    "deepseek": DeepseekProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openrouter": OpenRouterProvider,
    "bedrock": AWSBedrockProvider,
    "ollama": OllamaProvider
}

def get_provider(provider_name, api_key=None):
    """Get the appropriate LLM provider based on name"""
    if provider_name not in _providers_map:
        raise ConfigError(f"Unsupported provider: {provider_name}. Supported: {', '.join(_providers_map.keys())}")

    try:
        # Use the map defined above
        return _providers_map[provider_name](api_key)
    except Exception as e:
        raise ConfigError(f"Error initializing {provider_name} provider: {str(e)}") from e

def generate_with_provider(provider_name, prompt, model=None, api_key=None, temperature=0.2, max_tokens=2048):
    """Generate infrastructure code using the specified provider"""
    provider = get_provider(provider_name, api_key)
    return provider.generate(prompt, model, temperature, max_tokens)

def validate_api_key(provider_name, api_key):
    """Validate API key for the specified provider"""
    provider = get_provider(provider_name, api_key)
    return provider.validate_api_key()

def get_available_providers():
    """Get a list of available LLM providers dynamically"""
    return list(_providers_map.keys())

def get_available_models(provider_name, api_key=None):
    """Get a list of available models for the specified provider, dynamically if possible."""
    try:
        # Instantiate the provider - it handles API key precedence (arg > env > config)
        # For Bedrock/Ollama, api_key arg is ignored, uses env/config/local setup.
        provider = get_provider(provider_name, api_key)

        # Call the provider's list_models method
        models = provider.list_models()
        # print(f"DEBUG (llm_integration): list_models for {provider_name} returned: {models}") # Remove debug print

        # Return the fetched models, or an empty list if fetching failed (handled in provider)
        return models if models else []

    except ConfigError:
         # Let ConfigErrors (like missing API key needed for listing) propagate
         raise
    except Exception as e:
        # Catch other unexpected errors during model listing specifically
        print(f"Unexpected error getting models for {provider_name}: {e}")
        # Consider logging the traceback here for debugging
        # import traceback
        # print(traceback.format_exc())
        return [] # Return empty list for unexpected errors during the list_models call itself
