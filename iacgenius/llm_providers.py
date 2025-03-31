import requests
import os
from .config_handler import read_config
from .exceptions import ConfigError # Import from exceptions module

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

    def list_models(self):
        """List available models for the provider"""
        # Default implementation returns an empty list or raises error
        # Subclasses should override this if they support dynamic model listing
        print(f"Warning: list_models() not implemented for {self.__class__.__name__}. Returning empty list.")
        return []


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
            raise ConfigError(f"Generation failed: {str(e)}") from e

    def list_models(self):
        """List available models using the DeepSeek API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(f"{self.BASE_URL}/models", headers=headers)
            response.raise_for_status()
            models_data = response.json().get("data", [])
            return [model.get("id") for model in models_data if model.get("id")]
        except Exception as e:
            print(f"Warning: Failed to list DeepSeek models: {str(e)}")
            # Fallback to empty list on error
            return []

class OpenRouterProvider(LLMProvider):
    """OpenRouter LLM provider (aggregator)"""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key=None):
        super().__init__(api_key)
        # OpenRouter primarily uses environment variable or direct input
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            # Unlike others, don't check config by default for OpenRouter key
            raise ConfigError("OpenRouter API key not found in OPENROUTER_API_KEY environment variable")
        # Recommended headers by OpenRouter
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/IaC-Genius/iacgenius", # Replace with your actual repo URL
            "X-Title": "IACGenius", # Replace with your app name
        }

    def validate_api_key(self):
        """Validate the OpenRouter API key by checking credits"""
        try:
            # OpenRouter doesn't have a simple /models endpoint for validation without auth sometimes
            # Checking credits remaining is a common way to validate
            response = requests.get("https://openrouter.ai/api/v1/auth/key", headers=self.headers)
            response.raise_for_status()
            # Check if the response indicates a valid key (e.g., contains expected fields)
            # A simple status check might suffice if the endpoint requires auth
            return True
        except Exception as e:
            # Distinguish between auth errors (401) and other issues
            status_code = getattr(getattr(e, 'response', None), 'status_code', None)
            if status_code == 401:
                 raise ConfigError("OpenRouter API key validation failed: Invalid API Key (401)") from e
            raise ConfigError(f"OpenRouter API key validation failed: {str(e)}") from e

    def generate(self, prompt, model="openai/gpt-3.5-turbo", temperature=0.2, max_tokens=2048):
        """Generate text using OpenRouter's API"""
        payload = {
            "model": model, # Expects format like 'openai/gpt-4o', 'google/gemini-pro' etc.
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
            response = requests.post(f"{self.BASE_URL}/chat/completions", json=payload, headers=self.headers, timeout=180)
            response.raise_for_status()
            # Ensure response has choices and message content
            choices = response.json().get("choices")
            if not choices:
                raise ConfigError("OpenRouter API response missing 'choices'.")
            message = choices[0].get("message")
            if not message:
                 raise ConfigError("OpenRouter API response missing 'message' in choices.")
            content = message.get("content")
            if content is None:
                 raise ConfigError("OpenRouter API response missing 'content' in message.")
            return content
        except Exception as e:
            # Add more specific error checking if possible
            raise ConfigError(f"OpenRouter generation failed: {str(e)}") from e

    def list_models(self):
        """List available models using the OpenRouter API"""
        # OpenRouter's model list endpoint doesn't strictly require auth,
        # but including headers is good practice.
        try:
            response = requests.get(f"{self.BASE_URL}/models", headers=self.headers)
            response.raise_for_status()
            models_data = response.json().get("data", [])
            # Extract model IDs, potentially filtering or sorting
            # Example: return sorted([model.get("id") for model in models_data if model.get("id")])
            # For simplicity, return known good ones + potentially others found
            known_models = [
                "openai/gpt-4o", "openai/gpt-3.5-turbo", "google/gemini-pro-1.5",
                "anthropic/claude-3.5-sonnet", "mistralai/mistral-7b-instruct",
                "meta-llama/llama-3-8b-instruct"
            ]
            fetched_models = {model.get("id") for model in models_data if model.get("id")}
            # Combine and deduplicate, keeping known ones first
            combined = known_models + sorted(list(fetched_models - set(known_models)))
            return combined
        except Exception as e:
            print(f"Warning: Failed to list OpenRouter models: {str(e)}")
            # Fallback to empty list on error
            return []

class AWSBedrockProvider(LLMProvider):
    """AWS Bedrock LLM provider"""

    # Map user-friendly names to Bedrock model IDs
    MODEL_ID_MAP = {
        "claude-3.5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
        "claude-3-opus": "anthropic.claude-3-opus-20240229-v1:0",
        "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
        "llama3-8b-instruct": "meta.llama3-8b-instruct-v1:0",
        "llama3-70b-instruct": "meta.llama3-70b-instruct-v1:0",
        "titan-text-express": "amazon.titan-text-express-v1",
        # Add other models as needed
    }

    def __init__(self, api_key=None): # api_key is not used for Bedrock
        super().__init__(api_key=None) # Pass None explicitly
        try:
            import boto3
            # Allow region to be specified via environment or AWS config
            self.region_name = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
            if not self.region_name:
                 # Attempt to get region from boto3 session if not in env vars
                 session = boto3.Session()
                 self.region_name = session.region_name
                 if not self.region_name:
                      raise ConfigError("AWS Region not configured. Set AWS_REGION or AWS_DEFAULT_REGION environment variable, or configure AWS credentials.")

            self.bedrock_runtime = boto3.client(
                service_name='bedrock-runtime',
                region_name=self.region_name
                # Credentials are automatically handled by boto3 (env vars, shared credentials file, IAM role, etc.)
            )
        except ImportError:
            raise ConfigError("AWS Bedrock provider requires 'boto3'. Please install it.")
        except Exception as e:
            raise ConfigError(f"Failed to initialize AWS Bedrock client: {str(e)}") from e

    def validate_api_key(self):
        """Validate AWS credentials by attempting a simple Bedrock API call"""
        # Bedrock doesn't use API keys in the same way. We validate credentials implicitly.
        # Attempting to list foundation models is a way to check connectivity and permissions.
        try:
            import boto3
            bedrock_client = boto3.client(service_name='bedrock', region_name=self.region_name)
            bedrock_client.list_foundation_models(byProvider='Anthropic') # Example call
            return True
        except Exception as e:
            # Catch potential NoCredentialsError, ClientError etc.
            raise ConfigError(f"AWS Bedrock credential/permission validation failed: {str(e)}") from e

    def get_bedrock_model_id(self, model_name):
        """Get the Bedrock model ID from the user-friendly name"""
        bedrock_id = self.MODEL_ID_MAP.get(model_name)
        if not bedrock_id:
             # Maybe the user provided the full ID directly
             if model_name.startswith(("anthropic.", "meta.", "amazon.", "cohere.", "ai21.")):
                  return model_name
             raise ConfigError(f"Unknown or unsupported Bedrock model name: {model_name}. Supported: {list(self.MODEL_ID_MAP.keys())}")
        return bedrock_id

    def generate(self, prompt, model="claude-3.5-sonnet", temperature=0.2, max_tokens=2048):
        """Generate text using AWS Bedrock"""
        import json # Ensure json is imported

        bedrock_model_id = self.get_bedrock_model_id(model)

        # Construct the payload based on the model provider (Bedrock API varies)
        provider_name = bedrock_model_id.split('.')[0]
        request_body = {}

        if provider_name == "anthropic":
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": "You are an expert Infrastructure-as-Code engineer. Generate valid, secure cloud infrastructure configurations.",
                "messages": [{"role": "user", "content": prompt}]
            }
        elif provider_name == "meta": # Llama models
             request_body = {
                  "prompt": f"<s>[INST] System: You are an expert Infrastructure-as-Code engineer. Generate valid, secure cloud infrastructure configurations.\nUser: {prompt} [/INST]",
                  "max_gen_len": max_tokens,
                  "temperature": temperature,
             }
        elif provider_name == "amazon": # Titan models
             request_body = {
                  "inputText": prompt,
                  "textGenerationConfig": {
                       "maxTokenCount": max_tokens,
                       "temperature": temperature,
                       "stopSequences": [], # Define stop sequences if needed
                  }
             }
        # Add logic for other providers like cohere, ai21 if needed
        else:
            raise ConfigError(f"Payload construction not implemented for Bedrock provider: {provider_name}")

        try:
            response = self.bedrock_runtime.invoke_model(
                body=json.dumps(request_body),
                modelId=bedrock_model_id,
                accept='application/json',
                contentType='application/json'
            )

            response_body = json.loads(response.get('body').read())

            # Extract content based on the model provider
            if provider_name == "anthropic":
                if "content" not in response_body or not response_body["content"]:
                     raise ConfigError("Invalid response from Bedrock (Anthropic): 'content' missing or empty.")
                return response_body["content"][0]["text"]
            elif provider_name == "meta":
                 return response_body.get('generation')
            elif provider_name == "amazon":
                 if "results" not in response_body or not response_body["results"]:
                      raise ConfigError("Invalid response from Bedrock (Titan): 'results' missing or empty.")
                 return response_body["results"][0].get("outputText")
            else:
                 raise ConfigError(f"Response parsing not implemented for Bedrock provider: {provider_name}")

        except Exception as e:
            # Catch specific boto3 errors if possible (e.g., botocore.exceptions.ClientError)
            raise ConfigError(f"AWS Bedrock generation failed: {str(e)}") from e

    def list_models(self):
        """List available foundation models from AWS Bedrock"""
        try:
            import boto3
            # Use the 'bedrock' client, not 'bedrock-runtime' for listing
            bedrock_client = boto3.client(service_name='bedrock', region_name=self.region_name)
            # Example: List models supporting text generation
            response = bedrock_client.list_foundation_models(
                # byProvider='Anthropic', # Optional: filter by provider
                # byCustomizationType='FINE_TUNING', # Optional: filter by customization
                byOutputModality='TEXT', # Filter for text output models
                byInferenceType='ON_DEMAND' # Filter for on-demand models
            )
            model_summaries = response.get('modelSummaries', [])

            # Map model IDs back to user-friendly names if possible, otherwise use ID
            available_models = []
            reverse_map = {v: k for k, v in self.MODEL_ID_MAP.items()}
            for summary in model_summaries:
                model_id = summary.get('modelId')
                if model_id:
                    friendly_name = reverse_map.get(model_id)
                    # Only include models we have a friendly mapping for, or adjust as needed
                    if friendly_name:
                         available_models.append(friendly_name)
             # Optionally include unmapped IDs:
             # else:
             #    available_models.append(model_id)

            # Return the user-friendly names we support
            # return sorted(list(set(available_models))) # Ensure unique and sorted
            # Return only the ones defined in our map for consistency with UI
            return sorted(list(self.MODEL_ID_MAP.keys()))

        except ImportError: # Removed unused variable 'e'
             print("Warning: Boto3 not installed, cannot list Bedrock models.")
             return list(self.MODEL_ID_MAP.keys()) # Fallback to static list
        except Exception as e:
            print(f"Warning: Failed to list AWS Bedrock models: {str(e)}")
            # Fallback to the known static list in case of error
            # Re-raise the exception with context if needed, or just return fallback
            # For now, just returning the fallback list as per original logic.
            # If we wanted to raise, it would be:
            # raise ConfigError(f"Failed to list AWS Bedrock models: {str(e)}") from e
            return list(self.MODEL_ID_MAP.keys())

class OllamaProvider(LLMProvider):
    """Ollama LLM provider (local)"""

    # Default base URL, can be overridden via config or env var later if needed
    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, api_key=None): # api_key is not used for Ollama
        super().__init__(api_key=None)
        # TODO: Allow overriding base_url via config/env
        self.base_url = self.DEFAULT_BASE_URL
        self.headers = {"Content-Type": "application/json"}
        # Check connectivity on init
        self._check_ollama_connection()

    def _check_ollama_connection(self):
        """Check if the Ollama server is reachable"""
        try:
            # Ollama root endpoint usually returns "Ollama is running"
            response = requests.get(self.base_url, timeout=5)
            response.raise_for_status()
            if "Ollama is running" not in response.text:
                 print(f"Warning: Ollama server found at {self.base_url}, but response unexpected: {response.text}")
        except requests.exceptions.ConnectionError:
             raise ConfigError(f"Ollama server not reachable at {self.base_url}. Ensure Ollama is running.")
        except Exception as e:
             raise ConfigError(f"Error connecting to Ollama server at {self.base_url}: {str(e)}") from e

    def validate_api_key(self):
        """Ollama doesn't use API keys, so validation is just connectivity check."""
        try:
            self._check_ollama_connection()
            return True
        except ConfigError as e:
            # Re-raise ConfigError to provide specific feedback
            raise e # Re-raise the specific ConfigError
        except Exception as e:
            # Catch any other unexpected errors during check
            raise ConfigError(f"Unexpected error during Ollama connectivity check: {str(e)}") from e

    def generate(self, prompt, model="llama3", temperature=0.2, max_tokens=2048):
        """Generate text using a local Ollama instance"""
        # Ollama uses /api/chat endpoint
        api_url = f"{self.base_url}/api/chat"

        payload = {
            "model": model, # Expects model name like 'llama3', 'mistral' etc.
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
            "options": { # Ollama uses an 'options' object for parameters
                "temperature": temperature,
                "num_predict": max_tokens # Ollama uses num_predict for max tokens
                # Add other Ollama options here if needed (e.g., top_p, top_k)
            },
            "stream": False # We want the full response, not streaming for now
        }

        try:
            response = requests.post(api_url, json=payload, headers=self.headers, timeout=180) # Longer timeout for local models
            response.raise_for_status()

            response_data = response.json()

            # Extract content from the response structure
            message = response_data.get("message")
            if not message:
                 raise ConfigError("Ollama API response missing 'message'.")
            content = message.get("content")
            if content is None:
                 raise ConfigError("Ollama API response missing 'content' in message.")

            return content.strip() # Strip potential whitespace

        except Exception as e:
            raise ConfigError(f"Ollama generation failed: {str(e)}") from e

    def list_models(self):
        """List available models from the local Ollama instance"""
        api_url = f"{self.base_url}/api/tags"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            models_data = response.json().get("models", [])
            # Extract the 'name' field (e.g., "llama3:latest")
            # Optionally strip tags like ':latest' if desired
            return sorted([model.get("name") for model in models_data if model.get("name")])
        except requests.exceptions.ConnectionError:
             print(f"Warning: Ollama server not reachable at {self.base_url} to list models.")
             return [] # Return empty list if connection fails
        except Exception as e:
            # Use the captured exception variable 'e' in the warning message
            print(f"Warning: Failed to list Ollama models: {e}")
            return [] # Return empty list on other errors

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
            raise ConfigError(f"API key validation failed: {str(e)}") from e # Keep existing context chaining

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
            response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
            # Check if response JSON is valid and contains expected structure
            try:
                response_data = response.json()
                if "choices" not in response_data or not response_data["choices"]:
                     raise ConfigError("OpenAI API response missing 'choices'.")
                message = response_data["choices"][0].get("message")
                if not message:
                     raise ConfigError("OpenAI API response missing 'message' in choices.")
                content = message.get("content")
                if content is None:
                     raise ConfigError("OpenAI API response missing 'content' in message.")
                return content
            except json.JSONDecodeError:
                 raise ConfigError(f"Failed to decode JSON response from OpenAI: {response.text}")
            except KeyError as ke:
                 raise ConfigError(f"Unexpected response structure from OpenAI (missing key {ke}): {response.json()}")

        except requests.exceptions.HTTPError as e:
            # Try to get more specific error details from OpenAI response body
            error_message = f"Generation failed: {str(e)}"
            try:
                error_details = e.response.json()
                error_message += f"\nDetails: {error_details}"
            except json.JSONDecodeError:
                error_message += f"\nResponse Text: {e.response.text}"
            raise ConfigError(error_message) from e
        except Exception as e:
            # Catch other potential errors (network issues, timeouts, etc.)
            raise ConfigError(f"Generation failed with unexpected error: {str(e)}") from e

    def list_models(self):
        """List available models using the OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.get(f"{self.BASE_URL}/models", headers=headers)
            response.raise_for_status()
            models_data = response.json().get("data", [])
            # Filter for models owned by 'openai' or 'system' potentially, and sort
            # return sorted([model.get("id") for model in models_data if model.get("id") and model.get("owned_by") in ["openai", "system"]])
            # Simpler: return all IDs found
            return sorted([model.get("id") for model in models_data if model.get("id")])
        except Exception as e:
            print(f"Warning: Failed to list OpenAI models: {str(e)}")
            # Fallback to empty list on error
            return []

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
            raise ConfigError(f"API key validation failed: {str(e)}") from e

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
            raise ConfigError(f"Generation failed: {str(e)}") from e

    def list_models(self):
        """List known compatible models for Anthropic"""
        # Anthropic API doesn't have a standard '/models' endpoint.
        # Return the known compatible models based on API version/docs.
        print("Info: Anthropic model listing returns a static list of known compatible models.")
        return ["claude-3-5-sonnet-latest", "claude-3-opus-latest", "claude-3-haiku-latest"]
