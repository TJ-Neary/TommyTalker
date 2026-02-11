"""
Tests for audio feedback system with sound pool variation.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

from tommy_talker.utils.audio_feedback import AudioFeedback, get_audio_feedback


class TestSoundPoolValidation:
    """Test sound pool validation against system sounds."""

    def test_start_pool_has_sounds(self):
        """Start sound pool has at least one valid sound."""
        af = AudioFeedback(enabled=False)
        assert len(af._start_sounds) > 0

    def test_stop_pool_has_sounds(self):
        """Stop sound pool has at least one valid sound."""
        af = AudioFeedback(enabled=False)
        assert len(af._stop_sounds) > 0

    def test_error_pool_has_sounds(self):
        """Error sound pool has at least one valid sound."""
        af = AudioFeedback(enabled=False)
        assert len(af._error_sounds) > 0

    def test_no_result_pool_has_sounds(self):
        """No-result sound pool has at least one valid sound."""
        af = AudioFeedback(enabled=False)
        assert len(af._no_result_sounds) > 0

    def test_missing_sounds_filtered(self):
        """Sounds that don't exist on the system are filtered out."""
        af = AudioFeedback(enabled=False)
        fake_pool = af._validate_pool(["NonExistent.aiff", "AlsoFake.aiff"])
        assert len(fake_pool) == 0


class TestRoundRobin:
    """Test round-robin sound rotation."""

    def test_rotation_cycles_through_pool(self):
        """Round-robin cycles through all sounds in the pool."""
        af = AudioFeedback(enabled=False, vary_sounds=True)
        pool_size = len(af._start_sounds)
        assert pool_size > 1, "Need multiple sounds to test rotation"

        sounds = []
        for _ in range(pool_size):
            s = af._next_sound(af._start_sounds, "_start_idx")
            sounds.append(s)

        # All sounds in pool should have been used
        assert len(set(sounds)) == pool_size

    def test_rotation_wraps_around(self):
        """Round-robin wraps around after exhausting pool."""
        af = AudioFeedback(enabled=False, vary_sounds=True)
        pool_size = len(af._start_sounds)

        first = af._next_sound(af._start_sounds, "_start_idx")
        for _ in range(pool_size - 1):
            af._next_sound(af._start_sounds, "_start_idx")
        wrap = af._next_sound(af._start_sounds, "_start_idx")

        assert first == wrap, "Should wrap around to first sound"


class TestNoVariation:
    """Test no-variation mode (always same sound)."""

    def test_no_variation_returns_first_sound(self):
        """With vary_sounds=False, always returns first sound."""
        af = AudioFeedback(enabled=False, vary_sounds=False)
        sounds = set()
        for _ in range(5):
            s = af._next_sound(af._start_sounds, "_start_idx")
            sounds.add(s)
        assert len(sounds) == 1, "No-variation should always return same sound"


class TestPlayMethods:
    """Test play methods exist and handle disabled state."""

    def test_play_start_exists(self):
        af = AudioFeedback(enabled=False)
        af.play_start()  # Should not raise

    def test_play_stop_exists(self):
        af = AudioFeedback(enabled=False)
        af.play_stop()

    def test_play_no_result_exists(self):
        af = AudioFeedback(enabled=False)
        af.play_no_result()

    def test_play_error_exists(self):
        af = AudioFeedback(enabled=False)
        af.play_error()

    def test_disabled_plays_nothing(self):
        """When disabled, _play_async should not spawn processes."""
        af = AudioFeedback(enabled=False)
        with patch("tommy_talker.utils.audio_feedback.subprocess.Popen") as mock_popen:
            af.play_start()
            af.play_stop()
            af.play_error()
            af.play_no_result()
            mock_popen.assert_not_called()


class TestGlobalInstance:
    """Test global singleton behavior."""

    def test_get_audio_feedback_returns_instance(self):
        instance = get_audio_feedback()
        assert isinstance(instance, AudioFeedback)

    def test_get_audio_feedback_returns_same_instance(self):
        a = get_audio_feedback()
        b = get_audio_feedback()
        assert a is b
