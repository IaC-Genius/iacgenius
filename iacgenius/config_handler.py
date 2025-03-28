import os
import keyring
from cryptography.fernet import Fernet
import toml
from pathlib import Path

CONFIG_FILE = Path.home() / ".iacgeniusrc"
SERVICE_NAME = "iacgenius"
KEYRING_KEY_NAME = "config_key"

class ConfigError(Exception):
    pass

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
            # Merge stored config with defaults
            if "defaults" in stored_config:
                config["defaults"].update(stored_config["defaults"])
            if "presets" in stored_config:
                config["presets"].update(stored_config["presets"])
        except Exception as e:
            # Log error but continue with defaults
            print(f"Warning: Config read failed: {str(e)}")
            # Do not return here, continue with environment variables

    # Merge environment variables with proper precedence
    env_vars = {
        "provider": os.environ.get("IACGENIUS_PROVIDER"),
        "model": os.environ.get("IACGENIUS_MODEL"),
        "api_key": os.environ.get("IACGENIUS_API_KEY")
    }
    
    # Environment variables override config file defaults
    config["defaults"].update({k: v for k, v in env_vars.items() if v is not None})
        
    return config

def write_config(config):
    try:
        fernet = get_fernet()
        encrypted_data = fernet.encrypt(toml.dumps(config).encode())
        CONFIG_FILE.write_bytes(encrypted_data)
        CONFIG_FILE.chmod(0o600)
    except Exception as e:
        raise ConfigError(f"Config write failed: {str(e)}")

def get_default(key):
    config = read_config()
    return config.get("defaults", {}).get(key)

def update_defaults(**kwargs):
    config = read_config()
    
    # Encrypt API key if provided
    if "api_key" in kwargs:
        fernet = get_fernet()
        kwargs["api_key"] = fernet.encrypt(kwargs["api_key"].encode()).decode()
    
    # Validate provider/model combinations
    from .llm_integration import get_available_providers, get_available_models
    
    if "provider" in kwargs:
        provider = kwargs["provider"]
        available_providers = get_available_providers()
        if provider not in available_providers:
            raise ConfigError(f"Invalid provider: {provider}")
            
        if "model" in kwargs:
            available_models = get_available_models(provider)
            if available_models and kwargs["model"] not in available_models:
                raise ConfigError(f"Invalid model for {provider}: {kwargs['model']}")
    
    # Merge and save updates
    config["defaults"] = {**config.get("defaults", {}), **kwargs}
    write_config(config)

def get_preset(name):
    config = read_config()
    return config.get("presets", {}).get(name)
