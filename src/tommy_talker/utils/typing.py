"""
TommyTalker Typing Utility
Type text at cursor position using pyautogui.
Also handles clipboard paste for longer text.
"""

import time
from typing import Optional

# pyautogui for typing at cursor
try:
    import pyautogui
    HAS_PYAUTOGUI = True
    
    # Safety settings
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.01     # Small pause between actions
except ImportError:
    HAS_PYAUTOGUI = False
    print("[WARNING] pyautogui not installed - typing disabled")

# For clipboard operations
try:
    import subprocess
    HAS_PBCOPY = True
except Exception:
    HAS_PBCOPY = False


class TypingController:
    """
    Controller for typing text at the cursor position.
    
    Features:
    - Direct typing for short text (< 100 chars)
    - Clipboard paste for longer text (faster, more reliable)
    - Support for special characters
    """
    
    # Threshold for switching to clipboard paste
    PASTE_THRESHOLD = 100
    
    # Typing speed (interval between characters)
    TYPING_INTERVAL = 0.02
    
    def __init__(self):
        if not HAS_PYAUTOGUI:
            print("[TypingController] pyautogui not available")
            
    def type_text(self, text: str, use_clipboard: Optional[bool] = None) -> bool:
        """
        Type text at the current cursor position.
        
        Args:
            text: Text to type
            use_clipboard: Force clipboard paste (None = auto-decide)
            
        Returns:
            True if successful
        """
        if not text:
            return True
            
        if not HAS_PYAUTOGUI:
            print(f"[TypingController] Would type: {text[:50]}...")
            return False
            
        # Decide whether to use clipboard
        if use_clipboard is None:
            use_clipboard = len(text) > self.PASTE_THRESHOLD
            
        try:
            if use_clipboard:
                return self._paste_from_clipboard(text)
            else:
                return self._type_directly(text)
                
        except Exception as e:
            print(f"[TypingController] Error typing: {e}")
            return False
            
    def _type_directly(self, text: str) -> bool:
        """Type text character by character."""
        try:
            # Use typewrite for basic ASCII
            # Use write for unicode support
            pyautogui.write(text, interval=self.TYPING_INTERVAL)
            return True
        except Exception as e:
            print(f"[TypingController] Direct typing failed: {e}")
            # Fallback to clipboard
            return self._paste_from_clipboard(text)
            
    def _paste_from_clipboard(self, text: str) -> bool:
        """Copy text to clipboard and paste."""
        try:
            # Copy to clipboard using pbcopy (macOS)
            process = subprocess.Popen(
                ['pbcopy'],
                stdin=subprocess.PIPE,
                env={'LANG': 'en_US.UTF-8'}
            )
            process.communicate(text.encode('utf-8'))
            
            # Small delay to ensure clipboard is ready
            time.sleep(0.05)
            
            # Paste using Cmd+V
            pyautogui.hotkey('command', 'v')
            
            return True
            
        except Exception as e:
            print(f"[TypingController] Clipboard paste failed: {e}")
            return False
            
    def press_key(self, key: str) -> bool:
        """Press a single key."""
        if not HAS_PYAUTOGUI:
            return False
            
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            print(f"[TypingController] Key press failed: {e}")
            return False
            
    def hotkey(self, *keys: str) -> bool:
        """Press a hotkey combination."""
        if not HAS_PYAUTOGUI:
            return False
            
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            print(f"[TypingController] Hotkey failed: {e}")
            return False


# Global instance
_typing_controller: Optional[TypingController] = None


def get_typing_controller() -> TypingController:
    """Get the global typing controller instance."""
    global _typing_controller
    if _typing_controller is None:
        _typing_controller = TypingController()
    return _typing_controller


def type_at_cursor(text: str) -> bool:
    """Convenience function to type text at cursor."""
    return get_typing_controller().type_text(text)


def paste_text(text: str) -> bool:
    """Convenience function to paste text via clipboard."""
    return get_typing_controller().type_text(text, use_clipboard=True)
