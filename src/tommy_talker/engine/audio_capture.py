"""
TommyTalker Audio Capture
Dual-stream architecture: Stream A (live feed to whisper) and Stream B (archive to disk).
"""

import threading
import queue
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

from tommy_talker.utils.config import get_recordings_path


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
        callback: Optional[Callable[[AudioChunk], None]] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.callback = callback
        
        self._stream: Optional[sd.InputStream] = None
        self._is_recording = False
        
    def _audio_callback(self, indata, frames, time_info, status):
        """sounddevice callback - runs in separate thread."""
        if status:
            print(f"[AudioCapture] Status: {status}")
            
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
            callback=self._audio_callback
        )
        self._stream.start()
        self._is_recording = True
        print(f"[AudioCapture] Started recording at {self.sample_rate}Hz")
        
    def stop(self):
        """Stop audio capture."""
        if not self._is_recording:
            return
            
        self._is_recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
        print("[AudioCapture] Stopped recording")
        
    @property
    def is_recording(self) -> bool:
        return self._is_recording


class DualStreamRecorder:
    """
    Dual-stream audio pipeline:
    - Stream A: Live feed to callback (for real-time transcription)
    - Stream B: Archive feed saved immediately to disk as timestamped .wav
    
    Both streams run in parallel from the same microphone input.
    """
    
    def __init__(
        self,
        live_callback: Optional[Callable[[AudioChunk], None]] = None,
        sample_rate: int = AudioCapture.DEFAULT_SAMPLE_RATE
    ):
        self.live_callback = live_callback
        self.sample_rate = sample_rate
        
        self._capture: Optional[AudioCapture] = None
        self._archive_buffer: list[np.ndarray] = []
        self._archive_lock = threading.Lock()
        self._current_session_path: Optional[Path] = None
        
    def _on_audio_chunk(self, chunk: AudioChunk):
        """Handle incoming audio - send to both streams."""
        # Stream A: Live callback
        if self.live_callback:
            self.live_callback(chunk)
            
        # Stream B: Archive to buffer (saved on stop)
        with self._archive_lock:
            self._archive_buffer.append(chunk.data)
            
    def start(self) -> Path:
        """
        Start dual-stream recording.
        Returns the path where the archive will be saved.
        """
        # Create timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self._current_session_path = get_recordings_path() / f"recording_{timestamp}.wav"
        
        # Clear archive buffer
        with self._archive_lock:
            self._archive_buffer = []
            
        # Start capture
        self._capture = AudioCapture(
            sample_rate=self.sample_rate,
            callback=self._on_audio_chunk
        )
        self._capture.start()
        
        print(f"[DualStream] Recording to: {self._current_session_path}")
        return self._current_session_path
        
    def stop(self) -> Optional[Path]:
        """
        Stop recording and save archive to disk.
        Returns the path to the saved file.
        """
        if not self._capture:
            return None
            
        self._capture.stop()
        
        # Save archive buffer to disk
        saved_path = self._save_archive()
        
        self._capture = None
        return saved_path
        
    def _save_archive(self) -> Optional[Path]:
        """Save the archive buffer to a WAV file."""
        if not self._current_session_path:
            return None
            
        with self._archive_lock:
            if not self._archive_buffer:
                print("[DualStream] No audio to save")
                return None
                
            # Concatenate all chunks
            audio_data = np.concatenate(self._archive_buffer, axis=0)
            
        # Ensure directory exists
        self._current_session_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save as WAV
        sf.write(
            self._current_session_path,
            audio_data,
            self.sample_rate,
            subtype='PCM_16'
        )
        
        print(f"[DualStream] Saved archive: {self._current_session_path}")
        return self._current_session_path
        
    @property
    def is_recording(self) -> bool:
        return self._capture is not None and self._capture.is_recording
