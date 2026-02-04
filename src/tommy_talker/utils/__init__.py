"""
TommyTalker Utils Module
Hardware detection, configuration, permissions, and global hotkeys.
"""

from tommy_talker.utils.hardware_detect import HardwareProfile, detect_hardware
from tommy_talker.utils.config import UserConfig, load_config, save_config, ensure_data_dirs
from tommy_talker.utils.permissions import PermissionStatus, check_permissions, open_system_preferences
from tommy_talker.utils.hotkeys import HotkeyManager
from tommy_talker.utils.typing import TypingController, type_at_cursor, paste_text

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
