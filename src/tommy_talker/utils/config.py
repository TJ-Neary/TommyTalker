"""
TommyTalker Configuration
User preferences, paths, and settings management.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

log = logging.getLogger("TommyTalker")


# Base data directory
BASE_DATA_DIR = Path.home() / "Documents" / "TommyTalker"

# Default configuration values
DEFAULT_HOTKEYS = {
    "cursor_mode": "RightCmd",
    "toggle_record": "Option+R",
    "open_dashboard": "Option+D",
}

DEFAULT_VOCABULARY = [
    "TommyTalker",
]


@dataclass
class UserConfig:
    """User configuration and preferences."""

    # Logging
    logging_enabled: bool = True

    # Onboarding
    skip_onboarding: bool = False

    # Custom vocabulary for Whisper initial_prompt
    vocabulary: list[str] = field(default_factory=lambda: list(DEFAULT_VOCABULARY))

    # Global hotkey bindings
    hotkeys: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))

    # Default operating mode
    default_mode: str = "cursor"

    # Recording trigger mode: "toggle" or "push_to_talk"
    recording_mode: str = "push_to_talk"

    # App context detection
    app_context_enabled: bool = True

    # Audio feedback variation (round-robin sound pools)
    audio_feedback_variation: bool = True

    # Custom Whisper model override
    custom_whisper_model: Optional[str] = None

    # Session recording
    session_audio_source: str = "mic"  # "mic", "system", "system_and_mic"
    session_system_device: Optional[str] = None  # Name of virtual audio device


def get_config_path() -> Path:
    """Get the path to the config file."""
    return BASE_DATA_DIR / "config.json"


def get_recordings_path() -> Path:
    """Get the path to the recordings directory."""
    return BASE_DATA_DIR / "Recordings"


def ensure_data_dirs():
    """Ensure all data directories exist."""
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    get_recordings_path().mkdir(parents=True, exist_ok=True)
    log.debug("Data directories ensured at: %s", BASE_DATA_DIR)


def load_config() -> UserConfig:
    """
    Load user configuration from disk.
    Returns default config if file doesn't exist.
    """
    config_path = get_config_path()

    if not config_path.exists():
        log.debug("No config file found, using defaults")
        return UserConfig()

    try:
        with open(config_path, "r") as f:
            data = json.load(f)

        config = UserConfig(
            logging_enabled=data.get("logging_enabled", True),
            skip_onboarding=data.get("skip_onboarding", False),
            vocabulary=data.get("vocabulary", DEFAULT_VOCABULARY),
            hotkeys=data.get("hotkeys", DEFAULT_HOTKEYS),
            default_mode=data.get("default_mode", "cursor"),
            recording_mode=data.get("recording_mode", "push_to_talk"),
            app_context_enabled=data.get("app_context_enabled", True),
            audio_feedback_variation=data.get("audio_feedback_variation", True),
            custom_whisper_model=data.get("custom_whisper_model"),
            session_audio_source=data.get("session_audio_source", "mic"),
            session_system_device=data.get("session_system_device"),
        )

        # Migrate old defaults to new defaults
        if config.hotkeys.get("cursor_mode") == "Cmd+.":
            config.hotkeys["cursor_mode"] = DEFAULT_HOTKEYS["cursor_mode"]
            save_config(config)
            log.debug("Migrated cursor_mode hotkey: Cmd+. -> RightCmd")

        log.debug("Loaded from: %s", config_path)
        return config

    except Exception as e:
        log.error("Error loading config: %s", e)
        return UserConfig()


def save_config(config: UserConfig) -> bool:
    """Save user configuration to disk."""
    config_path = get_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w") as f:
            json.dump(asdict(config), f, indent=2)

        log.debug("Saved to: %s", config_path)
        return True

    except Exception as e:
        log.error("Error saving config: %s", e)
        return False
