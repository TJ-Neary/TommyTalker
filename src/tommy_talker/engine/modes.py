"""
TommyTalker Mode Controllers
Push-to-talk cursor mode orchestration.
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Callable

log = logging.getLogger("TommyTalker")

from tommy_talker.engine.audio_capture import Recorder
from tommy_talker.engine.transcriber import Transcriber
from tommy_talker.utils.config import UserConfig
from tommy_talker.utils.hardware_detect import HardwareProfile


class OperatingMode(Enum):
    """Operating mode."""
    CURSOR = "cursor"


@dataclass
class ModeResult:
    """Result from a mode operation."""
    success: bool
    text: str
    error: Optional[str] = None
    metadata: Optional[dict] = None


class CursorModeController:
    """
    Cursor Mode: Push-to-Talk
    Record -> Transcribe in memory -> Type at cursor
    """

    def __init__(self, config: UserConfig, hardware: HardwareProfile,
                 on_text_ready: Optional[Callable[[str], None]] = None):
        self.config = config
        self.hardware = hardware
        self.on_text_ready = on_text_ready
        self._is_active = False
        self._app_context = None

        self.transcriber = Transcriber(
            tier=hardware.tier,
            custom_vocabulary=config.vocabulary
        )
        self.recorder = Recorder()

    def set_app_context(self, app_context):
        """Set the app context for this recording session."""
        self._app_context = app_context

    def start(self):
        """Start recording."""
        self._is_active = True
        self.recorder.start()
        log.debug("CursorMode started - listening")

    def stop(self) -> ModeResult:
        """Stop recording and transcribe from memory."""
        self._is_active = False

        audio_data = self.recorder.stop()

        if audio_data is None or len(audio_data) == 0:
            return ModeResult(success=False, text="", error="No audio recorded")

        result = self.transcriber.transcribe_audio(audio_data)

        if not result:
            return ModeResult(success=False, text="", error="Transcription failed")

        if self.on_text_ready and result.text:
            self.on_text_ready(result.text)

        log.debug("CursorMode transcribed: %s", result.text[:80])
        return ModeResult(
            success=True,
            text=result.text,
            metadata={"duration": result.duration}
        )

    @property
    def is_active(self) -> bool:
        return self._is_active


class ModeManager:
    """
    Central manager for operating modes.
    Ensures only one mode is active at a time.
    """

    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        self.config = config
        self.hardware = hardware

        self._current_mode: Optional[OperatingMode] = None
        self._current_controller: Optional[CursorModeController] = None

        # Callback for mode results
        self.on_text_output: Optional[Callable[[str], None]] = None

    def _create_controller(self, mode: OperatingMode) -> CursorModeController:
        """Create a controller for the specified mode."""
        if mode == OperatingMode.CURSOR:
            return CursorModeController(
                self.config, self.hardware,
                on_text_ready=self._handle_text_output
            )
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _handle_text_output(self, text: str):
        """Handle text output from modes."""
        if self.on_text_output:
            self.on_text_output(text)

    def start_mode(self, mode: OperatingMode, app_context=None) -> bool:
        """Start a mode (stops any currently active mode first)."""
        if self._current_controller and self._current_controller.is_active:
            self.stop_current_mode()

        try:
            self._current_mode = mode
            self._current_controller = self._create_controller(mode)

            if app_context:
                self._current_controller.set_app_context(app_context)

            self._current_controller.start()
            return True

        except Exception as e:
            log.error("ModeManager error starting mode: %s", e)
            self._current_mode = None
            self._current_controller = None
            return False

    def stop_current_mode(self) -> Optional[ModeResult]:
        """Stop the currently active mode."""
        if not self._current_controller:
            return None

        result = self._current_controller.stop()

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
            self.start_mode(OperatingMode.CURSOR)
            return True

    @property
    def current_mode(self) -> Optional[OperatingMode]:
        return self._current_mode

    @property
    def is_recording(self) -> bool:
        return self._current_controller is not None and self._current_controller.is_active
