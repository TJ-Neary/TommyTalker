"""
TommyTalker Application Controller
Main application orchestration connecting GUI, engine, and utils.
"""

import logging
import re
import time
from pathlib import Path
from typing import Optional

log = logging.getLogger("TommyTalker")
from PyQt6.QtCore import QObject, pyqtSignal, QThread

import sounddevice as sd

from tommy_talker.engine.audio_capture import SessionRecorder
from tommy_talker.engine.modes import ModeManager, OperatingMode, ModeResult
from tommy_talker.utils.config import UserConfig, save_config
from tommy_talker.utils.hardware_detect import HardwareProfile
from tommy_talker.utils.hotkeys import HotkeyManager, is_modifier_only_hotkey
from tommy_talker.utils.typing import type_at_cursor, paste_text
from tommy_talker.utils.audio_feedback import get_audio_feedback
from tommy_talker.utils.app_context import AppContext, TextInputFormat, get_app_context

# Minimum time between hotkey triggers (debounce)
HOTKEY_DEBOUNCE_SECONDS = 0.5


class AppController(QObject):
    """
    Central application controller that wires together all components.

    Responsibilities:
    - Push-to-talk recording and transcription
    - Session recording (save audio to WAV files)
    - Hotkey registration and handling
    - Text output (typing/pasting)
    - Configuration updates
    """

    # Signals for GUI updates
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(object)  # ModeResult
    recording_changed = pyqtSignal(bool)  # True = PTT recording, False = idle
    session_recording_changed = pyqtSignal(bool)  # True = session recording active
    any_recording_changed = pyqtSignal(bool)  # True = any recording active
    status_message = pyqtSignal(str)

    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware

        # Debounce tracking for hotkeys
        self._last_hotkey_time: float = 0

        # App context captured at recording start
        self._app_context: Optional[AppContext] = None

        # Initialize mode manager (push-to-talk)
        self.mode_manager = ModeManager(config, hardware)
        self.mode_manager.on_text_output = self._on_text_output

        # Session recorder (save to WAV)
        self._session_recorder: Optional[SessionRecorder] = None

        # Initialize hotkey manager
        self.hotkey_manager = HotkeyManager()
        self._register_hotkeys()

        # Set initial mode from config
        self._current_mode = OperatingMode(config.default_mode)

    def _register_hotkeys(self):
        """Register global hotkeys from config."""
        hotkeys = self.config.hotkeys
        is_push_to_talk = self.config.recording_mode == "push_to_talk"

        # Cursor mode hotkey
        if "cursor_mode" in hotkeys:
            cursor_hotkey = hotkeys["cursor_mode"]
            use_push_to_talk = is_push_to_talk or is_modifier_only_hotkey(cursor_hotkey)

            if use_push_to_talk:
                self.hotkey_manager.register(
                    cursor_hotkey,
                    self._on_cursor_hotkey_down,
                    "Cursor Mode",
                    callback_up=self._on_hotkey_up
                )
            else:
                self.hotkey_manager.register(
                    cursor_hotkey,
                    self._on_cursor_hotkey_toggle,
                    "Cursor Mode"
                )

        # Toggle recording hotkey (always toggle behavior)
        if "toggle_record" in hotkeys:
            self.hotkey_manager.register(
                hotkeys["toggle_record"],
                self.toggle_recording,
                "Toggle Recording"
            )

        # Open dashboard hotkey (handled by GUI)
        if "open_dashboard" in hotkeys:
            self.hotkey_manager.register(
                hotkeys["open_dashboard"],
                lambda: self.status_message.emit("Opening dashboard..."),
                "Open Dashboard"
            )

    # ── Push-to-Talk ──────────────────────────────────────────────

    def _on_cursor_hotkey_down(self):
        """Handle Cursor mode hotkey press (push-to-talk: start recording)."""
        if self._current_mode != OperatingMode.CURSOR:
            self.set_mode(OperatingMode.CURSOR)
        if not self.mode_manager.is_recording:
            self.start_recording()

    def _on_cursor_hotkey_toggle(self):
        """Handle Cursor mode hotkey press (toggle mode)."""
        if self._current_mode != OperatingMode.CURSOR:
            self.set_mode(OperatingMode.CURSOR)
        self.toggle_recording()

    def _on_hotkey_up(self):
        """Handle hotkey release (push-to-talk: stop recording)."""
        if self.mode_manager.is_recording:
            self.stop_recording()

    def set_mode(self, mode: OperatingMode):
        """Set the current operating mode."""
        if self.mode_manager.is_recording:
            self.stop_recording()

        self._current_mode = mode
        self.status_message.emit(f"Mode: {mode.value.title()}")

    def start_recording(self) -> bool:
        """Start push-to-talk recording."""
        # Capture app context BEFORE recording starts
        if self.config.app_context_enabled:
            self._app_context = get_app_context()
        else:
            self._app_context = None

        # Mute mic in session recorder during PTT
        if self._session_recorder and self._session_recorder.is_recording:
            self._session_recorder.mute_mic()

        success = self.mode_manager.start_mode(self._current_mode, app_context=self._app_context)

        if success:
            get_audio_feedback().play_start()

            self.recording_started.emit()
            self.recording_changed.emit(True)
            self._update_any_recording()

            ctx_hint = ""
            if self._app_context and self._app_context.profile:
                ctx_hint = f" [{self._app_context.app_name}]"
            self.status_message.emit(f"Recording ({self._current_mode.value}){ctx_hint}...")

        return success

    def stop_recording(self) -> Optional[ModeResult]:
        """Stop push-to-talk recording and process result."""
        result = self.mode_manager.stop_current_mode()

        # Unmute mic in session recorder after PTT
        if self._session_recorder and self._session_recorder.is_recording:
            self._session_recorder.unmute_mic()

        self.recording_changed.emit(False)
        self._update_any_recording()

        audio = get_audio_feedback()

        if result:
            self.recording_stopped.emit(result)

            if result.success and result.text:
                audio.play_stop()
                self.status_message.emit("Recording processed")
            elif result.success and not result.text:
                audio.play_no_result()
                self.status_message.emit("No speech detected")
            else:
                audio.play_error()
                self.status_message.emit(f"Error: {result.error}")
        else:
            audio.play_stop()

        return result

    def toggle_recording(self):
        """Toggle push-to-talk recording state with debounce."""
        now = time.time()
        if now - self._last_hotkey_time < HOTKEY_DEBOUNCE_SECONDS:
            return
        self._last_hotkey_time = now

        if self.mode_manager.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    # ── Session Recording ─────────────────────────────────────────

    def _resolve_device_index(self, device_name: Optional[str]) -> Optional[int]:
        """Resolve a device name to a sounddevice device index."""
        if not device_name:
            return None
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if dev["name"] == device_name and dev["max_input_channels"] > 0:
                    return i
        except Exception:
            pass
        return None

    def start_session_recording(self) -> bool:
        """Start a session recording (save audio to WAV file)."""
        if self._session_recorder and self._session_recorder.is_recording:
            return False

        system_device = self._resolve_device_index(self.config.session_system_device)

        self._session_recorder = SessionRecorder(
            source_mode=self.config.session_audio_source,
            system_device=system_device,
        )

        try:
            path = self._session_recorder.start()
            if path is None:
                self._session_recorder = None
                self.status_message.emit("Session recording failed to start")
                return False

            get_audio_feedback().play_start()
            self.session_recording_changed.emit(True)
            self._update_any_recording()
            self.status_message.emit("Session recording started")
            return True

        except Exception as e:
            log.error("Session recording error: %s", e)
            self._session_recorder = None
            self.status_message.emit(f"Session recording failed: {e}")
            return False

    def stop_session_recording(self) -> Optional[Path]:
        """Stop session recording and return the saved file path."""
        if not self._session_recorder or not self._session_recorder.is_recording:
            return None

        path = self._session_recorder.stop()
        self._session_recorder = None

        get_audio_feedback().play_stop()
        self.session_recording_changed.emit(False)
        self._update_any_recording()

        if path:
            self.status_message.emit(f"Session saved: {path.name}")
        else:
            self.status_message.emit("Session recording stopped")

        return path

    def toggle_session_recording(self):
        """Toggle session recording on/off."""
        if self._session_recorder and self._session_recorder.is_recording:
            self.stop_session_recording()
        else:
            self.start_session_recording()

    @property
    def is_session_recording(self) -> bool:
        return self._session_recorder is not None and self._session_recorder.is_recording

    # ── Shared ────────────────────────────────────────────────────

    def _update_any_recording(self):
        """Emit unified any-recording-active signal."""
        ptt_active = self.mode_manager.is_recording
        session_active = self.is_session_recording
        self.any_recording_changed.emit(ptt_active or session_active)

    def _apply_output_formatting(self, text: str) -> str:
        """Apply lightweight output formatting based on app context."""
        if not self._app_context:
            return text

        fmt = self._app_context.text_input_format

        if fmt == TextInputFormat.SEARCH_QUERY:
            text = text.strip().rstrip(".,!?;:")
            text = " ".join(text.split())
        elif fmt == TextInputFormat.TERMINAL_COMMAND:
            filler = r"\b(um|uh|so|like|please|can you|could you|go ahead and)\b"
            text = re.sub(filler, "", text, flags=re.IGNORECASE)
            text = " ".join(text.split()).strip().strip(".,!?;:").strip()
        elif fmt == TextInputFormat.URL:
            text = text.replace(" ", "")

        return text

    def _on_text_output(self, text: str):
        """Handle text output from modes (type/paste)."""
        if not text:
            return

        text = self._apply_output_formatting(text)
        success = paste_text(text)

        if success:
            self.status_message.emit("Text pasted")
        else:
            self.status_message.emit("Failed to paste text")

    def update_config(self, new_config: UserConfig):
        """Update configuration and save."""
        self.config = new_config
        self.mode_manager.config = new_config

        # Re-register hotkeys if changed
        self.hotkey_manager.stop()
        self._register_hotkeys()
        self.hotkey_manager.start()

        save_config(new_config)
        self.status_message.emit("Settings saved")

    def start_hotkeys(self) -> bool:
        """Start listening for global hotkeys."""
        return self.hotkey_manager.start()

    def stop_hotkeys(self):
        """Stop listening for global hotkeys."""
        self.hotkey_manager.stop()

    def shutdown(self):
        """Clean shutdown of all components."""
        if self.is_session_recording:
            self._session_recorder.stop()
            self._session_recorder = None

        if self.mode_manager.is_recording:
            self.mode_manager.stop_current_mode()

        self.hotkey_manager.stop()
        log.info("AppController shutdown complete")

    @property
    def is_recording(self) -> bool:
        return self.mode_manager.is_recording

    @property
    def current_mode(self) -> OperatingMode:
        return self._current_mode
