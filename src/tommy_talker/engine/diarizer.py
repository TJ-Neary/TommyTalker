"""
TommyTalker Diarizer
Speaker identification using pyannote.audio.
Only enabled for Tier 3 (>32GB RAM) by default.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# pyannote import - requires HuggingFace token
try:
    from pyannote.audio import Pipeline
    HAS_PYANNOTE = True
except ImportError:
    HAS_PYANNOTE = False
    print("[WARNING] pyannote.audio not installed - diarization disabled")


@dataclass
class SpeakerSegment:
    """A segment of speech from a single speaker."""
    speaker: str  # "Speaker A", "Speaker B", etc.
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: Optional[str] = None  # Transcribed text (if aligned)


@dataclass
class DiarizationResult:
    """Result from speaker diarization."""
    segments: list[SpeakerSegment]
    num_speakers: int
    audio_duration: float


class Diarizer:
    """
    Speaker diarization using pyannote.audio.
    
    REQUIREMENTS:
    - HuggingFace token with access to pyannote models
    - Acceptance of pyannote terms on HuggingFace
    - Tier 3 hardware (>32GB RAM) recommended
    
    Features:
    - Automatic speaker count detection
    - Speaker labeling (Speaker A, Speaker B, etc.)
    - Segment timestamps for meeting transcripts
    """
    
    # Speaker labels
    SPEAKER_LABELS = ["Speaker A", "Speaker B", "Speaker C", "Speaker D", 
                      "Speaker E", "Speaker F", "Speaker G", "Speaker H"]
    
    def __init__(self, huggingface_token: Optional[str] = None):
        """
        Initialize diarizer with HuggingFace token.
        
        Args:
            huggingface_token: HuggingFace access token for pyannote models
        """
        self.hf_token = huggingface_token
        self._pipeline: Optional[Pipeline] = None
        
        if not HAS_PYANNOTE:
            print("[Diarizer] pyannote.audio not available")
            return
            
        if not self.hf_token:
            print("[Diarizer] No HuggingFace token provided - diarization disabled")
            return
            
    def _load_pipeline(self) -> bool:
        """Load the diarization pipeline (lazy loading)."""
        if self._pipeline is not None:
            return True
            
        if not HAS_PYANNOTE or not self.hf_token:
            return False
            
        try:
            print("[Diarizer] Loading pyannote pipeline...")
            self._pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                use_auth_token=self.hf_token
            )
            print("[Diarizer] Pipeline loaded successfully")
            return True
            
        except Exception as e:
            print(f"[Diarizer] Error loading pipeline: {e}")
            return False
            
    def diarize(self, audio_path: Path) -> Optional[DiarizationResult]:
        """
        Perform speaker diarization on an audio file.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            DiarizationResult or None if diarization failed
        """
        if not self._load_pipeline():
            return None
            
        if not audio_path.exists():
            print(f"[Diarizer] File not found: {audio_path}")
            return None
            
        try:
            print(f"[Diarizer] Processing: {audio_path}")
            
            # Run diarization
            diarization = self._pipeline(str(audio_path))
            
            # Convert to segments
            segments = []
            speaker_map = {}  # Map pyannote speaker IDs to our labels
            
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                # Map speaker ID to label
                if speaker not in speaker_map:
                    idx = len(speaker_map)
                    if idx < len(self.SPEAKER_LABELS):
                        speaker_map[speaker] = self.SPEAKER_LABELS[idx]
                    else:
                        speaker_map[speaker] = f"Speaker {idx + 1}"
                        
                segments.append(SpeakerSegment(
                    speaker=speaker_map[speaker],
                    start=turn.start,
                    end=turn.end
                ))
                
            # Get audio duration
            import soundfile as sf
            info = sf.info(str(audio_path))
            duration = info.duration
            
            return DiarizationResult(
                segments=segments,
                num_speakers=len(speaker_map),
                audio_duration=duration
            )
            
        except Exception as e:
            print(f"[Diarizer] Error during diarization: {e}")
            return None
            
    def set_token(self, token: str):
        """
        Set or update the HuggingFace token.
        
        Args:
            token: HuggingFace access token
        """
        self.hf_token = token
        self._pipeline = None  # Reset pipeline to reload with new token
        print("[Diarizer] Token updated")
        
    @property
    def is_available(self) -> bool:
        """Check if diarization is available."""
        return HAS_PYANNOTE and self.hf_token is not None


def align_transcript_with_diarization(
    transcript_segments: list,
    diarization: DiarizationResult
) -> list[SpeakerSegment]:
    """
    Align transcript segments with diarization to add speaker labels.
    
    Args:
        transcript_segments: Segments from Whisper transcription
        diarization: Diarization result
        
    Returns:
        List of SpeakerSegments with text and speaker labels
    """
    aligned = []
    
    for tseg in transcript_segments:
        # Find overlapping diarization segment
        tseg_start = tseg.get("start", 0)
        tseg_end = tseg.get("end", 0)
        tseg_text = tseg.get("text", "").strip()
        
        # Find speaker with most overlap
        best_speaker = "Unknown"
        best_overlap = 0
        
        for dseg in diarization.segments:
            overlap_start = max(tseg_start, dseg.start)
            overlap_end = min(tseg_end, dseg.end)
            overlap = max(0, overlap_end - overlap_start)
            
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = dseg.speaker
                
        aligned.append(SpeakerSegment(
            speaker=best_speaker,
            start=tseg_start,
            end=tseg_end,
            text=tseg_text
        ))
        
    return aligned
