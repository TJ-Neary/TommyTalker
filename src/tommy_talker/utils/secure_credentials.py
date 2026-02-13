"""
TommyTalker Secure Credentials
Environment-based credential storage using python-dotenv.
Stores API keys and tokens in .env file (gitignored).
"""

import logging
import os
from pathlib import Path
from typing import Optional

log = logging.getLogger("TommyTalker")

# Use python-dotenv for .env file handling
try:
    from dotenv import load_dotenv, set_key, dotenv_values
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    log.warning("python-dotenv not installed - credential storage limited")


# Path to .env file in project root
def _get_env_path() -> Path:
    """Get path to .env file."""
    # Try to find project root (where main.py is)
    current = Path(__file__).parent.parent
    return current / ".env"


def _ensure_env_file():
    """Ensure .env file exists."""
    env_path = _get_env_path()
    if not env_path.exists():
        env_path.touch()
        log.debug("Created .env file at: %s", env_path)


def load_env():
    """Load environment variables from .env file."""
    if HAS_DOTENV:
        env_path = _get_env_path()
        if env_path.exists():
            load_dotenv(env_path)
            log.debug("Loaded .env from: %s", env_path)


def store_credential(key: str, value: str) -> bool:
    """
    Store a credential in the .env file.
    
    Args:
        key: Environment variable name (e.g., "OPENAI_API_KEY")
        value: The value to store
        
    Returns:
        True if stored successfully
    """
    if not HAS_DOTENV:
        log.warning("dotenv not available, cannot store %s", key)
        return False
        
    try:
        _ensure_env_file()
        env_path = _get_env_path()
        set_key(str(env_path), key, value)
        # Also set in current environment
        os.environ[key] = value
        log.debug("Stored %s in .env", key)
        return True
    except Exception as e:
        log.error("Error storing %s: %s", key, e)
        return False


def get_credential(key: str) -> Optional[str]:
    """
    Retrieve a credential from environment or .env file.
    
    Args:
        key: Environment variable name
        
    Returns:
        The value or None if not found
    """
    # First try environment
    value = os.getenv(key)
    if value:
        return value
        
    # Try loading from .env file directly
    if HAS_DOTENV:
        env_path = _get_env_path()
        if env_path.exists():
            values = dotenv_values(env_path)
            return values.get(key)
            
    return None


def credential_exists(key: str) -> bool:
    """Check if a credential is set."""
    value = get_credential(key)
    return value is not None and len(value) > 0


# Convenience functions for specific credentials
def store_cloud_api_key(api_key: str) -> bool:
    """Store the Cloud Mode API key."""
    return store_credential("OPENAI_API_KEY", api_key)


def get_cloud_api_key() -> Optional[str]:
    """Retrieve the Cloud Mode API key."""
    return get_credential("OPENAI_API_KEY")


def store_cloud_base_url(url: str) -> bool:
    """Store the Cloud API base URL."""
    return store_credential("OPENAI_BASE_URL", url)


def get_cloud_base_url() -> Optional[str]:
    """Retrieve the Cloud API base URL."""
    return get_credential("OPENAI_BASE_URL") or "https://api.openai.com/v1"


def store_huggingface_token(token: str) -> bool:
    """Store the HuggingFace token."""
    return store_credential("HUGGINGFACE_TOKEN", token)


def get_huggingface_token() -> Optional[str]:
    """Retrieve the HuggingFace token."""
    return get_credential("HUGGINGFACE_TOKEN")


# Load .env on module import
load_env()
