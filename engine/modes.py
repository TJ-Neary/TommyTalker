"""
TommyTalker Mode Controllers
Central orchestration for the 4 operating modes.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable
import threading

from engine.audio_capture import DualStreamRecorder, AudioChunk
from engine.transcriber import Transcriber, TranscriptionResult
from engine.llm_client import LLMClient
from engine.diarizer import Diarizer, align_transcript_with_diarization
from engine.rag_store import RAGStore
from utils.config import UserConfig, get_chroma_path, get_style_guide_path
from utils.hardware_detect import HardwareProfile


class OperatingMode(Enum):
    """The 4 operating modes."""
    CURSOR = "cursor"
    EDITOR = "editor"
    MEETING = "meeting"
    HUD = "hud"


@dataclass
class ModeResult:
    """Result from a mode operation."""
    success: bool
    text: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


class BaseModeController:
    """Base class for mode controllers."""
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        self.config = config
        self.hardware = hardware
        self._is_active = False
        
    def start(self):
        """Start the mode."""
        self._is_active = True
        
    def stop(self) -> Optional[ModeResult]:
        """Stop the mode and return result."""
        self._is_active = False
        return None
        
    @property
    def is_active(self) -> bool:
        return self._is_active


class CursorModeController(BaseModeController):
    """
    Mode 1: Cursor
    Listen → Transcribe → Type at cursor
    
    Features:
    - Live transcription via mlx_whisper
    - Vocabulary injection from config
    - Types directly at cursor via pyautogui
    """
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile,
                 on_text_ready: Optional[Callable[[str], None]] = None):
        super().__init__(config, hardware)
        self.on_text_ready = on_text_ready
        
        # Initialize components
        self.transcriber = Transcriber(
            tier=hardware.tier,
            custom_vocabulary=config.vocabulary
        )
        self.recorder = DualStreamRecorder(
            live_callback=self._on_audio_chunk
        )
        
        self._audio_buffer = []
        self._buffer_lock = threading.Lock()
        
    def _on_audio_chunk(self, chunk: AudioChunk):
        """Handle incoming audio for live transcription."""
        with self._buffer_lock:
            self._audio_buffer.append(chunk.data)
            
    def start(self):
        """Start listening and transcribing."""
        super().start()
        self._audio_buffer = []
        self.recorder.start()
        print("[CursorMode] Started - listening...")
        
    def stop(self) -> ModeResult:
        """Stop and transcribe accumulated audio."""
        super().stop()
        
        # Stop recording
        audio_path = self.recorder.stop()
        
        if not audio_path or not audio_path.exists():
            return ModeResult(success=False, text="", error="No audio recorded")
            
        # Transcribe the file
        result = self.transcriber.transcribe_file(audio_path)
        
        if not result:
            return ModeResult(success=False, text="", error="Transcription failed")
            
        # Type at cursor if callback provided
        if self.on_text_ready and result.text:
            self.on_text_ready(result.text)
            
        print(f"[CursorMode] Transcribed: {result.text[:50]}...")
        return ModeResult(
            success=True,
            text=result.text,
            metadata={"duration": result.duration, "audio_path": str(audio_path)}
        )


class EditorModeController(BaseModeController):
    """
    Mode 2: Editor
    Record → Transcribe → LLM Rewrite ("Make Professional") → Paste
    
    Features:
    - Full recording before transcription
    - LLM rewriting via Ollama
    - Style guide application if present
    """
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile,
                 on_text_ready: Optional[Callable[[str], None]] = None):
        super().__init__(config, hardware)
        self.on_text_ready = on_text_ready
        
        # Initialize components
        self.transcriber = Transcriber(
            tier=hardware.tier,
            custom_vocabulary=config.vocabulary
        )
        self.llm = LLMClient(
            tier=hardware.tier,
            custom_model=config.custom_llm_model if config.advanced_mode else None
        )
        self.recorder = DualStreamRecorder()
        
        # Load style guide if available
        style_path = get_style_guide_path()
        if style_path.exists():
            self.llm.load_style_guide(style_path)
            
    def start(self):
        """Start recording."""
        super().start()
        self.recorder.start()
        print("[EditorMode] Recording...")
        
    def stop(self) -> ModeResult:
        """Stop, transcribe, rewrite, and return result."""
        super().stop()
        
        # Stop recording
        audio_path = self.recorder.stop()
        
        if not audio_path or not audio_path.exists():
            return ModeResult(success=False, text="", error="No audio recorded")
            
        # Transcribe
        transcript = self.transcriber.transcribe_file(audio_path)
        
        if not transcript or not transcript.text:
            return ModeResult(success=False, text="", error="Transcription failed")
            
        print(f"[EditorMode] Transcribed: {transcript.text[:50]}...")
        
        # Rewrite with LLM
        rewrite_result = self.llm.rewrite_professional(transcript.text)
        
        if not rewrite_result:
            # Fall back to original if rewrite fails
            final_text = transcript.text
            print("[EditorMode] LLM rewrite failed, using original")
        else:
            final_text = rewrite_result.rewritten
            print(f"[EditorMode] Rewritten: {final_text[:50]}...")
            
        # Deliver result
        if self.on_text_ready:
            self.on_text_ready(final_text)
            
        return ModeResult(
            success=True,
            text=final_text,
            metadata={
                "original": transcript.text,
                "audio_path": str(audio_path),
                "model_used": rewrite_result.model_used if rewrite_result else None
            }
        )


class MeetingModeController(BaseModeController):
    """
    Mode 3: Meeting
    Meeting assistant with timestamps and Speaker Diarization (Speaker A/B)
    
    Features:
    - Full meeting recording
    - Speaker diarization via pyannote.audio
    - Timestamped transcript with speaker labels
    - RAG storage for later retrieval
    """
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile,
                 on_transcript_ready: Optional[Callable[[str], None]] = None):
        super().__init__(config, hardware)
        self.on_transcript_ready = on_transcript_ready
        
        # Initialize components
        self.transcriber = Transcriber(
            tier=hardware.tier,
            custom_vocabulary=config.vocabulary
        )
        self.diarizer = Diarizer(
            huggingface_token=config.huggingface_token
        ) if hardware.diarization_enabled else None
        
        self.rag = RAGStore(get_chroma_path())
        self.recorder = DualStreamRecorder()
        
    def start(self):
        """Start meeting recording."""
        super().start()
        self.recorder.start()
        print("[MeetingMode] Recording meeting...")
        
    def stop(self) -> ModeResult:
        """Stop, transcribe, diarize, and return formatted transcript."""
        super().stop()
        
        # Stop recording
        audio_path = self.recorder.stop()
        
        if not audio_path or not audio_path.exists():
            return ModeResult(success=False, text="", error="No audio recorded")
            
        # Transcribe
        transcript = self.transcriber.transcribe_file(audio_path)
        
        if not transcript:
            return ModeResult(success=False, text="", error="Transcription failed")
            
        # Format transcript with timestamps
        formatted_lines = []
        
        # Try diarization if available
        if self.diarizer and self.diarizer.is_available:
            print("[MeetingMode] Running speaker diarization...")
            diarization = self.diarizer.diarize(audio_path)
            
            if diarization:
                # Align transcript with speakers
                aligned = align_transcript_with_diarization(
                    transcript.segments,
                    diarization
                )
                
                for seg in aligned:
                    timestamp = self._format_timestamp(seg.start)
                    formatted_lines.append(f"[{timestamp}] {seg.speaker}: {seg.text}")
            else:
                # Fallback to non-diarized
                for seg in transcript.segments:
                    timestamp = self._format_timestamp(seg.get("start", 0))
                    formatted_lines.append(f"[{timestamp}] {seg.get('text', '').strip()}")
        else:
            # No diarization - just timestamps
            for seg in transcript.segments:
                timestamp = self._format_timestamp(seg.get("start", 0))
                formatted_lines.append(f"[{timestamp}] {seg.get('text', '').strip()}")
                
        formatted_text = "\n".join(formatted_lines)
        
        # Store in RAG for later retrieval
        self.rag.add_transcript(formatted_text, {
            "mode": "meeting",
            "duration": transcript.duration,
            "audio_path": str(audio_path)
        })
        
        if self.on_transcript_ready:
            self.on_transcript_ready(formatted_text)
            
        print(f"[MeetingMode] Meeting transcript ready ({len(formatted_lines)} segments)")
        return ModeResult(
            success=True,
            text=formatted_text,
            metadata={
                "segments": len(formatted_lines),
                "duration": transcript.duration,
                "audio_path": str(audio_path)
            }
        )
        
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS."""
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"


class HUDModeController(BaseModeController):
    """
    Mode 4: HUD
    Transparent overlay for interview coaching
    
    Features:
    - Real-time transcription displayed in overlay
    - Screen-share invisible (NSWindowSharingTypeNone)
    - Optional LLM coaching suggestions
    """
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile,
                 on_live_text: Optional[Callable[[str], None]] = None,
                 on_suggestion: Optional[Callable[[str], None]] = None):
        super().__init__(config, hardware)
        self.on_live_text = on_live_text
        self.on_suggestion = on_suggestion
        
        # Initialize components
        self.transcriber = Transcriber(
            tier=hardware.tier,
            custom_vocabulary=config.vocabulary
        )
        self.recorder = DualStreamRecorder(
            live_callback=self._on_audio_chunk
        )
        
        # Buffer for incremental transcription
        self._audio_buffer = []
        self._buffer_lock = threading.Lock()
        self._transcribe_interval = 2.0  # Transcribe every 2 seconds
        self._transcribe_timer = None
        
    def _on_audio_chunk(self, chunk: AudioChunk):
        """Buffer audio for periodic transcription."""
        with self._buffer_lock:
            self._audio_buffer.append(chunk.data)
            
    def _periodic_transcribe(self):
        """Periodically transcribe buffered audio."""
        if not self._is_active:
            return
            
        import numpy as np
        
        with self._buffer_lock:
            if not self._audio_buffer:
                # Schedule next and return
                if self._is_active:
                    self._transcribe_timer = threading.Timer(
                        self._transcribe_interval,
                        self._periodic_transcribe
                    )
                    self._transcribe_timer.start()
                return
            
            # Concatenate and flatten to 1D (MLX expects shape (samples,))
            audio_data = np.concatenate(self._audio_buffer, axis=0).flatten()
            
            # Safety: limit to max 30 seconds of audio to prevent memory issues
            max_samples = int(30 * 16000)  # 30 seconds at 16kHz
            if len(audio_data) > max_samples:
                audio_data = audio_data[-max_samples:]
            
            # Clear buffer after taking data (don't accumulate indefinitely)
            self._audio_buffer = []
            
        # Ensure float32 type
        audio_data = audio_data.astype(np.float32)
                
        # Transcribe in try/except to prevent crashes
        try:
            result = self.transcriber.transcribe_audio(audio_data)
            
            if result and result.text and self.on_live_text:
                self.on_live_text(result.text)
        except Exception as e:
            print(f"[HUDMode] Transcription error: {e}")
            
        # Schedule next transcription
        if self._is_active:
            self._transcribe_timer = threading.Timer(
                self._transcribe_interval,
                self._periodic_transcribe
            )
            self._transcribe_timer.start()
            
    def start(self):
        """Start HUD mode with live transcription."""
        super().start()
        self._audio_buffer = []
        self.recorder.start()
        
        # Start periodic transcription
        self._transcribe_timer = threading.Timer(
            self._transcribe_interval,
            self._periodic_transcribe
        )
        self._transcribe_timer.start()
        
        print("[HUDMode] Started - live transcription active")
        
    def stop(self) -> ModeResult:
        """Stop HUD mode."""
        super().stop()
        
        # Cancel timer
        if self._transcribe_timer:
            self._transcribe_timer.cancel()
            self._transcribe_timer = None
            
        # Stop recording
        audio_path = self.recorder.stop()
        
        print("[HUDMode] Stopped")
        return ModeResult(
            success=True,
            text="HUD session ended",
            metadata={"audio_path": str(audio_path) if audio_path else None}
        )


class ModeManager:
    """
    Central manager for all operating modes.
    Ensures only one mode is active at a time.
    """
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        self.config = config
        self.hardware = hardware
        
        self._current_mode: Optional[OperatingMode] = None
        self._current_controller: Optional[BaseModeController] = None
        
        # Callbacks for mode results
        self.on_text_output: Optional[Callable[[str], None]] = None
        self.on_live_text: Optional[Callable[[str], None]] = None
        
    def _create_controller(self, mode: OperatingMode) -> BaseModeController:
        """Create a controller for the specified mode."""
        if mode == OperatingMode.CURSOR:
            return CursorModeController(
                self.config, self.hardware,
                on_text_ready=self._handle_text_output
            )
        elif mode == OperatingMode.EDITOR:
            return EditorModeController(
                self.config, self.hardware,
                on_text_ready=self._handle_text_output
            )
        elif mode == OperatingMode.MEETING:
            return MeetingModeController(
                self.config, self.hardware,
                on_transcript_ready=self._handle_text_output
            )
        elif mode == OperatingMode.HUD:
            return HUDModeController(
                self.config, self.hardware,
                on_live_text=self.on_live_text
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")
            
    def _handle_text_output(self, text: str):
        """Handle text output from modes."""
        if self.on_text_output:
            self.on_text_output(text)
            
    def start_mode(self, mode: OperatingMode) -> bool:
        """Start a mode (stops any currently active mode first)."""
        # Stop current mode if active
        if self._current_controller and self._current_controller.is_active:
            self.stop_current_mode()
            
        try:
            self._current_mode = mode
            self._current_controller = self._create_controller(mode)
            self._current_controller.start()
            
            print(f"[ModeManager] Started mode: {mode.value}")
            return True
            
        except Exception as e:
            print(f"[ModeManager] Error starting mode: {e}")
            self._current_mode = None
            self._current_controller = None
            return False
            
    def stop_current_mode(self) -> Optional[ModeResult]:
        """Stop the currently active mode."""
        if not self._current_controller:
            return None
            
        result = self._current_controller.stop()
        
        print(f"[ModeManager] Stopped mode: {self._current_mode.value if self._current_mode else 'none'}")
        
        self._current_mode = None
        self._current_controller = None
        
        return result
        
    def toggle_recording(self) -> bool:
        """Toggle recording for the current mode."""
        if self._current_controller and self._current_controller.is_active:
            self.stop_current_mode()
            return False
        elif self._current_mode:
            self.start_mode(self._current_mode)
            return True
        else:
            # Default to Cursor mode
            self.start_mode(OperatingMode.CURSOR)
            return True
            
    @property
    def current_mode(self) -> Optional[OperatingMode]:
        return self._current_mode
        
    @property
    def is_recording(self) -> bool:
        return self._current_controller is not None and self._current_controller.is_active
