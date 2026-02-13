"""
TommyTalker Transcriber
Speech-to-text using mlx_whisper (Apple Silicon optimized).
Supports vocabulary injection via initial_prompt.
"""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import numpy as np

log = logging.getLogger("TommyTalker")

# mlx_whisper import - may fail if not installed
try:
    import mlx_whisper
    HAS_MLX_WHISPER = True
except ImportError:
    HAS_MLX_WHISPER = False
    log.warning("mlx_whisper not installed - transcription disabled")


# Default vocabulary for Whisper initial_prompt
DEFAULT_VOCABULARY = [
    "TommyTalker",
]


@dataclass
class TranscriptionResult:
    """Result from transcription."""
    text: str
    segments: list  # List of segment dicts with timing info
    language: str
    duration: float


class Transcriber:
    """
    Speech-to-text transcription using mlx_whisper.
    
    Features:
    - Apple Silicon optimized via MLX
    - Vocabulary injection for better recognition of custom terms
    - Streaming and file-based transcription
    """
    
    # Model paths for each tier
    MODEL_MAP = {
        1: "mlx-community/distil-whisper-small",
        2: "mlx-community/distil-whisper-medium.en",
        3: "mlx-community/distil-whisper-large-v3",
    }
    
    def __init__(self, tier: int = 2, custom_vocabulary: Optional[list[str]] = None):
        """
        Initialize transcriber with hardware-appropriate model.
        
        Args:
            tier: Hardware tier (1, 2, or 3) determines which model to use
            custom_vocabulary: Additional words to inject into initial_prompt
        """
        self.tier = tier
        self.model_name = self.MODEL_MAP.get(tier, self.MODEL_MAP[2])
        self.vocabulary = list(DEFAULT_VOCABULARY)
        
        if custom_vocabulary:
            self.vocabulary.extend(custom_vocabulary)
            
        self._model = None
        
        if not HAS_MLX_WHISPER:
            log.warning("Transcriber: mlx_whisper not available")
            return
            
        log.info("Transcriber initialized with model: %s", self.model_name)
        
    def _get_initial_prompt(self) -> str:
        """Build the initial_prompt from vocabulary list."""
        return ", ".join(self.vocabulary)
        
    def transcribe_file(self, audio_path: Path) -> Optional[TranscriptionResult]:
        """
        Transcribe an audio file.
        
        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            
        Returns:
            TranscriptionResult or None if transcription failed
        """
        if not HAS_MLX_WHISPER:
            return None
            
        if not audio_path.exists():
            log.error("Transcriber file not found: %s", audio_path)
            return None
            
        try:
            result = mlx_whisper.transcribe(
                str(audio_path),
                path_or_hf_repo=self.model_name,
                initial_prompt=self._get_initial_prompt(),
            )
            
            return TranscriptionResult(
                text=result.get("text", "").strip(),
                segments=result.get("segments", []),
                language=result.get("language", "en"),
                duration=result.get("duration", 0.0)
            )
            
        except Exception as e:
            log.error("Transcriber error transcribing file: %s", e)
            return None
            
    def transcribe_audio(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[TranscriptionResult]:
        """
        Transcribe audio data directly (for streaming).
        
        Args:
            audio_data: NumPy array of audio samples
            sample_rate: Sample rate of the audio (default 16kHz)
            
        Returns:
            TranscriptionResult or None if transcription failed
        """
        if not HAS_MLX_WHISPER:
            return None
            
        try:
            # mlx_whisper can handle numpy arrays directly
            result = mlx_whisper.transcribe(
                audio_data,
                path_or_hf_repo=self.model_name,
                initial_prompt=self._get_initial_prompt(),
            )
            
            return TranscriptionResult(
                text=result.get("text", "").strip(),
                segments=result.get("segments", []),
                language=result.get("language", "en"),
                duration=len(audio_data) / sample_rate
            )
            
        except Exception as e:
            log.error("Transcriber error transcribing audio: %s", e)
            return None
            
    def update_vocabulary(self, words: list[str]):
        """Add words to the vocabulary for better recognition."""
        for word in words:
            if word not in self.vocabulary:
                self.vocabulary.append(word)
                
    def set_model(self, model_name: str):
        """
        Set a custom model (for Advanced Mode).
        
        Args:
            model_name: HuggingFace model path or local path
        """
        self.model_name = model_name
        self._model = None  # Reset cached model
        log.info("Transcriber model changed to: %s", model_name)
