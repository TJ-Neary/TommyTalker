"""
TommyTalker Audio Capture
Audio recording for push-to-talk transcription and session recording.
"""

import logging
import threading
from collections import deque
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("TommyTalker")
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

try:
    import soundfile as sf
    HAS_SOUNDFILE = True
except ImportError:
    HAS_SOUNDFILE = False


# Default recordings directory
RECORDINGS_DIR = Path.home() / "Documents" / "TommyTalker" / "Recordings"


@dataclass
class AudioChunk:
    """A chunk of audio data with timestamp."""
    data: np.ndarray
    sample_rate: int
    timestamp: datetime


class AudioCapture:
    """
    Low-level audio capture using sounddevice.
    Provides raw audio chunks via callback.
    """

    DEFAULT_SAMPLE_RATE = 16000  # Whisper expects 16kHz
    DEFAULT_CHANNELS = 1
    DEFAULT_CHUNK_SIZE = 1024

    def __init__(
        self,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        callback: Optional[Callable[[AudioChunk], None]] = None,
        device: Optional[int] = None,
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.callback = callback
        self.device = device

        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False

    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice callback - runs in separate thread."""
        if status:
            log.debug("AudioCapture status: %s", status)

        if self.callback and self._is_recording:
            chunk = AudioChunk(
                data=indata.copy(),
                sample_rate=self.sample_rate,
                timestamp=datetime.now()
            )
            self.callback(chunk)

    def start(self):
        """Start audio capture."""
        if self._is_recording:
            return

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            blocksize=self.chunk_size,
            callback=self._audio_callback,
            device=self.device,
        )
        self._stream.start()
        self._is_recording = True
        log.debug("AudioCapture started at %dHz", self.sample_rate)

    def stop(self):
        """Stop audio capture."""
        if not self._is_recording:
            return

        self._is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        log.debug("AudioCapture stopped")

    @property
    def is_recording(self) -> bool:
        return self._is_recording


class Recorder:
    """
    In-memory audio recorder for push-to-talk.

    Captures audio into a memory buffer via AudioCapture. On stop,
    returns the buffered audio as a numpy array ready for transcription.
    No files are written to disk.
    """

    def __init__(
        self,
        live_callback: Optional[Callable[[AudioChunk], None]] = None,
        sample_rate: int = AudioCapture.DEFAULT_SAMPLE_RATE
    ):
        self.live_callback = live_callback
        self.sample_rate = sample_rate

        self._capture: Optional[AudioCapture] = None
        self._buffer: list[np.ndarray] = []
        self._buffer_lock = threading.Lock()

    def _on_audio_chunk(self, chunk: AudioChunk):
        """Handle incoming audio — forward to live callback and buffer."""
        if self.live_callback:
            self.live_callback(chunk)

        with self._buffer_lock:
            self._buffer.append(chunk.data)

    def start(self):
        """Start recording into memory buffer."""
        with self._buffer_lock:
            self._buffer = []

        self._capture = AudioCapture(
            sample_rate=self.sample_rate,
            callback=self._on_audio_chunk
        )
        self._capture.start()

    def stop(self) -> Optional[np.ndarray]:
        """
        Stop recording and return buffered audio.

        Returns:
            numpy array of audio samples (float32, mono, 16kHz),
            or None if no audio was captured.
        """
        if not self._capture:
            return None

        self._capture.stop()
        self._capture = None

        with self._buffer_lock:
            if not self._buffer:
                return None
            audio = np.concatenate(self._buffer, axis=0).flatten().astype(np.float32)
            self._buffer = []

        return audio

    @property
    def is_recording(self) -> bool:
        return self._capture is not None and self._capture.is_recording


class SessionRecorder:
    """
    Session recorder that streams audio to a WAV file on disk.

    Supports three source modes:
    - "mic": Record from microphone (default input device)
    - "system": Record from a virtual audio device (e.g., BlackHole)
    - "system_and_mic": Mix both sources into a single mono WAV

    Provides mute_mic()/unmute_mic() so push-to-talk usage is excluded
    from session recordings.
    """

    DEFAULT_SAMPLE_RATE = 44100  # CD quality for archival
    DEFAULT_CHANNELS = 1
    DEFAULT_CHUNK_SIZE = 2048

    def __init__(
        self,
        source_mode: str = "mic",
        mic_device: Optional[int] = None,
        system_device: Optional[int] = None,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        output_dir: Path = RECORDINGS_DIR,
    ):
        self.source_mode = source_mode
        self.mic_device = mic_device
        self.system_device = system_device
        self.sample_rate = sample_rate
        self.output_dir = output_dir

        self._mic_capture: Optional[AudioCapture] = None
        self._system_capture: Optional[AudioCapture] = None
        self._sf_file: Optional["sf.SoundFile"] = None
        self._file_path: Optional[Path] = None
        self._write_lock = threading.Lock()
        self._mic_muted = False

        # Deques for dual-source mixing
        self._mic_deque: deque = deque()
        self._system_deque: deque = deque()

    def _on_mic_chunk(self, chunk: AudioChunk):
        """Handle incoming mic audio."""
        if self.source_mode == "system_and_mic":
            with self._write_lock:
                if self._mic_muted:
                    self._mic_deque.append(np.zeros_like(chunk.data))
                else:
                    self._mic_deque.append(chunk.data)
                self._flush_mixed()
        else:
            # Direct write for mic-only mode
            with self._write_lock:
                if self._sf_file and not self._mic_muted:
                    self._sf_file.write(chunk.data)

    def _on_system_chunk(self, chunk: AudioChunk):
        """Handle incoming system audio."""
        if self.source_mode == "system_and_mic":
            with self._write_lock:
                self._system_deque.append(chunk.data)
                self._flush_mixed()
        else:
            # Direct write for system-only mode
            with self._write_lock:
                if self._sf_file:
                    self._sf_file.write(chunk.data)

    def _flush_mixed(self):
        """Mix matching mic and system chunks and write to file."""
        while self._mic_deque and self._system_deque:
            mic_data = self._mic_deque.popleft()
            sys_data = self._system_deque.popleft()

            # Match lengths (in case of slight chunk size differences)
            min_len = min(len(mic_data), len(sys_data))
            mixed = (mic_data[:min_len] + sys_data[:min_len]) * 0.5

            if self._sf_file:
                self._sf_file.write(mixed)

    def start(self) -> Optional[Path]:
        """Start session recording. Creates WAV file and begins capture."""
        if not HAS_SOUNDFILE:
            log.error("soundfile not installed — cannot record")
            return None

        self.output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self._file_path = self.output_dir / f"TT_Session_{timestamp}.wav"

        self._sf_file = sf.SoundFile(
            str(self._file_path),
            mode="w",
            samplerate=self.sample_rate,
            channels=self.DEFAULT_CHANNELS,
            format="WAV",
            subtype="FLOAT",
        )

        # Start capture(s) based on source mode
        if self.source_mode in ("mic", "system_and_mic"):
            self._mic_capture = AudioCapture(
                sample_rate=self.sample_rate,
                channels=self.DEFAULT_CHANNELS,
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                callback=self._on_mic_chunk,
                device=self.mic_device,
            )
            self._mic_capture.start()

        if self.source_mode in ("system", "system_and_mic"):
            if self.system_device is None:
                log.error("No system audio device configured")
                self._cleanup()
                return None

            self._system_capture = AudioCapture(
                sample_rate=self.sample_rate,
                channels=self.DEFAULT_CHANNELS,
                chunk_size=self.DEFAULT_CHUNK_SIZE,
                callback=self._on_system_chunk,
                device=self.system_device,
            )
            self._system_capture.start()

        log.info("SessionRecorder recording (%s) to: %s", self.source_mode, self._file_path)
        return self._file_path

    def stop(self) -> Optional[Path]:
        """Stop session recording and finalize the WAV file."""
        if not self._mic_capture and not self._system_capture:
            return None

        if self._mic_capture:
            self._mic_capture.stop()
            self._mic_capture = None

        if self._system_capture:
            self._system_capture.stop()
            self._system_capture = None

        # Flush any remaining mixed chunks
        with self._write_lock:
            if self.source_mode == "system_and_mic":
                self._flush_mixed()
            if self._sf_file:
                self._sf_file.close()
                self._sf_file = None

        path = self._file_path
        self._file_path = None
        self._mic_deque.clear()
        self._system_deque.clear()

        log.info("SessionRecorder saved: %s", path)
        return path

    def _cleanup(self):
        """Clean up on startup failure."""
        if self._mic_capture:
            self._mic_capture.stop()
            self._mic_capture = None
        if self._sf_file:
            self._sf_file.close()
            self._sf_file = None
        if self._file_path and self._file_path.exists():
            self._file_path.unlink()
        self._file_path = None

    def mute_mic(self):
        """Mute mic channel (used during push-to-talk to exclude PTT audio)."""
        self._mic_muted = True

    def unmute_mic(self):
        """Unmute mic channel."""
        self._mic_muted = False

    @property
    def is_recording(self) -> bool:
        mic_active = self._mic_capture is not None and self._mic_capture.is_recording
        sys_active = self._system_capture is not None and self._system_capture.is_recording
        return mic_active or sys_active

    @property
    def file_path(self) -> Optional[Path]:
        return self._file_path
