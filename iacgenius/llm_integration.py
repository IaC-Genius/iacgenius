import os
import requests
from .config_handler import read_config, ConfigError
from .llm_providers import DeepseekProvider, OpenAIProvider, AnthropicProvider

def get_provider(provider_name, api_key=None):
    """Get the appropriate LLM provider based on name"""
    providers = {
        "deepseek": DeepseekProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider
    }
    
    if provider_name not in providers:
        raise ConfigError(f"Unsupported provider: {provider_name}")
    
    try:
        return providers[provider_name](api_key)
    except Exception as e:
        raise ConfigError(f"Error initializing {provider_name} provider: {str(e)}")

def generate_with_deepseek(prompt, model="deepseek-chat", temperature=0.2, max_tokens=2048):
    """Generate infrastructure code using DeepSeek's API (legacy function for backward compatibility)"""
    provider = DeepseekProvider()
    return provider.generate(prompt, model, temperature, max_tokens)

def generate_with_provider(provider_name, prompt, model=None, api_key=None, temperature=0.2, max_tokens=2048):
    """Generate infrastructure code using the specified provider"""
    provider = get_provider(provider_name, api_key)
    return provider.generate(prompt, model, temperature, max_tokens)

def validate_api_key(provider_name, api_key):
    """Validate API key for the specified provider"""
    provider = get_provider(provider_name, api_key)
    return provider.validate_api_key()

def get_available_providers():
    """Get a list of available LLM providers"""
    return ["deepseek", "openai", "anthropic"]

def get_available_models(provider_name):
    """Get a list of available models for the specified provider"""
    models = {
        "deepseek": ["deepseek-chat", "deepseek-reasoner"],
        "openai": ["gpt-4-turbo", "gpt-3.5-turbo", "gpt-4o"],
        "anthropic": ["claude-3-5-sonnet-latest", "claude-3-7-sonnet-latest", "claude-3-5-haiku-latest"]
    }
    
    return models.get(provider_name, [])
