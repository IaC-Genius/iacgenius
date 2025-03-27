import requests
import os
from .config_handler import read_config, ConfigError

class LLMProvider:
    """Base class for LLM providers"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key
        self.config = read_config()
    
    def validate_api_key(self):
        """Validate the API key"""
        raise NotImplementedError("Subclasses must implement validate_api_key")
    
    def generate(self, prompt, model=None, temperature=0.2, max_tokens=2048):
        """Generate text from the LLM"""
        raise NotImplementedError("Subclasses must implement generate")


class DeepseekProvider(LLMProvider):
    """DeepSeek LLM provider"""
    
    BASE_URL = "https://api.deepseek.com/v1"
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        # Use provided API key or get from config/environment
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY") or self.config.get("defaults", {}).get("api_key")
        if not self.api_key:
            raise ConfigError("DeepSeek API key not configured")
    
    def validate_api_key(self):
        """Validate the DeepSeek API key"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(f"{self.BASE_URL}/models", headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            raise ConfigError(f"API key validation failed: {str(e)}") from e
    
    def generate(self, prompt, model="deepseek-chat", temperature=0.2, max_tokens=2048):
        """Generate text using DeepSeek's API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Infrastructure-as-Code engineer. Generate valid, secure cloud infrastructure configurations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/chat/completions", json=payload, headers=headers, timeout=180)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise ConfigError(f"Generation failed: {str(e)}")


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        # Use provided API key or get from config/environment
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or self.config.get("defaults", {}).get("api_key")
        if not self.api_key:
            raise ConfigError("OpenAI API key not configured")
    
    def validate_api_key(self):
        """Validate the OpenAI API key"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.get(f"{self.BASE_URL}/models", headers=headers)
            response.raise_for_status()
            return True
        except Exception as e:
            raise ConfigError(f"API key validation failed: {str(e)}")
    
    def generate(self, prompt, model="gpt-3.5-turbo", temperature=0.2, max_tokens=2048):
        """Generate text using OpenAI's API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Infrastructure-as-Code engineer. Generate valid, secure cloud infrastructure configurations."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/chat/completions", json=payload, headers=headers, timeout=180)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise ConfigError(f"Generation failed: {str(e)}")


class AnthropicProvider(LLMProvider):
    """Anthropic LLM provider"""
    
    BASE_URL = "https://api.anthropic.com/v1"
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        # Use provided API key or get from config/environment
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or self.config.get("defaults", {}).get("api_key")
        if not self.api_key:
            raise ConfigError("Anthropic API key not configured")
    
    def validate_api_key(self):
        """Validate the Anthropic API key"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        try:
            # Anthropic requires a POST request for validation
            response = requests.post(
                f"{self.BASE_URL}/messages",
                headers=headers,
                json={"max_tokens": 1, "messages": []}
            )
            # 400 status is expected for empty request
            return response.status_code == 400
        except Exception as e:
            raise ConfigError(f"API key validation failed: {str(e)}")
    
    def generate(self, prompt, model="claude-3-5-sonnet-latest", temperature=0.2, max_tokens=2048):
        """Generate text using Anthropic's API"""
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "system": "You are an expert Infrastructure-as-Code engineer. Generate valid, secure cloud infrastructure configurations.",
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/messages", json=payload, headers=headers, timeout=180)
            response.raise_for_status()
            return response.json()["content"][0]["text"]
        except Exception as e:
            raise ConfigError(f"Generation failed: {str(e)}")


class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM provider"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key=None):
        super().__init__(api_key)
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY") or self.config.get("defaults", {}).get("api_key")
        if not self.api_key:
            raise ConfigError("OpenRouter API key not configured")
    
    def validate_api_key(self):
        # Ensure API key is properly formatted
        if not self.api_key or not isinstance(self.api_key, str):
            raise ConfigError("API key must be a non-empty string")
            
        if not self.api_key.startswith("sk-or-"):
            raise ConfigError("OpenRouter API key must start with 'sk-or-'")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/iacgenius/iacgenius",
            "X-Title": "IacGenius (https://github.com/iacgenius/iacgenius)"
        }
        
        try:
            # Use models endpoint for validation
            response = requests.get(
                f"{self.BASE_URL}/models",
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                return True
                
            error_msg = f"API validation failed (status {response.status_code})"
            if response.text:
                error_msg += f": {response.text}"
            raise ConfigError(error_msg)
                
        except requests.exceptions.RequestException as e:
            raise ConfigError(f"API key validation failed: {str(e)}") from e
    
    def generate(self, prompt, model="deepseek/deepseek-chat-v3-0324:free", temperature=0.2, max_tokens=2048):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/your-repo",
            "X-Title": "IacGenius",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Infrastructure-as-Code engineer..."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(f"{self.BASE_URL}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise ConfigError(f"Generation failed: {str(e)}")
