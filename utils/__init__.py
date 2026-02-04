"""
TommyTalker Utils Module
Hardware detection, configuration, permissions, and global hotkeys.
"""

from utils.hardware_detect import HardwareProfile, detect_hardware
from utils.config import UserConfig, load_config, save_config, ensure_data_dirs
from utils.permissions import PermissionStatus, check_permissions, open_system_preferences
from utils.hotkeys import HotkeyManager
from utils.typing import TypingController, type_at_cursor, paste_text

__all__ = [
    "HardwareProfile",
    "detect_hardware",
    "UserConfig",
    "load_config",
    "save_config",
    "ensure_data_dirs",
    "PermissionStatus",
    "check_permissions",
    "open_system_preferences",
    "HotkeyManager",
    "TypingController",
    "type_at_cursor",
    "paste_text",
]
