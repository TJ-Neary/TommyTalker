"""
TommyTalker Hotkeys
Global hotkey registration using Quartz Event Tap.

Supports both modifier-only keys (e.g., Right Command for push-to-talk)
and standard key combos (e.g., Option+R) via CGEventTap.
"""

import logging
from typing import Callable, Optional
from dataclasses import dataclass

log = logging.getLogger("TommyTalker")

try:
    from Quartz import (
        CGEventTapCreate,
        CGEventTapEnable,
        CGEventTapIsEnabled,
        CGEventMaskBit,
        kCGEventKeyDown,
        kCGEventKeyUp,
        kCGEventFlagsChanged,
        kCGHIDEventTap,
        kCGHeadInsertEventTap,
        kCGEventTapOptionDefault,
        CFMachPortCreateRunLoopSource,
        CFRunLoopAddSource,
        CFRunLoopGetCurrent,
        kCFRunLoopCommonModes,
        CGEventGetIntegerValueField,
        kCGKeyboardEventKeycode,
    )
    from AppKit import NSEvent
    HAS_QUARTZ = True
except ImportError:
    HAS_QUARTZ = False
    log.warning("Quartz not available - global hotkeys disabled")


# Key code mappings (macOS virtual key codes)
KEY_CODES = {
    # Letters
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4,
    "i": 34, "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35,
    "q": 12, "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7,
    "y": 16, "z": 6,
    # Numbers
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26,
    "8": 28, "9": 25,
    # Punctuation
    ".": 47, ",": 43, "/": 44, ";": 41, "'": 39,
    "[": 33, "]": 30, "-": 27, "=": 24, "`": 50, "\\": 42,
    # Special keys
    "space": 49, "return": 36, "escape": 53, "tab": 48, "delete": 51,
}

# Quartz modifier flags
MODIFIER_FLAGS = {
    "cmd": 1 << 20,    # Command
    "shift": 1 << 17,  # Shift
    "ctrl": 1 << 18,   # Control
    "alt": 1 << 19,    # Option/Alt
}

# Modifier-only key codes (macOS virtual key codes for individual modifier keys)
MODIFIER_KEY_CODES = {
    "right_cmd": 54,
    "left_cmd": 55,
    "right_shift": 60,
    "left_shift": 56,
    "right_option": 61,
    "left_option": 58,
    "right_ctrl": 62,
    "left_ctrl": 59,
}

# User-friendly name mappings -> MODIFIER_KEY_CODES keys
MODIFIER_KEY_NAMES = {
    "rightcmd": "right_cmd",
    "rightcommand": "right_cmd",
    "leftcmd": "left_cmd",
    "leftcommand": "left_cmd",
    "rightshift": "right_shift",
    "leftshift": "left_shift",
    "rightoption": "right_option",
    "rightalt": "right_option",
    "leftoption": "left_option",
    "leftalt": "left_option",
    "rightctrl": "right_ctrl",
    "rightcontrol": "right_ctrl",
    "leftctrl": "left_ctrl",
    "leftcontrol": "left_ctrl",
}


def is_modifier_only_hotkey(hotkey_str: str) -> bool:
    """Check if a hotkey string represents a modifier-only hotkey (e.g., 'RightCmd')."""
    normalized = hotkey_str.lower().replace(" ", "").replace("+", "").replace("_", "")
    return normalized in MODIFIER_KEY_NAMES


@dataclass
class Hotkey:
    """A registered hotkey."""
    key: str           # e.g., "space", "r"
    modifiers: list[str]  # e.g., ["cmd", "shift"]
    callback: Callable  # Called on key-down
    callback_up: Optional[Callable] = None  # Called on key-up (for push-to-talk)
    name: str = ""


class HotkeyManager:
    """
    Global hotkey manager using Quartz Event Taps.

    Supports modifier-only keys (e.g., RightCmd for push-to-talk) via
    kCGEventFlagsChanged, and standard key combos via kCGEventKeyDown/Up.
    """

    def __init__(self):
        self._hotkeys: dict[str, Hotkey] = {}
        self._modifier_hotkeys: dict[str, Hotkey] = {}
        self._pressed_keys: set[str] = set()
        self._pressed_key_codes: dict[int, str] = {}
        self._pressed_modifier_keys: set[int] = set()
        self._event_tap = None
        self._modifier_tap = None
        self._running = False

    def _parse_hotkey_string(self, hotkey_str: str) -> tuple[str, list[str]]:
        """Parse a hotkey string like "Cmd+Shift+Space" into key and modifiers."""
        # Check for modifier-only hotkey (e.g., "RightCmd", "LeftOption")
        normalized = hotkey_str.lower().replace(" ", "").replace("+", "").replace("_", "")
        if normalized in MODIFIER_KEY_NAMES:
            return MODIFIER_KEY_NAMES[normalized], []

        # Regular hotkey parsing
        parts = hotkey_str.lower().replace("+", " ").split()

        modifiers = []
        key = None

        for part in parts:
            if part in ("cmd", "command"):
                modifiers.append("cmd")
            elif part in ("shift",):
                modifiers.append("shift")
            elif part in ("ctrl", "control"):
                modifiers.append("ctrl")
            elif part in ("alt", "option", "opt"):
                modifiers.append("alt")
            else:
                key = part

        return key or "space", modifiers

    def _get_hotkey_id(self, key: str, modifiers: list[str]) -> str:
        """Generate a unique ID for a hotkey combination."""
        mods = "+".join(sorted(modifiers))
        return f"{mods}+{key}"

    def register(
        self,
        hotkey_str: str,
        callback: Callable,
        name: str = "",
        callback_up: Optional[Callable] = None
    ) -> bool:
        """Register a global hotkey."""
        if not HAS_QUARTZ:
            log.warning("Cannot register '%s' - Quartz not available", hotkey_str)
            return False

        key, modifiers = self._parse_hotkey_string(hotkey_str)

        # Modifier-only hotkeys (e.g., RightCmd) go to separate tracking
        if key in MODIFIER_KEY_CODES:
            hotkey = Hotkey(
                key=key, modifiers=[], callback=callback,
                callback_up=callback_up, name=name or hotkey_str
            )
            self._modifier_hotkeys[key] = hotkey
            log.debug("Registered modifier-only: %s (%s)", hotkey_str, name)
            return True

        # Regular hotkey registration
        hotkey_id = self._get_hotkey_id(key, modifiers)

        if key not in KEY_CODES:
            log.warning("Unknown key: %s", key)
            return False

        hotkey = Hotkey(
            key=key, modifiers=modifiers, callback=callback,
            callback_up=callback_up, name=name or hotkey_str
        )
        self._hotkeys[hotkey_id] = hotkey
        log.debug("Registered: %s (%s)", hotkey_str, name)
        return True

    def unregister(self, hotkey_str: str):
        """Unregister a hotkey."""
        key, modifiers = self._parse_hotkey_string(hotkey_str)

        if key in MODIFIER_KEY_CODES and key in self._modifier_hotkeys:
            del self._modifier_hotkeys[key]
            log.debug("Unregistered modifier: %s", hotkey_str)
            return

        hotkey_id = self._get_hotkey_id(key, modifiers)
        if hotkey_id in self._hotkeys:
            del self._hotkeys[hotkey_id]
            log.debug("Unregistered: %s", hotkey_str)

    def _check_modifiers(self, flags: int, required: list[str]) -> bool:
        """Check if the required modifiers are pressed."""
        for mod in required:
            if mod not in MODIFIER_FLAGS:
                continue
            if not (flags & MODIFIER_FLAGS[mod]):
                return False
        return True

    def _event_callback(self, proxy, event_type, event, refcon):
        """Callback for Quartz event tap (key down/up)."""
        if self._event_tap and not CGEventTapIsEnabled(self._event_tap):
            CGEventTapEnable(self._event_tap, True)

        if event_type not in (kCGEventKeyDown, kCGEventKeyUp):
            return event

        try:
            key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)

            # Handle key-up: check if this was a pressed hotkey
            if event_type == kCGEventKeyUp:
                if key_code in self._pressed_key_codes:
                    hotkey_id = self._pressed_key_codes.pop(key_code)
                    self._pressed_keys.discard(hotkey_id)

                    hotkey = self._hotkeys.get(hotkey_id)
                    if hotkey and hotkey.callback_up:
                        try:
                            hotkey.callback_up()
                        except Exception as e:
                            log.error("Key-up callback error: %s", e)

                    return None  # Consume key-up
                return event

            # Key-down: match hotkey
            flags = NSEvent.modifierFlags()

            for hotkey_id, hotkey in self._hotkeys.items():
                expected_key_code = KEY_CODES.get(hotkey.key)

                if key_code == expected_key_code:
                    if self._check_modifiers(flags, hotkey.modifiers):
                        if hotkey_id in self._pressed_keys:
                            return None  # Ignore key repeat

                        self._pressed_keys.add(hotkey_id)
                        self._pressed_key_codes[key_code] = hotkey_id

                        try:
                            hotkey.callback()
                        except Exception as e:
                            log.error("Key-down callback error: %s", e)

                        return None  # Consume the event

        except Exception as e:
            log.error("Event processing error: %s", e)

        return event

    def _modifier_event_callback(self, proxy, event_type, event, refcon):
        """Handle kCGEventFlagsChanged events for modifier-only hotkeys."""
        if self._modifier_tap and not CGEventTapIsEnabled(self._modifier_tap):
            CGEventTapEnable(self._modifier_tap, True)

        if event_type != kCGEventFlagsChanged:
            return event

        try:
            keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)

            for hotkey_id, hotkey in self._modifier_hotkeys.items():
                expected_keycode = MODIFIER_KEY_CODES.get(hotkey.key)

                if keycode == expected_keycode:
                    if keycode in self._pressed_modifier_keys:
                        # Key released
                        self._pressed_modifier_keys.discard(keycode)
                        if hotkey.callback_up:
                            try:
                                hotkey.callback_up()
                            except Exception as e:
                                log.error("Modifier key-up error: %s", e)
                    else:
                        # Key pressed
                        self._pressed_modifier_keys.add(keycode)
                        try:
                            hotkey.callback()
                        except Exception as e:
                            log.error("Modifier key-down error: %s", e)
                    break

        except Exception as e:
            log.error("Modifier event error: %s", e)

        # Never consume modifier events
        return event

    def start(self) -> bool:
        """Start listening for global hotkeys."""
        if self._running:
            return True

        if not HAS_QUARTZ:
            return False

        success = False

        # Start key event tap for regular hotkeys
        if self._hotkeys:
            success = self._start_key_tap()

        # Start modifier tap for modifier-only hotkeys (e.g., RightCmd)
        if self._modifier_hotkeys:
            modifier_ok = self._start_modifier_tap()
            if not success:
                success = modifier_ok

        return success

    def _start_key_tap(self) -> bool:
        """Start Quartz EventTap for key down/up events."""
        try:
            self._event_tap = CGEventTapCreate(
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionDefault,
                CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp),
                self._event_callback,
                None
            )

            if not self._event_tap:
                log.error("Failed to create event tap - check Accessibility permission")
                return False

            CGEventTapEnable(self._event_tap, True)
            source = CFMachPortCreateRunLoopSource(None, self._event_tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)

            self._running = True
            log.debug("Key event tap started")
            return True

        except Exception as e:
            log.error("Error starting key tap: %s", e)
            return False

    def _start_modifier_tap(self) -> bool:
        """Start Quartz EventTap for modifier-only hotkeys."""
        try:
            self._modifier_tap = CGEventTapCreate(
                kCGHIDEventTap,
                kCGHeadInsertEventTap,
                kCGEventTapOptionDefault,
                CGEventMaskBit(kCGEventFlagsChanged),
                self._modifier_event_callback,
                None
            )

            if not self._modifier_tap:
                log.error("Failed to create modifier tap - check Accessibility permission")
                return False

            CGEventTapEnable(self._modifier_tap, True)
            source = CFMachPortCreateRunLoopSource(None, self._modifier_tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)

            self._running = True
            log.debug("Modifier tap started")
            return True

        except Exception as e:
            log.error("Error starting modifier tap: %s", e)
            return False

    def stop(self):
        """Stop listening for global hotkeys."""
        if self._event_tap:
            CGEventTapEnable(self._event_tap, False)
            self._event_tap = None

        if self._modifier_tap:
            CGEventTapEnable(self._modifier_tap, False)
            self._modifier_tap = None

        self._pressed_modifier_keys.clear()
        self._pressed_keys.clear()
        self._pressed_key_codes.clear()
        self._running = False
        log.debug("Stopped")

    @property
    def is_running(self) -> bool:
        return self._running
