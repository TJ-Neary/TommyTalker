"""
Tests for modifier-only hotkey support (e.g., Right Command key).
"""

import pytest

from tommy_talker.utils.hotkeys import (
    MODIFIER_KEY_CODES,
    MODIFIER_KEY_NAMES,
    is_modifier_only_hotkey,
    HotkeyManager,
)


class TestModifierKeyCodes:
    """Test modifier key code definitions."""

    def test_right_cmd_keycode(self):
        """Right Command key has correct virtual keycode."""
        assert MODIFIER_KEY_CODES["right_cmd"] == 54

    def test_left_cmd_keycode(self):
        assert MODIFIER_KEY_CODES["left_cmd"] == 55

    def test_right_shift_keycode(self):
        assert MODIFIER_KEY_CODES["right_shift"] == 60

    def test_all_modifier_keys_defined(self):
        """All 8 modifier keys are defined."""
        expected = [
            "right_cmd", "left_cmd", "right_shift", "left_shift",
            "right_option", "left_option", "right_ctrl", "left_ctrl",
        ]
        for key in expected:
            assert key in MODIFIER_KEY_CODES


class TestModifierKeyNames:
    """Test user-friendly name mappings."""

    def test_rightcmd_maps(self):
        assert MODIFIER_KEY_NAMES["rightcmd"] == "right_cmd"

    def test_rightcommand_maps(self):
        assert MODIFIER_KEY_NAMES["rightcommand"] == "right_cmd"

    def test_rightoption_maps(self):
        assert MODIFIER_KEY_NAMES["rightoption"] == "right_option"

    def test_rightalt_maps(self):
        assert MODIFIER_KEY_NAMES["rightalt"] == "right_option"


class TestIsModifierOnlyHotkey:
    """Test the is_modifier_only_hotkey helper."""

    def test_right_cmd(self):
        assert is_modifier_only_hotkey("RightCmd") is True

    def test_right_command(self):
        assert is_modifier_only_hotkey("RightCommand") is True

    def test_left_option(self):
        assert is_modifier_only_hotkey("LeftOption") is True

    def test_regular_hotkey_not_modifier_only(self):
        assert is_modifier_only_hotkey("Cmd+.") is False

    def test_regular_multi_key_not_modifier_only(self):
        assert is_modifier_only_hotkey("Cmd+Shift+Space") is False

    def test_empty_string(self):
        assert is_modifier_only_hotkey("") is False

    def test_case_insensitive(self):
        assert is_modifier_only_hotkey("rightcmd") is True
        assert is_modifier_only_hotkey("RIGHTCMD") is True


class TestHotkeyManagerParsing:
    """Test hotkey string parsing for modifier-only keys."""

    def test_parse_rightcmd(self):
        mgr = HotkeyManager()
        key, mods = mgr._parse_hotkey_string("RightCmd")
        assert key == "right_cmd"
        assert mods == []

    def test_parse_leftoption(self):
        mgr = HotkeyManager()
        key, mods = mgr._parse_hotkey_string("LeftOption")
        assert key == "left_option"
        assert mods == []

    def test_parse_regular_hotkey_unchanged(self):
        """Regular hotkeys still parse normally."""
        mgr = HotkeyManager()
        key, mods = mgr._parse_hotkey_string("Cmd+.")
        assert key == "."
        assert "cmd" in mods

    def test_parse_multi_modifier(self):
        mgr = HotkeyManager()
        key, mods = mgr._parse_hotkey_string("Cmd+Shift+Space")
        assert key == "space"
        assert "cmd" in mods
        assert "shift" in mods


class TestModifierHotkeyRegistration:
    """Test registering modifier-only hotkeys."""

    def test_register_modifier_only_stores_in_modifier_dict(self):
        """Modifier-only hotkeys go to _modifier_hotkeys, not _hotkeys."""
        mgr = HotkeyManager()
        callback = lambda: None
        result = mgr.register("RightCmd", callback, "Test")

        if result:  # May fail if Quartz not available
            assert "right_cmd" in mgr._modifier_hotkeys
            assert len(mgr._hotkeys) == 0

    def test_register_regular_stores_in_hotkeys(self):
        """Regular hotkeys go to _hotkeys, not _modifier_hotkeys."""
        mgr = HotkeyManager()
        callback = lambda: None
        result = mgr.register("Cmd+.", callback, "Test")

        if result:
            assert len(mgr._modifier_hotkeys) == 0
            assert len(mgr._hotkeys) > 0

    def test_register_modifier_with_callback_up(self):
        """Modifier-only hotkeys can have callback_up for push-to-talk."""
        mgr = HotkeyManager()
        down = lambda: None
        up = lambda: None
        result = mgr.register("RightCmd", down, "Test", callback_up=up)

        if result:
            hotkey = mgr._modifier_hotkeys["right_cmd"]
            assert hotkey.callback is down
            assert hotkey.callback_up is up
