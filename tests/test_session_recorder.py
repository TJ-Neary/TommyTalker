"""
Tests for SessionRecorder — session recording to WAV files.
"""

import re
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest

from tommy_talker.engine.audio_capture import (
    AudioCapture,
    AudioChunk,
    SessionRecorder,
    RECORDINGS_DIR,
)
from tommy_talker.utils.config import UserConfig, load_config, save_config


# ── SessionRecorder Lifecycle ─────────────────────────────────


class TestSessionRecorderInit:
    def test_default_source_mode(self):
        rec = SessionRecorder()
        assert rec.source_mode == "mic"

    def test_default_sample_rate(self):
        rec = SessionRecorder()
        assert rec.sample_rate == 44100

    def test_custom_source_mode(self):
        rec = SessionRecorder(source_mode="system_and_mic")
        assert rec.source_mode == "system_and_mic"

    def test_not_recording_initially(self):
        rec = SessionRecorder()
        assert rec.is_recording is False

    def test_file_path_none_initially(self):
        rec = SessionRecorder()
        assert rec.file_path is None

    def test_default_output_dir(self):
        rec = SessionRecorder()
        assert rec.output_dir == RECORDINGS_DIR


class TestSessionRecorderStart:
    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_start_creates_wav_file(self, mock_start, mock_sf, tmp_path):
        rec = SessionRecorder(output_dir=tmp_path)
        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance

        path = rec.start()

        assert path is not None
        assert path.parent == tmp_path
        assert path.suffix == ".wav"
        mock_sf.SoundFile.assert_called_once()

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_filename_format(self, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(output_dir=tmp_path)
        path = rec.start()

        pattern = r"TT_Session_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.wav"
        assert re.match(pattern, path.name)

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_mic_mode_creates_one_capture(self, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(source_mode="mic", output_dir=tmp_path)
        rec.start()

        assert rec._mic_capture is not None
        assert rec._system_capture is None

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_system_mode_requires_device(self, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(source_mode="system", system_device=None, output_dir=tmp_path)
        path = rec.start()

        # Should fail without a system device
        assert path is None

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_system_mode_with_device(self, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(source_mode="system", system_device=5, output_dir=tmp_path)
        rec.start()

        assert rec._system_capture is not None
        assert rec._mic_capture is None

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_dual_mode_creates_two_captures(self, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(source_mode="system_and_mic", system_device=5, output_dir=tmp_path)
        rec.start()

        assert rec._mic_capture is not None
        assert rec._system_capture is not None


class TestSessionRecorderStop:
    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    @patch.object(AudioCapture, "stop")
    def test_stop_returns_path(self, mock_stop, mock_start, mock_sf, tmp_path):
        mock_sf.SoundFile.return_value = MagicMock()
        rec = SessionRecorder(output_dir=tmp_path)
        rec.start()
        path = rec.stop()

        assert path is not None
        assert path.suffix == ".wav"

    def test_stop_without_start_returns_none(self):
        rec = SessionRecorder()
        assert rec.stop() is None

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    @patch.object(AudioCapture, "stop")
    def test_stop_closes_soundfile(self, mock_stop, mock_start, mock_sf, tmp_path):
        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance
        rec = SessionRecorder(output_dir=tmp_path)
        rec.start()
        rec.stop()

        mock_sf_instance.close.assert_called_once()


# ── Mic Muting (PTT Exclusion) ───────────────────────────────


class TestMicMuting:
    def test_mute_unmute_flags(self):
        rec = SessionRecorder()
        assert rec._mic_muted is False

        rec.mute_mic()
        assert rec._mic_muted is True

        rec.unmute_mic()
        assert rec._mic_muted is False

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_muted_mic_writes_silence_in_single_mode(self, mock_start, mock_sf, tmp_path):
        from datetime import datetime

        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance
        rec = SessionRecorder(source_mode="mic", output_dir=tmp_path)
        rec.start()
        rec.mute_mic()

        # Simulate a chunk arriving while muted
        chunk = AudioChunk(
            data=np.ones((1024, 1), dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )
        rec._on_mic_chunk(chunk)

        # Muted in mic-only mode: should NOT write anything
        mock_sf_instance.write.assert_not_called()

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_unmuted_mic_writes_data(self, mock_start, mock_sf, tmp_path):
        from datetime import datetime

        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance
        rec = SessionRecorder(source_mode="mic", output_dir=tmp_path)
        rec.start()

        chunk = AudioChunk(
            data=np.ones((1024, 1), dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )
        rec._on_mic_chunk(chunk)

        mock_sf_instance.write.assert_called_once()


# ── Dual Source Mixing ────────────────────────────────────────


class TestDualSourceMixing:
    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_flush_mixed_averages_chunks(self, mock_start, mock_sf, tmp_path):
        from datetime import datetime

        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance
        rec = SessionRecorder(
            source_mode="system_and_mic", system_device=5, output_dir=tmp_path
        )
        rec.start()

        mic_chunk = AudioChunk(
            data=np.full((1024, 1), 0.4, dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )
        sys_chunk = AudioChunk(
            data=np.full((1024, 1), 0.6, dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )

        rec._on_mic_chunk(mic_chunk)
        rec._on_system_chunk(sys_chunk)

        # Should have written mixed audio
        assert mock_sf_instance.write.call_count == 1
        written_data = mock_sf_instance.write.call_args[0][0]
        np.testing.assert_allclose(written_data, 0.5, atol=1e-6)

    @patch("tommy_talker.engine.audio_capture.sf")
    @patch.object(AudioCapture, "start")
    def test_muted_mic_writes_silence_in_mix(self, mock_start, mock_sf, tmp_path):
        from datetime import datetime

        mock_sf_instance = MagicMock()
        mock_sf.SoundFile.return_value = mock_sf_instance
        rec = SessionRecorder(
            source_mode="system_and_mic", system_device=5, output_dir=tmp_path
        )
        rec.start()
        rec.mute_mic()

        mic_chunk = AudioChunk(
            data=np.full((1024, 1), 1.0, dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )
        sys_chunk = AudioChunk(
            data=np.full((1024, 1), 0.8, dtype=np.float32),
            sample_rate=44100,
            timestamp=datetime.now(),
        )

        rec._on_mic_chunk(mic_chunk)
        rec._on_system_chunk(sys_chunk)

        # Mic muted → zeros + 0.8 = 0.4 average
        written_data = mock_sf_instance.write.call_args[0][0]
        np.testing.assert_allclose(written_data, 0.4, atol=1e-6)


# ── AudioCapture Device Parameter ────────────────────────────


class TestAudioCaptureDevice:
    def test_default_device_is_none(self):
        cap = AudioCapture()
        assert cap.device is None

    def test_custom_device_stored(self):
        cap = AudioCapture(device=3)
        assert cap.device == 3

    @patch("tommy_talker.engine.audio_capture.sd.InputStream")
    def test_device_passed_to_input_stream(self, mock_stream_cls):
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        cap = AudioCapture(device=7)
        cap.start()

        mock_stream_cls.assert_called_once()
        call_kwargs = mock_stream_cls.call_args[1]
        assert call_kwargs["device"] == 7

    @patch("tommy_talker.engine.audio_capture.sd.InputStream")
    def test_none_device_passed_as_none(self, mock_stream_cls):
        mock_stream = MagicMock()
        mock_stream_cls.return_value = mock_stream

        cap = AudioCapture()
        cap.start()

        call_kwargs = mock_stream_cls.call_args[1]
        assert call_kwargs["device"] is None


# ── Config Round-Trip ─────────────────────────────────────────


class TestSessionConfig:
    def test_default_session_audio_source(self):
        config = UserConfig()
        assert config.session_audio_source == "mic"

    def test_default_session_system_device(self):
        config = UserConfig()
        assert config.session_system_device is None

    def test_config_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "tommy_talker.utils.config.BASE_DATA_DIR", tmp_path
        )

        config = UserConfig(
            session_audio_source="system_and_mic",
            session_system_device="BlackHole 2ch",
        )
        save_config(config)

        loaded = load_config()
        assert loaded.session_audio_source == "system_and_mic"
        assert loaded.session_system_device == "BlackHole 2ch"
