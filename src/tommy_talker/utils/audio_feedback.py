"""
TommyTalker Audio Feedback
Sound effects for recording start/stop feedback with variation.
"""

import logging
import subprocess
from pathlib import Path

log = logging.getLogger("TommyTalker")


class AudioFeedback:
    """
    Play audio feedback sounds using macOS system sounds.
    Uses afplay for reliable non-blocking playback.

    When variation is enabled, rotates through sound pools using round-robin
    to prevent repetition fatigue.
    """

    # System sound paths on macOS
    SYSTEM_SOUNDS = Path("/System/Library/Sounds")

    # Sound pools
    START_POOL = ["Blow.aiff"]
    STOP_POOL = ["Blow.aiff"]
    NO_RESULT_POOL = ["Frog.aiff", "Submarine.aiff"]
    ERROR_POOL = ["Basso.aiff", "Funk.aiff", "Sosumi.aiff"]

    def __init__(self, enabled: bool = True, vary_sounds: bool = True):
        self.enabled = enabled
        self.vary_sounds = vary_sounds

        # Round-robin indices
        self._start_idx = 0
        self._stop_idx = 0
        self._no_result_idx = 0
        self._error_idx = 0

        # Validate and filter pools to existing sounds
        self._start_sounds = self._validate_pool(self.START_POOL)
        self._stop_sounds = self._validate_pool(self.STOP_POOL)
        self._no_result_sounds = self._validate_pool(self.NO_RESULT_POOL)
        self._error_sounds = self._validate_pool(self.ERROR_POOL)

    def _validate_pool(self, pool: list[str]) -> list[Path]:
        """Filter a sound pool to only sounds that exist on the system."""
        valid = []
        for name in pool:
            path = self.SYSTEM_SOUNDS / name
            if path.exists():
                valid.append(path)
        if not valid:
            log.warning("No sounds found from pool %s", pool)
        return valid

    def _next_sound(self, pool: list[Path], idx_attr: str) -> Path | None:
        """Get the next sound from a pool using round-robin."""
        if not pool:
            return None

        if not self.vary_sounds:
            return pool[0]

        idx = getattr(self, idx_attr)
        sound = pool[idx % len(pool)]
        setattr(self, idx_attr, idx + 1)
        return sound

    def _play_async(self, sound_path: Path | None):
        """Play a sound asynchronously (non-blocking)."""
        if not self.enabled or sound_path is None:
            return

        if not sound_path.exists():
            return

        try:
            subprocess.Popen(
                ["afplay", "-v", "0.5", str(sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            log.error("Error playing sound: %s", e)

    def play_start(self):
        """Play recording start sound."""
        self._play_async(self._next_sound(self._start_sounds, "_start_idx"))

    def play_stop(self):
        """Play recording stop sound."""
        self._play_async(self._next_sound(self._stop_sounds, "_stop_idx"))

    def play_no_result(self):
        """Play distinct sound for empty transcription (no speech detected)."""
        self._play_async(self._next_sound(self._no_result_sounds, "_no_result_idx"))

    def play_error(self):
        """Play error sound."""
        self._play_async(self._next_sound(self._error_sounds, "_error_idx"))


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
