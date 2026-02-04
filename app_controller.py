"""
TommyTalker Application Controller
Main application orchestration connecting GUI, engine, and utils.
"""

import time
from typing import Optional
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from engine.modes import ModeManager, OperatingMode, ModeResult
from utils.config import UserConfig, save_config
from utils.hardware_detect import HardwareProfile
from utils.hotkeys import HotkeyManager
from utils.typing import type_at_cursor, paste_text
from utils.audio_feedback import get_audio_feedback

# Minimum time between hotkey triggers (debounce)
HOTKEY_DEBOUNCE_SECONDS = 0.5


class AppController(QObject):
    """
    Central application controller that wires together all components.
    
    Responsibilities:
    - Mode switching and recording control
    - Hotkey registration and handling
    - Text output (typing/pasting)
    - Configuration updates
    """
    
    # Signals for GUI updates
    mode_changed = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal(object)  # ModeResult
    recording_changed = pyqtSignal(bool)  # True = recording, False = idle
    live_text_updated = pyqtSignal(str)
    status_message = pyqtSignal(str)
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware
        
        # Debounce tracking for hotkeys
        self._last_hotkey_time: float = 0
        
        # Initialize mode manager
        self.mode_manager = ModeManager(config, hardware)
        self.mode_manager.on_text_output = self._on_text_output
        self.mode_manager.on_live_text = self._on_live_text
        
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
            if is_push_to_talk:
                # Push-to-talk: start on key-down, stop on key-up
                self.hotkey_manager.register(
                    hotkeys["cursor_mode"],
                    self._on_cursor_hotkey_down,
                    "Cursor Mode",
                    callback_up=self._on_hotkey_up
                )
            else:
                # Toggle: just key-down toggles state
                self.hotkey_manager.register(
                    hotkeys["cursor_mode"],
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
        # Stop any active recording first
        if self.mode_manager.is_recording:
            self.stop_recording()
            
        self._current_mode = mode
        self.mode_changed.emit(mode.value)
        self.status_message.emit(f"Mode: {mode.value.title()}")
        
    def start_recording(self) -> bool:
        """Start recording in the current mode."""
        success = self.mode_manager.start_mode(self._current_mode)
        
        if success:
            # Play audio feedback
            get_audio_feedback().play_start()
            
            self.recording_started.emit()
            self.recording_changed.emit(True)
            self.status_message.emit(f"Recording ({self._current_mode.value})...")
            
        return success
        
    def stop_recording(self) -> Optional[ModeResult]:
        """Stop recording and process result."""
        result = self.mode_manager.stop_current_mode()
        
        # Play audio feedback
        get_audio_feedback().play_stop()
        
        self.recording_changed.emit(False)
        
        if result:
            self.recording_stopped.emit(result)
            
            if result.success:
                self.status_message.emit("Recording processed")
            else:
                self.status_message.emit(f"Error: {result.error}")
                get_audio_feedback().play_error()
                
        return result
        
    def toggle_recording(self):
        """Toggle recording state with debounce protection."""
        # Debounce: ignore if triggered too quickly (prevents key repeat issues)
        now = time.time()
        if now - self._last_hotkey_time < HOTKEY_DEBOUNCE_SECONDS:
            return  # Ignore this trigger
        self._last_hotkey_time = now
        
        if self.mode_manager.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
            
    def _on_text_output(self, text: str):
        """Handle text output from modes (type/paste)."""
        if not text:
            return
            
        # Use paste for better reliability
        success = paste_text(text)
        
        if success:
            self.status_message.emit("Text pasted")
        else:
            self.status_message.emit("Failed to paste text")
            
    def _on_live_text(self, text: str):
        """Handle live text updates (HUD mode)."""
        self.live_text_updated.emit(text)
        
    def update_config(self, new_config: UserConfig):
        """Update configuration and save."""
        self.config = new_config
        self.mode_manager.config = new_config
        
        # Re-register hotkeys if changed
        self.hotkey_manager.stop()
        self._register_hotkeys()
        self.hotkey_manager.start()
        
        # Save to disk
        save_config(new_config)
        self.status_message.emit("Settings saved")
        
    def clear_session(self):
        """Clear session data (RAG, etc.)."""
        from engine.rag_store import RAGStore
        from utils.config import get_chroma_path
        
        rag = RAGStore(get_chroma_path())
        success = rag.clear_session()
        
        if success:
            self.status_message.emit("Session cleared")
        else:
            self.status_message.emit("Failed to clear session")
            
    def start_hotkeys(self) -> bool:
        """Start listening for global hotkeys."""
        return self.hotkey_manager.start()
        
    def stop_hotkeys(self):
        """Stop listening for global hotkeys."""
        self.hotkey_manager.stop()
        
    def shutdown(self):
        """Clean shutdown of all components."""
        # Stop any active recording
        if self.mode_manager.is_recording:
            self.mode_manager.stop_current_mode()
            
        # Stop hotkeys
        self.hotkey_manager.stop()
        
        print("[AppController] Shutdown complete")
        
    @property
    def is_recording(self) -> bool:
        return self.mode_manager.is_recording
        
    @property
    def current_mode(self) -> OperatingMode:
        return self._current_mode
