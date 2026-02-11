"""
TommyTalker Configuration
User preferences, paths, and settings management.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


# Base data directory
BASE_DATA_DIR = Path.home() / "Documents" / "TommyTalker"

# Default configuration values - user-friendly hotkeys
DEFAULT_HOTKEYS = {
    "cursor_mode": "RightCmd",
    "editor_mode": "Ctrl+/",
    "meeting_mode": "Option+M",
    "hud_mode": "Option+H",
    "toggle_record": "Option+R",
    "open_dashboard": "Option+D",
}

DEFAULT_VOCABULARY = [
    "TommyTalker", "RAG", "LLM", "Diarization", "Ollama", "vector store"
]


@dataclass
class UserConfig:
    """User configuration and preferences."""
    
    # Logging
    logging_enabled: bool = True  # Default to True for debugging
    
    # Onboarding
    skip_onboarding: bool = False
    
    # Custom vocabulary for Whisper initial_prompt
    vocabulary: list[str] = field(default_factory=lambda: list(DEFAULT_VOCABULARY))
    
    # Path to style guide file
    style_guide_path: Optional[str] = None
    
    # Global hotkey bindings (all modes)
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    
    # Default operating mode
    default_mode: str = "cursor"
    
    # Recording trigger mode: "toggle" or "push_to_talk"
    # toggle = press once to start, press again to stop
    # push_to_talk = hold to record, release to stop
    recording_mode: str = "push_to_talk"
    
    # Auto-clear session on new recording
    auto_clear_session: bool = False
    
    # HuggingFace token for pyannote.audio (stored securely via keyring)
    # Note: This is just for display status; actual token is in keychain
    huggingface_token_set: bool = False
    
    # Advanced mode for manual Ollama model tags
    advanced_mode: bool = False
    
    # Custom model overrides (when advanced_mode is True)
    custom_whisper_model: Optional[str] = None
    custom_llm_model: Optional[str] = None
    
    # App context detection
    app_context_enabled: bool = True

    # Audio feedback variation (round-robin sound pools)
    audio_feedback_variation: bool = True

    # Cloud Mode - Hybrid Cloud Uplink
    cloud_mode_enabled: bool = False
    cloud_api_base_url: str = "https://api.openai.com/v1"  # OpenAI-compatible endpoint
    cloud_api_model: str = "gpt-4o-mini"  # Default cloud model
    # Note: API key is stored securely in keychain, not in config
    cloud_api_key_set: bool = False


def get_config_path() -> Path:
    """Get the path to the config file."""
    return BASE_DATA_DIR / "config.json"


def get_recordings_path() -> Path:
    """Get the path to the recordings directory."""
    return BASE_DATA_DIR / "Recordings"


def get_chroma_path() -> Path:
    """Get the path to the ChromaDB directory."""
    return BASE_DATA_DIR / "chroma"


def get_sqlite_path() -> Path:
    """Get the path to the SQLite database."""
    return BASE_DATA_DIR / "sessions.db"


def get_style_guide_path() -> Path:
    """Get the default path to the style guide."""
    return BASE_DATA_DIR / "style_guide.txt"


def ensure_data_dirs():
    """Ensure all data directories exist."""
    dirs = [
        BASE_DATA_DIR,
        get_recordings_path(),
        get_chroma_path(),
    ]
    
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        
    print(f"[Config] Data directories ensured at: {BASE_DATA_DIR}")


def load_config() -> UserConfig:
    """
    Load user configuration from disk.
    Returns default config if file doesn't exist.
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        print("[Config] No config file found, using defaults")
        return UserConfig()
        
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
            
        # Handle missing fields gracefully
        config = UserConfig(
            logging_enabled=data.get("logging_enabled", True),
            skip_onboarding=data.get("skip_onboarding", False),
            vocabulary=data.get("vocabulary", DEFAULT_VOCABULARY),
            style_guide_path=data.get("style_guide_path"),
            hotkeys=data.get("hotkeys", DEFAULT_HOTKEYS),
            default_mode=data.get("default_mode", "cursor"),
            recording_mode=data.get("recording_mode", "push_to_talk"),
            auto_clear_session=data.get("auto_clear_session", False),
            huggingface_token_set=data.get("huggingface_token_set", False),
            advanced_mode=data.get("advanced_mode", False),
            custom_whisper_model=data.get("custom_whisper_model"),
            custom_llm_model=data.get("custom_llm_model"),
            app_context_enabled=data.get("app_context_enabled", True),
            audio_feedback_variation=data.get("audio_feedback_variation", True),
            cloud_mode_enabled=data.get("cloud_mode_enabled", False),
            cloud_api_base_url=data.get("cloud_api_base_url", "https://api.openai.com/v1"),
            cloud_api_model=data.get("cloud_api_model", "gpt-4o-mini"),
            cloud_api_key_set=data.get("cloud_api_key_set", False),
        )
        
        print(f"[Config] Loaded from: {config_path}")
        return config
        
    except Exception as e:
        print(f"[Config] Error loading config: {e}")
        return UserConfig()


def save_config(config: UserConfig) -> bool:
    """
    Save user configuration to disk.
    
    Returns:
        True if saved successfully
    """
    config_path = get_config_path()
    
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(asdict(config), f, indent=2)
            
        print(f"[Config] Saved to: {config_path}")
        return True
        
    except Exception as e:
        print(f"[Config] Error saving config: {e}")
        return False


def load_style_guide() -> Optional[str]:
    """Load style guide content from default location."""
    path = get_style_guide_path()
    
    if not path.exists():
        return None
        
    try:
        return path.read_text()
    except Exception as e:
        print(f"[Config] Error loading style guide: {e}")
        return None
