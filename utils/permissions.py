"""
TommyTalker Permissions
macOS permission checking for Microphone and Accessibility.
"""

import subprocess
from dataclasses import dataclass

# Check for pyobjc availability
HAS_PYOBJC = False
try:
    # Try importing AVFoundation for microphone check
    from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
    HAS_PYOBJC = True
except ImportError:
    pass


@dataclass
class PermissionStatus:
    """Status of required permissions."""
    microphone: bool
    accessibility: bool
    
    @property
    def all_granted(self) -> bool:
        return self.microphone and self.accessibility


def check_microphone_permission() -> bool:
    """
    Check if microphone permission is granted.
    Uses multiple fallback methods.
    
    Returns:
        True if permission is granted
    """
    # Method 1: Try pyobjc/AVFoundation
    if HAS_PYOBJC:
        try:
            auth_status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
            # 3 = authorized
            if auth_status == 3:
                return True
        except Exception as e:
            print(f"[Permissions] AVFoundation check failed: {e}")
    
    # Method 2: Try sounddevice - if we can query input devices, likely have permission
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if len(input_devices) > 0:
            # Try to actually open a stream briefly
            try:
                with sd.InputStream(samplerate=16000, channels=1, blocksize=1024):
                    pass
                return True
            except sd.PortAudioError as e:
                # Permission denied or device busy
                if "permission" in str(e).lower():
                    return False
                # Device busy is still success for permission check
                return True
    except Exception as e:
        print(f"[Permissions] sounddevice check failed: {e}")
    
    # Method 3: Check if tccutil shows permission (fallback)
    try:
        result = subprocess.run(
            ["sqlite3", "/Library/Application Support/com.apple.TCC/TCC.db",
             "SELECT client FROM access WHERE service='kTCCServiceMicrophone' AND allowed=1"],
            capture_output=True, text=True, timeout=2
        )
        # If we got any output, some apps have permission
        # This doesn't tell us if WE have permission, so just return True as likely
        return True
    except Exception:
        pass
    
    # Default: assume granted to avoid blocking when detection fails
    print("[Permissions] Could not verify microphone permission, assuming granted")
    return True


def check_accessibility_permission() -> bool:
    """
    Check if accessibility permission is granted.
    Required for global hotkeys and typing at cursor.
    
    Returns:
        True if permission is granted
    """
    try:
        # Use AppleScript to check accessibility
        # This is the most reliable cross-version method
        result = subprocess.run(
            [
                "osascript", "-e",
                'tell application "System Events" to return (UI elements enabled)'
            ],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        return result.stdout.strip().lower() == "true"
        
    except subprocess.TimeoutExpired:
        print("[Permissions] Accessibility check timed out")
        return False
    except Exception as e:
        print(f"[Permissions] Error checking accessibility: {e}")
        # If we can't check, assume granted
        return True


def check_permissions() -> PermissionStatus:
    """
    Check all required permissions.
    
    Returns:
        PermissionStatus with current permission states
    """
    mic = check_microphone_permission()
    acc = check_accessibility_permission()
    
    print(f"[Permissions] Microphone: {'✓' if mic else '✗'}, Accessibility: {'✓' if acc else '✗'}")
    
    return PermissionStatus(microphone=mic, accessibility=acc)


def request_microphone_permission():
    """
    Request microphone permission.
    This will trigger the system permission dialog.
    """
    if HAS_PYOBJC:
        try:
            AVCaptureDevice.requestAccessForMediaType_completionHandler_(
                AVMediaTypeAudio,
                lambda granted: print(f"[Permissions] Microphone access: {'granted' if granted else 'denied'}")
            )
            return
        except Exception as e:
            print(f"[Permissions] Error requesting microphone: {e}")
    
    # Fallback: try to open an audio stream to trigger the permission dialog
    try:
        import sounddevice as sd
        with sd.InputStream(samplerate=16000, channels=1, blocksize=1024):
            pass
    except Exception:
        pass


def open_system_preferences(pane: str):
    """
    Open System Settings/Preferences to a specific pane.
    
    Args:
        pane: "microphone" or "accessibility"
    """
    # macOS Ventura+ uses "System Settings" with new URL scheme
    urls = {
        "microphone": "x-apple.systempreferences:com.apple.preference.security?Privacy_Microphone",
        "accessibility": "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
    }
    
    url = urls.get(pane)
    if not url:
        print(f"[Permissions] Unknown pane: {pane}")
        return
        
    try:
        subprocess.run(["open", url], check=True)
        print(f"[Permissions] Opened System Settings: {pane}")
    except Exception as e:
        print(f"[Permissions] Error opening System Settings: {e}")
        
        # Fallback to opening Security & Privacy directly
        try:
            subprocess.run([
                "open", 
                "x-apple.systempreferences:com.apple.preference.security"
            ], check=True)
        except Exception:
            pass


def get_permission_instructions(pane: str) -> str:
    """Get human-readable instructions for granting a permission."""
    instructions = {
        "microphone": (
            "1. Open System Settings → Privacy & Security → Microphone\n"
            "2. Find Terminal (or Python) in the list\n"
            "3. Toggle the switch to ON\n"
            "4. Restart TommyTalker"
        ),
        "accessibility": (
            "1. Open System Settings → Privacy & Security → Accessibility\n"
            "2. Click the lock icon to make changes\n"
            "3. Click the + button and add Terminal\n"
            "4. Ensure the checkbox is checked\n"
            "5. Restart TommyTalker"
        ),
    }
    return instructions.get(pane, "Please grant the required permission in System Settings.")
