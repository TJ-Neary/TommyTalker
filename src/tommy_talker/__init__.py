"""
TommyTalker - Privacy-first voice intelligence suite for macOS.

Local-first speech-to-text via mlx-whisper, LLM-powered text rewriting via Ollama,
speaker diarization via pyannote.audio, and RAG-based meeting transcription via ChromaDB.
"""

__version__ = "0.1.0"

# Lazy imports - components are imported when accessed to avoid loading
# heavy dependencies at package import time.
#
# Direct imports:
#   from tommy_talker.engine import AudioCapture
#   from tommy_talker.utils import load_config
#   from tommy_talker.gui import DashboardWindow
#   from tommy_talker.app_controller import AppController

__all__ = [
    # Engine
    "AudioCapture",
    "DualStreamRecorder",
    "Transcriber",
    "LLMClient",
    "Diarizer",
    "RAGStore",
    "OperatingMode",
    "ModeManager",
    "ModeResult",
    # Utils
    "HardwareProfile",
    "detect_hardware",
    "UserConfig",
    "load_config",
    "save_config",
    "ensure_data_dirs",
    "PermissionStatus",
    "check_permissions",
    "HotkeyManager",
    "type_at_cursor",
    "paste_text",
    # GUI
    "MenuBarApp",
    "DashboardWindow",
    "HUDOverlay",
    "SetupGuideWindow",
    # Controller
    "AppController",
]
