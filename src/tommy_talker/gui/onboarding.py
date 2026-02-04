"""
TommyTalker Onboarding Wizard
First-run setup wizard to guide users through configuration.
"""

from PyQt6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QProgressBar,
    QGroupBox, QFormLayout, QCheckBox, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont

from tommy_talker.utils.config import UserConfig, DEFAULT_HOTKEYS, save_config
from tommy_talker.utils.hardware_detect import HardwareProfile
from tommy_talker.gui.hotkey_selector import HotkeySelector

# Check for ollama
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False


class ModelDownloadThread(QThread):
    """Background thread for downloading Ollama models."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        
    def run(self):
        if not HAS_OLLAMA:
            self.finished.emit(False, "Ollama not installed. Install from ollama.ai")
            return
            
        try:
            for progress in ollama.pull(self.model_name, stream=True):
                status = progress.get("status", "downloading")
                completed = progress.get("completed") or 0
                total = progress.get("total") or 0
                if total and total > 0 and completed is not None:
                    percent = int((completed / total) * 100)
                else:
                    percent = 0
                self.progress.emit(percent, status)
                
            self.finished.emit(True, f"Downloaded {self.model_name}")
        except Exception as e:
            self.finished.emit(False, str(e))


class WelcomePage(QWizardPage):
    """Welcome page introducing TommyTalker."""
    
    def __init__(self, hardware: HardwareProfile):
        super().__init__()
        self.hardware = hardware
        self.setTitle("Welcome to TommyTalker")
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Logo/title
        title = QLabel("🎤 TommyTalker")
        title.setFont(QFont("Helvetica Neue", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("Privacy-First Voice Intelligence Suite")
        subtitle.setFont(QFont("Helvetica Neue", 14))
        subtitle.setStyleSheet("color: #666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(30)
        
        # Hardware info
        hw_frame = QFrame()
        hw_frame.setStyleSheet("background: #f0f4f8; border-radius: 10px; padding: 15px;")
        hw_layout = QVBoxLayout(hw_frame)
        
        hw_title = QLabel("Your System")
        hw_title.setFont(QFont("Helvetica Neue", 12, QFont.Weight.Bold))
        hw_layout.addWidget(hw_title)
        
        hw_info = QLabel(
            f"• Chip: {self.hardware.chip_type}\n"
            f"• RAM: {self.hardware.ram_gb} GB\n"
            f"• Performance Tier: {self.hardware.tier}"
        )
        hw_info.setFont(QFont("Helvetica Neue", 12))
        hw_layout.addWidget(hw_info)
        
        layout.addWidget(hw_frame)
        
        # Features list
        features = QLabel(
            "This wizard will help you:\n\n"
            "1️⃣  Download AI models (Speech-to-Text & LLM)\n"
            "2️⃣  Configure global hotkeys\n"
            "3️⃣  Test your microphone\n"
        )
        features.setFont(QFont("Helvetica Neue", 13))
        layout.addWidget(features)
        
        layout.addStretch()


class ModelsPage(QWizardPage):
    """Model download page."""
    
    def __init__(self, hardware: HardwareProfile):
        super().__init__()
        self.hardware = hardware
        self.download_thread = None
        self.setTitle("Download AI Models")
        self.setSubTitle("Select and download the models for your system.")
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Whisper section
        whisper_group = QGroupBox("🎤 Speech-to-Text (Whisper)")
        whisper_layout = QVBoxLayout(whisper_group)
        
        whisper_info = QLabel(
            "Whisper models download automatically on first transcription.\n"
            f"Recommended for your tier: {self.hardware.whisper_model}"
        )
        whisper_info.setWordWrap(True)
        whisper_info.setStyleSheet("color: #666;")
        whisper_layout.addWidget(whisper_info)
        
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems([
            "mlx-community/distil-whisper-small",
            "mlx-community/distil-whisper-medium.en",
            "mlx-community/distil-whisper-large-v3"
        ])
        # Set recommended based on tier
        idx = self.whisper_combo.findText(self.hardware.whisper_model)
        if idx >= 0:
            self.whisper_combo.setCurrentIndex(idx)
        whisper_layout.addWidget(self.whisper_combo)
        
        self.whisper_status = QLabel("ℹ️ Will download on first use")
        self.whisper_status.setStyleSheet("color: #17a2b8;")
        whisper_layout.addWidget(self.whisper_status)
        
        layout.addWidget(whisper_group)
        
        # LLM section
        llm_group = QGroupBox("🤖 Large Language Model (Ollama)")
        llm_layout = QVBoxLayout(llm_group)
        
        if not HAS_OLLAMA:
            ollama_warning = QLabel("⚠️ Ollama not installed. Please install from ollama.ai first.")
            ollama_warning.setStyleSheet("color: #dc3545; font-weight: bold;")
            llm_layout.addWidget(ollama_warning)
        
        llm_info = QLabel(f"Recommended for your tier: {self.hardware.llm_model}")
        llm_info.setStyleSheet("color: #666;")
        llm_layout.addWidget(llm_info)
        
        self.llm_combo = QComboBox()
        self.llm_combo.addItems([
            "llama3.2:3b",
            "llama3.1:8b",
            "gemma2:27b",
            "qwen2.5:32b"
        ])
        idx = self.llm_combo.findText(self.hardware.llm_model)
        if idx >= 0:
            self.llm_combo.setCurrentIndex(idx)
        llm_layout.addWidget(self.llm_combo)
        
        # Download button and progress
        download_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("⬇️ Download LLM Now")
        self.download_btn.clicked.connect(self._start_download)
        self.download_btn.setEnabled(HAS_OLLAMA)
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #218838; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        download_layout.addWidget(self.download_btn)
        
        self.skip_btn = QPushButton("Skip for now")
        self.skip_btn.clicked.connect(self._skip_download)
        download_layout.addWidget(self.skip_btn)
        
        llm_layout.addLayout(download_layout)
        
        self.llm_progress = QProgressBar()
        self.llm_progress.setVisible(False)
        llm_layout.addWidget(self.llm_progress)
        
        self.llm_status = QLabel("")
        llm_layout.addWidget(self.llm_status)
        
        layout.addWidget(llm_group)
        layout.addStretch()
        
    def _start_download(self):
        """Start downloading the selected LLM model."""
        if self.download_thread and self.download_thread.isRunning():
            return
            
        model = self.llm_combo.currentText()
        
        self.download_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.llm_progress.setVisible(True)
        self.llm_progress.setValue(0)
        self.llm_status.setText(f"Starting download of {model}...")
        self.llm_status.setStyleSheet("color: #007bff;")
        
        self.download_thread = ModelDownloadThread(model)
        self.download_thread.progress.connect(self._on_progress)
        self.download_thread.finished.connect(self._on_finished)
        self.download_thread.start()
        
    def _on_progress(self, percent: int, status: str):
        self.llm_progress.setValue(percent)
        self.llm_status.setText(f"{status} ({percent}%)")
        
    def _on_finished(self, success: bool, message: str):
        self.download_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.llm_progress.setVisible(False)
        
        if success:
            self.llm_status.setText(f"✅ {message}")
            self.llm_status.setStyleSheet("color: #28a745;")
        else:
            self.llm_status.setText(f"❌ {message}")
            self.llm_status.setStyleSheet("color: #dc3545;")
            
    def _skip_download(self):
        self.llm_status.setText("⏭️ Skipped - you can download later from Dashboard")
        self.llm_status.setStyleSheet("color: #6c757d;")
        
    def get_whisper_model(self) -> str:
        """Get the selected Whisper model."""
        return self.whisper_combo.currentText()
    
    def get_llm_model(self) -> str:
        """Get the selected LLM model."""
        return self.llm_combo.currentText()


class HotkeysPage(QWizardPage):
    """Hotkey configuration page."""
    
    # System shortcuts that should never be used
    BLOCKED_SHORTCUTS = {
        "Cmd+Space",      # Spotlight
        "Cmd+Tab",        # App switcher
        "Cmd+Q",          # Quit
        "Cmd+W",          # Close window
        "Cmd+H",          # Hide
        "Cmd+M",          # Minimize
        "Cmd+C",          # Copy
        "Cmd+V",          # Paste
        "Cmd+X",          # Cut
        "Cmd+Z",          # Undo
        "Cmd+A",          # Select all
        "Cmd+S",          # Save
        "Option+Space",   # Special character input
    }
    
    def __init__(self, config: UserConfig):
        super().__init__()
        self.config = config
        self.setTitle("Configure Hotkeys")
        self.setSubTitle("Set up global hotkeys for quick access.")
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        info = QLabel("Select key combinations for each action:")
        info.setStyleSheet("color: #666;")
        layout.addWidget(info)
        
        # Validation status label
        self.validation_label = QLabel("")
        self.validation_label.setStyleSheet("color: #dc3545; font-weight: bold;")
        self.validation_label.setWordWrap(True)
        layout.addWidget(self.validation_label)
        
        form = QFormLayout()
        form.setSpacing(10)
        
        self.hotkey_cursor = HotkeySelector(self.config.hotkeys.get("cursor_mode", DEFAULT_HOTKEYS["cursor_mode"]))
        form.addRow("Cursor Mode:", self.hotkey_cursor)
        
        self.hotkey_editor = HotkeySelector(self.config.hotkeys.get("editor_mode", DEFAULT_HOTKEYS["editor_mode"]))
        form.addRow("Editor Mode:", self.hotkey_editor)
        
        self.hotkey_meeting = HotkeySelector(self.config.hotkeys.get("meeting_mode", DEFAULT_HOTKEYS["meeting_mode"]))
        form.addRow("Meeting Mode:", self.hotkey_meeting)
        
        self.hotkey_hud = HotkeySelector(self.config.hotkeys.get("hud_mode", DEFAULT_HOTKEYS["hud_mode"]))
        form.addRow("HUD Mode:", self.hotkey_hud)
        
        self.hotkey_record = HotkeySelector(self.config.hotkeys.get("toggle_record", DEFAULT_HOTKEYS["toggle_record"]))
        form.addRow("Toggle Recording:", self.hotkey_record)
        
        self.hotkey_dashboard = HotkeySelector(self.config.hotkeys.get("open_dashboard", DEFAULT_HOTKEYS["open_dashboard"]))
        form.addRow("Open Dashboard:", self.hotkey_dashboard)
        
        layout.addLayout(form)
        
        # Recording mode selection
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        mode_label = QLabel("<b>Recording Trigger Mode:</b>")
        layout.addWidget(mode_label)
        
        self.recording_mode_group = QButtonGroup(self)
        
        self.toggle_radio = QRadioButton("Toggle — Press once to start, press again to stop")
        self.recording_mode_group.addButton(self.toggle_radio)
        layout.addWidget(self.toggle_radio)
        
        self.ptt_radio = QRadioButton("Push-to-Talk — Hold to record, release to stop")
        self.recording_mode_group.addButton(self.ptt_radio)
        layout.addWidget(self.ptt_radio)
        
        # Default to toggle
        if self.config.recording_mode == "push_to_talk":
            self.ptt_radio.setChecked(True)
        else:
            self.toggle_radio.setChecked(True)
        
        # Tip
        tip = QLabel("💡 Tip: Push-to-Talk is easier for quick phrases; Toggle is better for longer dictation")
        tip.setStyleSheet("color: #17a2b8; font-style: italic;")
        tip.setWordWrap(True)
        layout.addWidget(tip)
        
        layout.addStretch()
        
    def validatePage(self) -> bool:
        """Validate hotkeys before allowing Next."""
        hotkeys = self.get_hotkeys()
        errors = []
        
        # Check for blocked system shortcuts
        for name, hk in hotkeys.items():
            if hk in self.BLOCKED_SHORTCUTS:
                errors.append(f"⚠️ '{hk}' is a system shortcut")
        
        # Check for duplicates
        seen = {}
        for name, hk in hotkeys.items():
            if hk in seen:
                errors.append(f"⚠️ '{hk}' used for both {seen[hk]} and {name}")
            else:
                seen[hk] = name
        
        if errors:
            self.validation_label.setText("\n".join(errors[:3]))  # Show first 3
            return False
        
        self.validation_label.setText("")
        return True
        
    def get_hotkeys(self) -> dict:
        """Get configured hotkeys."""
        return {
            "cursor_mode": self.hotkey_cursor.get_hotkey(),
            "editor_mode": self.hotkey_editor.get_hotkey(),
            "meeting_mode": self.hotkey_meeting.get_hotkey(),
            "hud_mode": self.hotkey_hud.get_hotkey(),
            "toggle_record": self.hotkey_record.get_hotkey(),
            "open_dashboard": self.hotkey_dashboard.get_hotkey(),
        }
    
    def get_recording_mode(self) -> str:
        """Get selected recording mode (toggle or push_to_talk)."""
        if self.ptt_radio.isChecked():
            return "push_to_talk"
        return "toggle"


class MicTestPage(QWizardPage):
    """Microphone test page."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Test Microphone")
        self.setSubTitle("Make sure your microphone is working correctly.")
        self._setup_ui()
        self.is_testing = False
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Mic info
        info = QLabel(
            "Click the button below to test your microphone.\n"
            "The test will record for 2 seconds and check audio levels."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Test button
        self.test_btn = QPushButton("🎤 Test Microphone")
        self.test_btn.setMinimumHeight(50)
        self.test_btn.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        self.test_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #0056b3; }
        """)
        self.test_btn.clicked.connect(self._test_mic)
        layout.addWidget(self.test_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        # Skip option
        skip_info = QLabel("You can skip this step and test later from the Dashboard.")
        skip_info.setStyleSheet("color: #666; font-size: 11px;")
        skip_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(skip_info)
        
    def _test_mic(self):
        """Run a quick microphone test using blocking record."""
        if self.is_testing:
            return
            
        self.is_testing = True
        self.test_btn.setEnabled(False)
        self.test_btn.setText("🔴 Recording...")
        self.status_label.setText("🎤 Recording for 2 seconds... speak now!")
        self.status_label.setStyleSheet("color: #007bff; font-weight: bold;")
        
        # Use QTimer to let UI update before blocking
        QTimer.singleShot(100, self._do_mic_test)
        
    def _do_mic_test(self):
        """Perform the actual mic test."""
        try:
            import sounddevice as sd
            import numpy as np
            
            # Record for 2 seconds
            duration = 2.0
            sample_rate = 16000
            
            audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
            sd.wait()  # Wait for recording to complete
            
            # Calculate RMS volume
            rms = np.sqrt(np.mean(audio**2))
            max_val = np.max(np.abs(audio))
            
            # Very low max value indicates permission denied (receiving silence)
            if max_val < 0.0001:
                self.status_label.setText(
                    "❌ No audio input detected.\n"
                    "Enable Terminal in System Settings → Privacy → Microphone"
                )
                self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            elif rms > 0.02:  # Stricter threshold - requires actual speech
                self.status_label.setText("✅ Microphone working! Audio detected.")
                self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            elif rms > 0.005:
                self.status_label.setText("⚠️ Low audio. Speak louder or move closer to mic.")
                self.status_label.setStyleSheet("color: #ffc107;")
            else:
                self.status_label.setText(
                    "⚠️ Very low audio. Check mic permissions or settings."
                )
                self.status_label.setStyleSheet("color: #ffc107;")
                
        except Exception as e:
            self.status_label.setText(f"❌ Error: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: #dc3545;")
        finally:
            self.is_testing = False
            self.test_btn.setEnabled(True)
            self.test_btn.setText("🎤 Test Microphone")


class CompletePage(QWizardPage):
    """Setup complete page."""
    
    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete!")
        self.setSubTitle("You're all set to use TommyTalker.")
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)  # Reduced spacing
        
        # Success icon (smaller)
        icon = QLabel("🎉")
        icon.setFont(QFont("Helvetica Neue", 32))  # Smaller
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon)
        
        # Quick start guide
        guide_frame = QFrame()
        guide_frame.setStyleSheet("background: #e8f5e9; border-radius: 10px; padding: 10px;")
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setSpacing(8)
        
        guide_title = QLabel("Quick Start Guide")
        guide_title.setFont(QFont("Helvetica Neue", 13, QFont.Weight.Bold))
        guide_layout.addWidget(guide_title)
        
        # Menu bar info (static) - more compact
        menu_info = QLabel(
            "🎤 <b>Menu Bar:</b> Click microphone icon for modes, settings, quit"
        )
        menu_info.setFont(QFont("Helvetica Neue", 11))
        menu_info.setWordWrap(True)
        guide_layout.addWidget(menu_info)
        
        # Hotkeys section (will be updated dynamically)
        self.hotkeys_label = QLabel("⌨️ <b>Your Hotkeys:</b> Loading...")
        self.hotkeys_label.setFont(QFont("Helvetica Neue", 11))
        self.hotkeys_label.setWordWrap(True)
        guide_layout.addWidget(self.hotkeys_label)
        
        note = QLabel("<i>Change hotkeys anytime: Dashboard → Settings</i>")
        note.setFont(QFont("Helvetica Neue", 10))
        note.setStyleSheet("color: #666;")
        guide_layout.addWidget(note)
        
        layout.addWidget(guide_frame)
        
        # Don't show again checkbox
        self.dont_show_cb = QCheckBox("Don't show this setup wizard again")
        layout.addWidget(self.dont_show_cb)
        
        layout.addStretch()
        
    def initializePage(self):
        """Called when the page is shown - update hotkeys from previous page."""
        # Get hotkeys from the wizard's hotkeys page
        wizard = self.wizard()
        if wizard and hasattr(wizard, 'hotkeys_page'):
            hotkeys = wizard.hotkeys_page.get_hotkeys()
            
            # More compact format - 2 per line
            hotkey_text = "⌨️ <b>Your Hotkeys:</b><br>"
            hotkey_text += f"<b>{hotkeys.get('cursor_mode', '?')}</b> Cursor  •  "
            hotkey_text += f"<b>{hotkeys.get('editor_mode', '?')}</b> Editor  •  "
            hotkey_text += f"<b>{hotkeys.get('meeting_mode', '?')}</b> Meeting<br>"
            hotkey_text += f"<b>{hotkeys.get('hud_mode', '?')}</b> HUD  •  "
            hotkey_text += f"<b>{hotkeys.get('toggle_record', '?')}</b> Record  •  "
            hotkey_text += f"<b>{hotkeys.get('open_dashboard', '?')}</b> Dashboard"
            
            self.hotkeys_label.setText(hotkey_text)


class OnboardingWizard(QWizard):
    """
    First-run onboarding wizard.
    
    Steps:
    1. Welcome - Overview
    2. Download Models - Whisper + LLM
    3. Configure Hotkeys - Set key bindings
    4. Test Microphone - Verify audio
    5. Done - Quick start guide
    """
    
    # Emitted when wizard completes with updated config
    setup_complete = pyqtSignal(UserConfig)
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware
        
        self.setWindowTitle("TommyTalker Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 550)
        
        # Add pages
        self.welcome_page = WelcomePage(hardware)
        self.addPage(self.welcome_page)
        
        self.models_page = ModelsPage(hardware)
        self.addPage(self.models_page)
        
        self.hotkeys_page = HotkeysPage(config)
        self.addPage(self.hotkeys_page)
        
        self.mic_page = MicTestPage()
        self.addPage(self.mic_page)
        
        self.complete_page = CompletePage()
        self.addPage(self.complete_page)
        
        # Connect finish
        self.finished.connect(self._on_finish)
        
    def _on_finish(self, result: int):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            # Update config with selections
            self.config.hotkeys = self.hotkeys_page.get_hotkeys()
            self.config.recording_mode = self.hotkeys_page.get_recording_mode()
            
            # Save model selections from Models page
            self.config.whisper_model = self.models_page.get_whisper_model()
            self.config.llm_model = self.models_page.get_llm_model()
            
            # Set skip_onboarding if checkbox checked
            if self.complete_page.dont_show_cb.isChecked():
                self.config.skip_onboarding = True
            
            # Save config
            save_config(self.config)
            
            self.setup_complete.emit(self.config)
