"""
TommyTalker Audio Feedback
Simple sound effects for recording start/stop feedback.
"""

import subprocess
from pathlib import Path


class AudioFeedback:
    """
    Play audio feedback sounds using macOS system sounds.
    Uses afplay for reliable non-blocking playback.
    """
    
    # System sound paths on macOS
    SYSTEM_SOUNDS = Path("/System/Library/Sounds")
    
    # Sound mappings
    START_SOUND = "Tink.aiff"      # Short, crisp sound for start
    STOP_SOUND = "Pop.aiff"        # Different sound for stop
    ERROR_SOUND = "Basso.aiff"     # Error/warning sound
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._check_sounds()
        
    def _check_sounds(self):
        """Check if system sounds exist."""
        self._start_path = self.SYSTEM_SOUNDS / self.START_SOUND
        self._stop_path = self.SYSTEM_SOUNDS / self.STOP_SOUND
        self._error_path = self.SYSTEM_SOUNDS / self.ERROR_SOUND
        
        if not self._start_path.exists():
            print(f"[AudioFeedback] Warning: Start sound not found at {self._start_path}")
            
    def _play_async(self, sound_path: Path):
        """Play a sound asynchronously (non-blocking)."""
        if not self.enabled:
            return
            
        if not sound_path.exists():
            return
            
        try:
            # Use afplay with low volume so it's subtle
            subprocess.Popen(
                ["afplay", "-v", "0.5", str(sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            print(f"[AudioFeedback] Error playing sound: {e}")
            
    def play_start(self):
        """Play recording start sound."""
        self._play_async(self._start_path)
        
    def play_stop(self):
        """Play recording stop sound."""
        self._play_async(self._stop_path)
        
    def play_error(self):
        """Play error sound."""
        self._play_async(self._error_path)


# Global instance
_audio_feedback: AudioFeedback | None = None


def get_audio_feedback() -> AudioFeedback:
    """Get the global audio feedback instance."""
    global _audio_feedback
    if _audio_feedback is None:
        _audio_feedback = AudioFeedback()
    return _audio_feedback


def set_audio_feedback_enabled(enabled: bool):
    """Enable or disable audio feedback globally."""
    get_audio_feedback().enabled = enabled
