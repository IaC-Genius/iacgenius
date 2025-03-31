import os
import keyring
from cryptography.fernet import Fernet
import toml
from pathlib import Path
# Import ConfigError from the new exceptions module
from .exceptions import ConfigError
# NOTE: llm_integration imports moved inside update_defaults to break circular import

CONFIG_FILE = Path.home() / ".iacgeniusrc"
SERVICE_NAME = "iacgenius"
KEYRING_KEY_NAME = "config_key"


def get_fernet():
    key = keyring.get_password(SERVICE_NAME, KEYRING_KEY_NAME)
    if not key:
        key = Fernet.generate_key().decode()
        keyring.set_password(SERVICE_NAME, KEYRING_KEY_NAME, key)
    return Fernet(key.encode())

def read_config():
    """Read config with environment variable support"""
    config = {
        "defaults": {
            "provider": "deepseek",
            "model": "deepseek-chat",
            "api_key": None
        },
        "presets": {}
    }

    if CONFIG_FILE.exists():
        try:
            encrypted_data = CONFIG_FILE.read_bytes()
            fernet = get_fernet()
            decrypted_data = fernet.decrypt(encrypted_data)
            stored_config = toml.loads(decrypted_data.decode())

            # Merge stored config, decrypting API key if present
            if "defaults" in stored_config:
                stored_defaults = stored_config["defaults"]
                if "api_key" in stored_defaults and stored_defaults["api_key"]:
                    try:
                        # Decrypt the API key read from the file
                        stored_defaults["api_key"] = fernet.decrypt(stored_defaults["api_key"].encode()).decode()
                    except Exception as decrypt_err:
                        print(f"Warning: Failed to decrypt stored API key: {decrypt_err}. Key ignored.")
                        stored_defaults["api_key"] = None # Set to None if decryption fails
                config["defaults"].update(stored_defaults)

            if "presets" in stored_config:
                config["presets"].update(stored_config["presets"]) # Presets likely don't need decryption

        except Exception as e:
            # Log error but continue with defaults and environment variables
            print(f"Warning: Config read/decryption failed: {str(e)}")
            # Ensure config structure is still valid
            config["defaults"] = config.get("defaults", {})
            config["presets"] = config.get("presets", {})


    # --- Environment Variable Handling ---
    # Determine provider first (Env > Config > Default)
    current_provider = os.environ.get("IACGENIUS_PROVIDER") or config["defaults"].get("provider") or "deepseek"
    config["defaults"]["provider"] = current_provider # Ensure provider is set

    # Determine model (Env > Config > Default)
    current_model = os.environ.get("IACGENIUS_MODEL") or config["defaults"].get("model")
    if current_model: # Only update if there's a model from Env or Config
        config["defaults"]["model"] = current_model

    # Determine API Key (Specific Env > Generic Env > Config > None)
    provider_env_key_name = f"{current_provider.upper()}_API_KEY"
    api_key_from_env = os.environ.get(provider_env_key_name) or os.environ.get("IACGENIUS_API_KEY")

    if api_key_from_env:
        config["defaults"]["api_key"] = api_key_from_env
    # If no env var, the decrypted key from config (or None) remains

    # Update with any other generic env vars if they weren't handled above
    # (Currently only provider/model/key are handled with specific logic)
    other_env_vars = {
         # Example: "some_other_setting": os.environ.get("IACGENIUS_OTHER_SETTING")
    }
    config["defaults"].update({k: v for k, v in other_env_vars.items() if v is not None})

    return config

def write_config(config):
    try:
        fernet = get_fernet()
        encrypted_data = fernet.encrypt(toml.dumps(config).encode())
        CONFIG_FILE.write_bytes(encrypted_data)
        CONFIG_FILE.chmod(0o600)
    except Exception as e:
        raise ConfigError(f"Config write failed: {str(e)}") from e

def get_default(key):
    config = read_config()
    return config.get("defaults", {}).get(key)


def update_defaults(**kwargs):
    config = read_config() # Read current config (handles decryption/env vars)
    current_defaults = config.get("defaults", {})
    updates_to_apply = {}

    # Determine the provider being set or the current default
    # Import necessary functions locally to break circular import
    from .llm_integration import get_available_providers, get_available_models

    provider_to_validate = kwargs.get("provider", current_defaults.get("provider"))

    # Validate Provider
    if "provider" in kwargs:
        provider = kwargs["provider"]
        available_providers = get_available_providers() # Now called locally
        if provider not in available_providers:
            raise ConfigError(f"Invalid provider: '{provider}'. Available: {', '.join(available_providers)}")
        updates_to_apply["provider"] = provider
        provider_to_validate = provider # Use the new provider for model validation

    # Validate Model against the provider being set (or current default if provider isn't changing)
    if "model" in kwargs:
        model = kwargs["model"]
        if not provider_to_validate:
             raise ConfigError("Cannot validate model without a provider specified or configured.")

        available_models = get_available_models(provider_to_validate) # Now called locally
        # Allow setting if no specific models are listed (e.g., Ollama) or if model is valid
        if available_models and model not in available_models:
             raise ConfigError(f"Invalid model '{model}' for provider '{provider_to_validate}'. Available: {', '.join(available_models)}")
        updates_to_apply["model"] = model

    # Encrypt API key if provided
    if "api_key" in kwargs and kwargs["api_key"]: # Check if api_key is not None or empty
        fernet = get_fernet()
        try:
            # Encrypt the plain text key before storing
            updates_to_apply["api_key"] = fernet.encrypt(kwargs["api_key"].encode()).decode()
        except Exception as encrypt_err:
            raise ConfigError(f"Failed to encrypt API key: {encrypt_err}") from encrypt_err
    elif "api_key" in kwargs and not kwargs["api_key"]:
        # Handle setting API key to empty/None explicitly
        updates_to_apply["api_key"] = None


    # Apply other updates directly (add validation if needed for other keys)
    for key, value in kwargs.items():
        if key not in ["provider", "model", "api_key"]:
            updates_to_apply[key] = value

    # Merge updates into the existing defaults
    merged_defaults = {**current_defaults, **updates_to_apply}

    # Prepare the config object to be written (only include sections that exist)
    config_to_write = {}
    if merged_defaults:
        config_to_write["defaults"] = merged_defaults
    if config.get("presets"): # Preserve existing presets
        config_to_write["presets"] = config["presets"]

    # Write the potentially updated config
    write_config(config_to_write)

def get_preset(name):
    config = read_config()
    return config.get("presets", {}).get(name)
