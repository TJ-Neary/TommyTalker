"""
TommyTalker Hotkeys
Global hotkey registration using Carbon HIToolbox RegisterEventHotKey.

Based on QuickMacHotKey pattern (https://github.com/glyph/QuickMacHotKey)
which properly consumes events and doesn't leak keystrokes to apps.
"""

from typing import Callable, Optional
from dataclasses import dataclass

# Try to import pyobjc Carbon functions
try:
    import objc
    from Foundation import NSObject
    from Carbon import (
        RegisterEventHotKey,
        UnregisterEventHotKey,
        GetEventDispatcherTarget,
        InstallEventHandler,
        GetEventParameter,
        kEventClassKeyboard,
        kEventHotKeyPressed,
        kEventHotKeyReleased,
    )
    HAS_CARBON = True
except ImportError:
    HAS_CARBON = False
    print("[WARNING] Carbon hotkeys not available - falling back to event tap")

# Always import Quartz — needed for modifier-only hotkeys AND as fallback for regular hotkeys
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
    if not HAS_CARBON:
        print("[WARNING] Neither Carbon nor Quartz available - global hotkeys disabled")


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
    ".": 47,   # Period
    ",": 43,   # Comma
    "/": 44,   # Slash
    ";": 41,   # Semicolon
    "'": 39,   # Quote
    "[": 33,   # Left bracket
    "]": 30,   # Right bracket
    "-": 27,   # Minus
    "=": 24,   # Equals
    "`": 50,   # Backtick
    "\\": 42,  # Backslash
    # Special keys
    "space": 49,
    "return": 36,
    "escape": 53,
    "tab": 48,
    "delete": 51,
}

# Carbon modifier masks
CARBON_MODIFIERS = {
    "cmd": 0x0100,      # cmdKey
    "shift": 0x0200,    # shiftKey
    "alt": 0x0800,      # optionKey
    "ctrl": 0x1000,     # controlKey
}

# Quartz modifier flags (fallback)
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

# User-friendly name mappings → MODIFIER_KEY_CODES keys
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
    name: str = ""          # Human-readable name
    ref: object = None      # Carbon hotkey reference


class HotkeyManager:
    """
    Global hotkey manager.
    
    Uses Carbon RegisterEventHotKey if available (preferred, consumes events properly).
    Falls back to Quartz Event Taps if Carbon isn't available.
    """
    
    def __init__(self):
        self._hotkeys: dict[str, Hotkey] = {}
        self._modifier_hotkeys: dict[str, Hotkey] = {}  # Modifier-only hotkeys
        self._hotkey_refs: dict[int, str] = {}  # Maps hotkey ID to hotkey_id string
        self._pressed_keys: set[str] = set()  # Track currently pressed hotkeys
        self._pressed_key_codes: dict[int, str] = {}  # For fallback mode
        self._pressed_modifier_keys: set[int] = set()  # Track pressed modifier keycodes
        self._event_tap = None
        self._modifier_tap = None  # Separate tap for modifier-only hotkeys
        self._event_handler = None
        self._running = False
        self._next_hotkey_id = 1

        if HAS_CARBON:
            print("[HotkeyManager] Using Carbon RegisterEventHotKey (preferred)")
        elif HAS_QUARTZ:
            print("[HotkeyManager] Using Quartz EventTap (fallback)")
        else:
            print("[HotkeyManager] No hotkey support available")
            
    def _parse_hotkey_string(self, hotkey_str: str) -> tuple[str, list[str]]:
        """
        Parse a hotkey string like "Cmd+Shift+Space" into key and modifiers.
        Also handles modifier-only strings like "RightCmd".

        Returns:
            (key, [modifiers]) — for modifier-only hotkeys, key is in MODIFIER_KEY_CODES
        """
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
    
    def _get_carbon_modifier_mask(self, modifiers: list[str]) -> int:
        """Convert modifier list to Carbon modifier mask."""
        mask = 0
        for mod in modifiers:
            if mod in CARBON_MODIFIERS:
                mask |= CARBON_MODIFIERS[mod]
        return mask
        
    def register(
        self,
        hotkey_str: str,
        callback: Callable,
        name: str = "",
        callback_up: Optional[Callable] = None
    ) -> bool:
        """
        Register a global hotkey.

        Args:
            hotkey_str: Hotkey string like "Cmd+Shift+Space" or "RightCmd"
            callback: Function to call when hotkey is pressed
            name: Human-readable name for the hotkey
            callback_up: Optional function to call when hotkey is released

        Returns:
            True if registered successfully
        """
        if not HAS_CARBON and not HAS_QUARTZ:
            print(f"[HotkeyManager] Cannot register '{hotkey_str}' - no hotkey support")
            return False

        key, modifiers = self._parse_hotkey_string(hotkey_str)

        # Modifier-only hotkeys (e.g., RightCmd) go to separate tracking
        if key in MODIFIER_KEY_CODES:
            if not HAS_QUARTZ:
                print(f"[HotkeyManager] Cannot register modifier-only '{hotkey_str}' - Quartz not available")
                return False
            hotkey = Hotkey(
                key=key,
                modifiers=[],
                callback=callback,
                callback_up=callback_up,
                name=name or hotkey_str
            )
            self._modifier_hotkeys[key] = hotkey
            print(f"[HotkeyManager] Registered modifier-only: {hotkey_str} ({name})")
            return True

        # Regular hotkey registration
        hotkey_id = self._get_hotkey_id(key, modifiers)

        if key not in KEY_CODES:
            print(f"[HotkeyManager] Unknown key: {key}")
            return False

        hotkey = Hotkey(
            key=key,
            modifiers=modifiers,
            callback=callback,
            callback_up=callback_up,
            name=name or hotkey_str
        )

        # For Carbon, register immediately if already running
        if HAS_CARBON and self._running:
            if not self._register_carbon_hotkey(hotkey, self._next_hotkey_id):
                return False
            self._hotkey_refs[self._next_hotkey_id] = hotkey_id
            self._next_hotkey_id += 1

        self._hotkeys[hotkey_id] = hotkey
        print(f"[HotkeyManager] Registered: {hotkey_str} ({name})")
        return True
    
    def _register_carbon_hotkey(self, hotkey: Hotkey, numeric_id: int) -> bool:
        """Register a single hotkey with Carbon."""
        if not HAS_CARBON:
            return False
            
        key_code = KEY_CODES.get(hotkey.key)
        mod_mask = self._get_carbon_modifier_mask(hotkey.modifiers)
        
        # Signature 'TMTK' (TommyTalker)
        signature = 0x544D544B
        hotkey_id = (signature, numeric_id)
        
        try:
            result, ref = RegisterEventHotKey(
                key_code,
                mod_mask,
                hotkey_id,
                GetEventDispatcherTarget(),
                0,
                None
            )
            
            if result == 0:
                hotkey.ref = ref
                return True
            else:
                print(f"[HotkeyManager] Failed to register Carbon hotkey: {result}")
                return False
        except Exception as e:
            print(f"[HotkeyManager] Carbon registration error: {e}")
            return False
        
    def unregister(self, hotkey_str: str):
        """Unregister a hotkey."""
        key, modifiers = self._parse_hotkey_string(hotkey_str)
        hotkey_id = self._get_hotkey_id(key, modifiers)
        
        if hotkey_id in self._hotkeys:
            hotkey = self._hotkeys[hotkey_id]
            
            # Unregister from Carbon if applicable
            if HAS_CARBON and hotkey.ref:
                try:
                    UnregisterEventHotKey(hotkey.ref)
                except Exception as e:
                    print(f"[HotkeyManager] Error unregistering: {e}")
                    
            del self._hotkeys[hotkey_id]
            print(f"[HotkeyManager] Unregistered: {hotkey_str}")
            
    def _check_modifiers(self, flags: int, required: list[str]) -> bool:
        """Check if the required modifiers are pressed (for fallback mode)."""
        for mod in required:
            if mod not in MODIFIER_FLAGS:
                continue
            if not (flags & MODIFIER_FLAGS[mod]):
                return False
        return True
        
    def _event_callback(self, proxy, event_type, event, refcon):
        """Callback for Quartz event tap (fallback mode)."""
        # Re-enable event tap if it was auto-disabled by macOS
        if self._event_tap and not CGEventTapIsEnabled(self._event_tap):
            print("[HotkeyManager] Re-enabling event tap")
            CGEventTapEnable(self._event_tap, True)
        
        if event_type not in (kCGEventKeyDown, kCGEventKeyUp):
            return event
            
        try:
            # Get key code
            key_code = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
            
            # Handle key-up first - check if this was a pressed hotkey
            if event_type == kCGEventKeyUp:
                if key_code in self._pressed_key_codes:
                    hotkey_id = self._pressed_key_codes.pop(key_code)
                    self._pressed_keys.discard(hotkey_id)
                    
                    hotkey = self._hotkeys.get(hotkey_id)
                    if hotkey and hotkey.callback_up:
                        try:
                            hotkey.callback_up()
                        except Exception as e:
                            print(f"[HotkeyManager] Key-up callback error: {e}")
                    
                    return None  # Consume key-up
                return event  # Not our key-up
            
            # Key-down: Get modifier flags and match hotkey
            flags = NSEvent.modifierFlags()
            
            for hotkey_id, hotkey in self._hotkeys.items():
                expected_key_code = KEY_CODES.get(hotkey.key)
                
                if key_code == expected_key_code:
                    if self._check_modifiers(flags, hotkey.modifiers):
                        # Check if already pressed (key repeat)
                        if hotkey_id in self._pressed_keys:
                            return None  # Ignore key repeat, but consume event
                        
                        self._pressed_keys.add(hotkey_id)
                        self._pressed_key_codes[key_code] = hotkey_id  # Track for key-up
                        
                        # Execute key-down callback
                        try:
                            hotkey.callback()
                        except Exception as e:
                            print(f"[HotkeyManager] Key-down callback error: {e}")
                            
                        return None  # Consume the event
                        
        except Exception as e:
            print(f"[HotkeyManager] Event processing error: {e}")
            
        return event
        
    def start(self) -> bool:
        """
        Start listening for global hotkeys.

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        if HAS_CARBON:
            result = self._start_carbon()
        elif HAS_QUARTZ:
            result = self._start_quartz()
        else:
            result = False

        # Start modifier tap for modifier-only hotkeys (works alongside Carbon)
        if self._modifier_hotkeys and HAS_QUARTZ:
            modifier_result = self._start_modifier_tap()
            if not result:
                result = modifier_result

        return result
            
    def _start_carbon(self) -> bool:
        """Start Carbon-based hotkey listening."""
        # Note: Carbon RegisterEventHotKey works with the main run loop
        # For now, register all hotkeys
        numeric_id = 1
        for hotkey_id, hotkey in self._hotkeys.items():
            if self._register_carbon_hotkey(hotkey, numeric_id):
                self._hotkey_refs[numeric_id] = hotkey_id
                numeric_id += 1
                
        self._next_hotkey_id = numeric_id
        self._running = True
        print("[HotkeyManager] Started listening for hotkeys (Carbon)")
        return True
        
    def _start_quartz(self) -> bool:
        """Start Quartz EventTap-based hotkey listening (fallback)."""
        try:
            # Create event tap for both key-down and key-up
            self._event_tap = CGEventTapCreate(
                kCGHIDEventTap,           # Tap location
                kCGHeadInsertEventTap,    # Placement
                kCGEventTapOptionDefault,  # Options
                CGEventMaskBit(kCGEventKeyDown) | CGEventMaskBit(kCGEventKeyUp),
                self._event_callback,     # Callback
                None                      # User info
            )

            if not self._event_tap:
                print("[HotkeyManager] Failed to create event tap - check Accessibility permission")
                return False

            # Enable the tap
            CGEventTapEnable(self._event_tap, True)

            # Add to run loop
            source = CFMachPortCreateRunLoopSource(None, self._event_tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)

            self._running = True
            print("[HotkeyManager] Started listening for hotkeys (Quartz fallback)")
            return True

        except Exception as e:
            print(f"[HotkeyManager] Error starting: {e}")
            return False

    def _start_modifier_tap(self) -> bool:
        """Start a Quartz event tap for modifier-only hotkeys (e.g., RightCmd)."""
        if not HAS_QUARTZ:
            print("[HotkeyManager] Quartz not available for modifier-only hotkeys")
            return False

        if not self._modifier_hotkeys:
            return True  # Nothing to listen for

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
                print("[HotkeyManager] Failed to create modifier event tap - check Accessibility permission")
                return False

            CGEventTapEnable(self._modifier_tap, True)

            source = CFMachPortCreateRunLoopSource(None, self._modifier_tap, 0)
            CFRunLoopAddSource(CFRunLoopGetCurrent(), source, kCFRunLoopCommonModes)

            print("[HotkeyManager] Modifier tap started for modifier-only hotkeys")
            return True

        except Exception as e:
            print(f"[HotkeyManager] Error starting modifier tap: {e}")
            return False

    def _modifier_event_callback(self, proxy, event_type, event, refcon):
        """Handle kCGEventFlagsChanged events for modifier-only hotkeys."""
        # Re-enable tap if macOS auto-disabled it
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
                        # Key was pressed, now released
                        self._pressed_modifier_keys.discard(keycode)
                        if hotkey.callback_up:
                            try:
                                hotkey.callback_up()
                            except Exception as e:
                                print(f"[HotkeyManager] Modifier key-up error: {e}")
                    else:
                        # Key pressed
                        self._pressed_modifier_keys.add(keycode)
                        try:
                            hotkey.callback()
                        except Exception as e:
                            print(f"[HotkeyManager] Modifier key-down error: {e}")
                    break

        except Exception as e:
            print(f"[HotkeyManager] Modifier event error: {e}")

        # Never consume modifier events — they must flow to the system
        return event

    def stop(self):
        """Stop listening for global hotkeys."""
        if HAS_CARBON:
            # Unregister all Carbon hotkeys
            for hotkey in self._hotkeys.values():
                if hotkey.ref:
                    try:
                        UnregisterEventHotKey(hotkey.ref)
                        hotkey.ref = None
                    except:
                        pass

        if self._event_tap:
            CGEventTapEnable(self._event_tap, False)
            self._event_tap = None

        # Stop modifier tap
        if self._modifier_tap:
            CGEventTapEnable(self._modifier_tap, False)
            self._modifier_tap = None
        self._pressed_modifier_keys.clear()

        self._running = False
        print("[HotkeyManager] Stopped listening for hotkeys")
        
    @property
    def is_running(self) -> bool:
        return self._running
