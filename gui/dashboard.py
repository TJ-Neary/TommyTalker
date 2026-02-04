"""
TommyTalker Dashboard Window
Main control panel with mode controls, settings, and session management.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QComboBox,
    QLineEdit, QCheckBox, QTextEdit, QProgressBar,
    QGroupBox, QFormLayout, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtGui import QFont

from utils.config import UserConfig, DEFAULT_HOTKEYS
from utils.hardware_detect import HardwareProfile
from gui.hotkey_selector import HotkeySelector
from utils.secure_credentials import (
    store_cloud_api_key, get_cloud_api_key,
    store_cloud_base_url, get_cloud_base_url,
    store_huggingface_token, get_huggingface_token,
    credential_exists
)

# Check for ollama
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False


class OllamaDownloadThread(QThread):
    """Background thread for downloading Ollama models."""
    progress = pyqtSignal(int, str)  # percent, status
    finished = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, model_name: str):
        super().__init__()
        self.model_name = model_name
        
    def run(self):
        if not HAS_OLLAMA:
            self.finished.emit(False, "Ollama not installed")
            return
            
        try:
            for progress in ollama.pull(self.model_name, stream=True):
                status = progress.get("status", "downloading")
                completed = progress.get("completed") or 0
                total = progress.get("total") or 0
                # Handle None and zero cases
                if total and total > 0 and completed is not None:
                    percent = int((completed / total) * 100)
                else:
                    percent = 0
                self.progress.emit(percent, status)
                
            self.finished.emit(True, f"Successfully downloaded {self.model_name}")
        except Exception as e:
            self.finished.emit(False, f"Download failed: {str(e)}")


class DashboardWindow(QMainWindow):
    """Main dashboard control panel."""
    
    # Signals
    clear_session_signal = pyqtSignal()
    config_changed_signal = pyqtSignal(UserConfig)
    mode_activated_signal = pyqtSignal(str)  # Emitted when user clicks Activate button
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware
        self.current_mode = config.default_mode
        self.download_thread = None
        
        self.setWindowTitle("TommyTalker Dashboard")
        self.setMinimumSize(650, 600)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the dashboard UI with tabs."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Header with current mode indicator
        header_layout = QHBoxLayout()
        
        header = QLabel(f"TommyTalker — Tier {self.hardware.tier}")
        header.setFont(QFont("Helvetica Neue", 18, QFont.Weight.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        self.mode_indicator = QLabel(f"Mode: {self.current_mode.upper()}")
        self.mode_indicator.setStyleSheet("color: #007bff; font-weight: bold;")
        header_layout.addWidget(self.mode_indicator)
        
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_modes_tab(), "Modes")
        self.tabs.addTab(self._create_models_tab(), "Models")
        self.tabs.addTab(self._create_settings_tab(), "Settings")
        self.tabs.addTab(self._create_session_tab(), "Session")
        layout.addWidget(self.tabs)
        
    def _create_modes_tab(self) -> QWidget:
        """Create the modes control tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Current mode status
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #e8f4fd; border-radius: 8px; padding: 10px;")
        status_layout = QVBoxLayout(status_frame)
        
        self.current_mode_label = QLabel(f"🎯 Active Mode: {self.current_mode.upper()}")
        self.current_mode_label.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        status_layout.addWidget(self.current_mode_label)
        
        layout.addWidget(status_frame)
        
        # Mode cards - all hotkeys read from config
        modes = [
            ("cursor", "🎤 Cursor Mode", "Live transcription → Types at your cursor", 
             self.config.hotkeys.get("cursor_mode", "Ctrl+Shift+Space")),
            ("editor", "✍️ Editor Mode", "Record → LLM rewrites → Pastes result", 
             self.config.hotkeys.get("editor_mode", "Ctrl+Shift+E")),
            ("meeting", "📝 Meeting Mode", "Meeting assistant with speaker diarization", 
             self.config.hotkeys.get("meeting_mode", "Ctrl+Shift+M")),
            ("hud", "👁️ HUD Mode", "Transparent overlay (screen-share invisible)", 
             self.config.hotkeys.get("hud_mode", "Ctrl+Shift+H")),
        ]
        
        self.mode_buttons = {}
        self.mode_hotkey_labels = {}
        
        for mode_id, name, desc, hotkey in modes:
            group = QGroupBox(name)
            group_layout = QVBoxLayout(group)
            
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            group_layout.addWidget(desc_label)
            
            hotkey_label = QLabel(f"Hotkey: {hotkey}")
            hotkey_label.setStyleSheet("color: gray; font-size: 11px;")
            hotkey_label.setObjectName(f"hotkey_{mode_id}")
            self.mode_hotkey_labels[mode_id] = hotkey_label
            group_layout.addWidget(hotkey_label)
            
            btn_layout = QHBoxLayout()
            
            activate_btn = QPushButton(f"Activate")
            activate_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            activate_btn.clicked.connect(lambda checked, m=mode_id: self._activate_mode(m))
            self.mode_buttons[mode_id] = activate_btn
            btn_layout.addWidget(activate_btn)
            
            btn_layout.addStretch()
            group_layout.addLayout(btn_layout)
            
            layout.addWidget(group)
        
        # Update button states
        self._update_mode_buttons()
            
        layout.addStretch()
        return widget
    
    def _activate_mode(self, mode: str):
        """Handle mode activation."""
        self.current_mode = mode
        self._update_mode_buttons()
        self.current_mode_label.setText(f"🎯 Active Mode: {mode.upper()}")
        self.mode_indicator.setText(f"Mode: {mode.upper()}")
        self.mode_activated_signal.emit(mode)
        print(f"[Dashboard] Mode activated: {mode}")
        
    def _update_mode_buttons(self):
        """Update button states to show which mode is active."""
        for mode_id, btn in self.mode_buttons.items():
            if mode_id == self.current_mode:
                btn.setText("✓ Active")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        padding: 8px 20px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                """)
                btn.setEnabled(False)
            else:
                btn.setText("Activate")
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #28a745;
                        color: white;
                        padding: 8px 20px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover {
                        background-color: #218838;
                    }
                """)
                btn.setEnabled(True)
        
    def _create_models_tab(self) -> QWidget:
        """Create the model manager tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Current tier info
        tier_info = QGroupBox("Hardware Tier")
        tier_layout = QFormLayout(tier_info)
        tier_layout.addRow("Chip:", QLabel(self.hardware.chip_type))
        tier_layout.addRow("RAM:", QLabel(f"{self.hardware.ram_gb} GB"))
        tier_layout.addRow("Tier:", QLabel(f"{self.hardware.tier} ({'Pro' if self.hardware.tier == 3 else 'Standard' if self.hardware.tier == 2 else 'Basic'})"))
        layout.addWidget(tier_info)
        
        # Whisper model
        whisper_group = QGroupBox("🎤 Speech-to-Text (mlx_whisper)")
        whisper_layout = QVBoxLayout(whisper_group)
        
        whisper_info = QLabel("Models download automatically on first use from HuggingFace.")
        whisper_info.setStyleSheet("color: gray; font-size: 11px;")
        whisper_info.setWordWrap(True)
        whisper_layout.addWidget(whisper_info)
        
        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems([
            "mlx-community/distil-whisper-small",
            "mlx-community/distil-whisper-medium.en",
            "mlx-community/distil-whisper-large-v3"
        ])
        # Try to set current value, default to tier-appropriate
        current_whisper = self.hardware.whisper_model
        idx = self.whisper_combo.findText(current_whisper)
        if idx >= 0:
            self.whisper_combo.setCurrentIndex(idx)
        whisper_layout.addWidget(self.whisper_combo)
        
        self.whisper_status = QLabel("ℹ️ Will download on first transcription")
        self.whisper_status.setStyleSheet("color: #6c757d;")
        whisper_layout.addWidget(self.whisper_status)
        
        layout.addWidget(whisper_group)
        
        # LLM model (Ollama)
        llm_group = QGroupBox("🤖 LLM (Ollama)")
        llm_layout = QVBoxLayout(llm_group)
        
        # Check Ollama status
        if not HAS_OLLAMA:
            ollama_warning = QLabel("⚠️ Ollama not installed. Install from ollama.ai")
            ollama_warning.setStyleSheet("color: #dc3545; font-weight: bold;")
            llm_layout.addWidget(ollama_warning)
        
        self.llm_combo = QComboBox()
        self.llm_combo.addItems([
            "llama3.2:3b",
            "llama3.1:8b", 
            "gemma2:27b",
            "qwen2.5:32b"
        ])
        # Set to tier-appropriate default
        current_llm = self.hardware.llm_model
        idx = self.llm_combo.findText(current_llm)
        if idx >= 0:
            self.llm_combo.setCurrentIndex(idx)
        llm_layout.addWidget(self.llm_combo)
        
        # Advanced mode - manual model entry
        self.advanced_mode_cb = QCheckBox("Advanced Mode (enter custom model tag)")
        self.advanced_mode_cb.setChecked(self.config.advanced_mode)
        self.advanced_mode_cb.toggled.connect(self._toggle_advanced_mode)
        llm_layout.addWidget(self.advanced_mode_cb)
        
        self.manual_model_input = QLineEdit()
        self.manual_model_input.setPlaceholderText("e.g., qwen2.5:32b, mistral:latest")
        self.manual_model_input.setVisible(self.config.advanced_mode)
        if self.config.custom_llm_model:
            self.manual_model_input.setText(self.config.custom_llm_model)
        llm_layout.addWidget(self.manual_model_input)
        
        # Download section
        download_layout = QHBoxLayout()
        
        self.llm_download_btn = QPushButton("⬇️ Download Model")
        self.llm_download_btn.clicked.connect(self._download_llm_model)
        self.llm_download_btn.setEnabled(HAS_OLLAMA)
        download_layout.addWidget(self.llm_download_btn)
        
        download_layout.addStretch()
        llm_layout.addLayout(download_layout)
        
        self.llm_progress = QProgressBar()
        self.llm_progress.setVisible(False)
        llm_layout.addWidget(self.llm_progress)
        
        self.llm_status = QLabel("")
        self.llm_status.setWordWrap(True)
        llm_layout.addWidget(self.llm_status)
        
        layout.addWidget(llm_group)
        
        layout.addStretch()
        return widget
    
    def _download_llm_model(self):
        """Start downloading the selected LLM model."""
        if self.download_thread and self.download_thread.isRunning():
            QMessageBox.warning(self, "Download in Progress", "Please wait for the current download to complete.")
            return
        
        # Get model name
        if self.advanced_mode_cb.isChecked() and self.manual_model_input.text():
            model = self.manual_model_input.text().strip()
        else:
            model = self.llm_combo.currentText()
        
        if not model:
            QMessageBox.warning(self, "No Model Selected", "Please select or enter a model name.")
            return
        
        print(f"[Dashboard] Starting download: {model}")
        
        # Update UI
        self.llm_download_btn.setEnabled(False)
        self.llm_download_btn.setText("Downloading...")
        self.llm_progress.setVisible(True)
        self.llm_progress.setValue(0)
        self.llm_status.setText(f"Starting download of {model}...")
        self.llm_status.setStyleSheet("color: #007bff;")
        
        # Start download thread
        self.download_thread = OllamaDownloadThread(model)
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.start()
        
    def _on_download_progress(self, percent: int, status: str):
        """Handle download progress updates."""
        self.llm_progress.setValue(percent)
        self.llm_status.setText(f"{status} ({percent}%)")
        
    def _on_download_finished(self, success: bool, message: str):
        """Handle download completion."""
        self.llm_download_btn.setEnabled(True)
        self.llm_download_btn.setText("⬇️ Download Model")
        self.llm_progress.setVisible(False)
        
        if success:
            self.llm_status.setText(f"✅ {message}")
            self.llm_status.setStyleSheet("color: #28a745;")
            QMessageBox.information(self, "Download Complete", message)
        else:
            self.llm_status.setText(f"❌ {message}")
            self.llm_status.setStyleSheet("color: #dc3545;")
            QMessageBox.critical(self, "Download Failed", message)
        
    def _create_settings_tab(self) -> QWidget:
        """Create the settings tab with HuggingFace token, Cloud Mode, and hotkeys."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Hotkeys section - using dropdown selectors
        hotkeys_group = QGroupBox("⌨️ Global Hotkeys")
        hotkeys_layout = QVBoxLayout(hotkeys_group)
        
        hotkey_info = QLabel("Select modifier keys and final key for each hotkey:")
        hotkey_info.setStyleSheet("color: gray; font-size: 11px;")
        hotkey_info.setWordWrap(True)
        hotkeys_layout.addWidget(hotkey_info)
        
        # Use grid layout for cleaner display (2 columns: label | selector)
        from PyQt6.QtWidgets import QGridLayout
        hotkey_grid = QGridLayout()
        hotkey_grid.setSpacing(8)
        
        # Mode hotkeys using dropdown selectors - stacked in grid
        hotkey_items = [
            ("Cursor Mode:", "cursor_mode", "Ctrl+Shift+Space"),
            ("Editor Mode:", "editor_mode", "Ctrl+Shift+E"),
            ("Meeting Mode:", "meeting_mode", "Ctrl+Shift+M"),
            ("HUD Mode:", "hud_mode", "Ctrl+Shift+H"),
            ("Toggle Recording:", "toggle_record", "Ctrl+Shift+R"),
            ("Open Dashboard:", "open_dashboard", "Ctrl+Shift+D"),
        ]
        
        self.hotkey_selectors = {}
        for row, (label_text, key, default) in enumerate(hotkey_items):
            label = QLabel(label_text)
            label.setMinimumWidth(120)
            hotkey_grid.addWidget(label, row, 0)
            
            selector = HotkeySelector(self.config.hotkeys.get(key, default))
            self.hotkey_selectors[key] = selector
            hotkey_grid.addWidget(selector, row, 1)
        
        # Convenience references for save/reset
        self.hotkey_cursor = self.hotkey_selectors["cursor_mode"]
        self.hotkey_editor = self.hotkey_selectors["editor_mode"]
        self.hotkey_meeting = self.hotkey_selectors["meeting_mode"]
        self.hotkey_hud = self.hotkey_selectors["hud_mode"]
        self.hotkey_record = self.hotkey_selectors["toggle_record"]
        self.hotkey_dashboard = self.hotkey_selectors["open_dashboard"]
        
        hotkeys_layout.addLayout(hotkey_grid)
        
        # Reset defaults button
        reset_btn = QPushButton("↩️ Reset to Defaults")
        reset_btn.clicked.connect(self._reset_hotkeys)
        hotkeys_layout.addWidget(reset_btn)
        
        layout.addWidget(hotkeys_group)
        
        # Recording Mode section
        recording_group = QGroupBox("🎙️ Recording Mode")
        recording_layout = QVBoxLayout(recording_group)
        
        recording_info = QLabel("Choose how hotkeys trigger recording:")
        recording_info.setStyleSheet("color: gray; font-size: 11px;")
        recording_layout.addWidget(recording_info)
        
        # Radio buttons for mode selection
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        self.recording_mode_group = QButtonGroup(self)
        
        self.toggle_radio = QRadioButton("Toggle — Press once to start, press again to stop")
        self.toggle_radio.setToolTip("Tap the hotkey to start recording, tap again to stop and transcribe.")
        self.recording_mode_group.addButton(self.toggle_radio)
        recording_layout.addWidget(self.toggle_radio)
        
        self.ptt_radio = QRadioButton("Push-to-Talk — Hold to record, release to stop")
        self.ptt_radio.setToolTip("Hold the hotkey while speaking. Release when done to transcribe.")
        self.recording_mode_group.addButton(self.ptt_radio)
        recording_layout.addWidget(self.ptt_radio)
        
        # Set current state from config
        if self.config.recording_mode == "push_to_talk":
            self.ptt_radio.setChecked(True)
        else:
            self.toggle_radio.setChecked(True)
        
        layout.addWidget(recording_group)
        
        # Cloud Mode - Hybrid Cloud Uplink
        cloud_group = QGroupBox("☁️ Cloud Mode (Hybrid Uplink)")
        cloud_layout = QVBoxLayout(cloud_group)
        
        cloud_info = QLabel("Offload LLM inference to OpenAI-compatible API (OpenAI, Groq, OpenRouter)")
        cloud_info.setWordWrap(True)
        cloud_info.setStyleSheet("color: gray;")
        cloud_layout.addWidget(cloud_info)
        
        self.cloud_mode_cb = QCheckBox("Enable Cloud Mode")
        self.cloud_mode_cb.setChecked(self.config.cloud_mode_enabled)
        self.cloud_mode_cb.toggled.connect(self._toggle_cloud_mode)
        cloud_layout.addWidget(self.cloud_mode_cb)
        
        cloud_form = QFormLayout()
        
        self.cloud_base_url = QLineEdit(self.config.cloud_api_base_url)
        self.cloud_base_url.setPlaceholderText("https://api.openai.com/v1")
        cloud_form.addRow("API Base URL:", self.cloud_base_url)
        
        self.cloud_model = QLineEdit(self.config.cloud_api_model)
        self.cloud_model.setPlaceholderText("gpt-4o-mini")
        cloud_form.addRow("Model:", self.cloud_model)
        
        self.cloud_api_key = QLineEdit()
        self.cloud_api_key.setPlaceholderText("sk-... (stored in .env)")
        self.cloud_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        if self.config.cloud_api_key_set:
            self.cloud_api_key.setPlaceholderText("••••••••• (key saved)")
        cloud_form.addRow("API Key:", self.cloud_api_key)
        
        cloud_layout.addLayout(cloud_form)
        self._update_cloud_fields(self.config.cloud_mode_enabled)
        
        layout.addWidget(cloud_group)
        
        # HuggingFace Token
        hf_group = QGroupBox("🤗 HuggingFace Token (for Diarization)")
        hf_layout = QVBoxLayout(hf_group)
        
        hf_info = QLabel("Required for speaker diarization. Get token at: huggingface.co/settings/tokens")
        hf_info.setWordWrap(True)
        hf_info.setStyleSheet("color: gray; font-size: 11px;")
        hf_layout.addWidget(hf_info)
        
        self.hf_token_input = QLineEdit()
        self.hf_token_input.setPlaceholderText("hf_... (stored in .env)")
        self.hf_token_input.setEchoMode(QLineEdit.EchoMode.Password)
        if self.config.huggingface_token_set:
            self.hf_token_input.setPlaceholderText("••••••••• (token saved)")
        hf_layout.addWidget(self.hf_token_input)
        
        layout.addWidget(hf_group)
        
        # Vocabulary
        vocab_group = QGroupBox("📝 Custom Vocabulary (for Whisper)")
        vocab_layout = QVBoxLayout(vocab_group)
        
        vocab_info = QLabel("Words injected into Whisper's initial_prompt for better recognition:")
        vocab_info.setWordWrap(True)
        vocab_layout.addWidget(vocab_info)
        
        self.vocab_edit = QTextEdit()
        self.vocab_edit.setPlainText(", ".join(self.config.vocabulary))
        self.vocab_edit.setMaximumHeight(60)
        vocab_layout.addWidget(self.vocab_edit)
        
        layout.addWidget(vocab_group)
        
        # Logging section
        logging_group = QGroupBox("📋 Logging")
        logging_layout = QVBoxLayout(logging_group)
        
        self.logging_cb = QCheckBox("Enable Logging")
        self.logging_cb.setChecked(self.config.logging_enabled)
        logging_layout.addWidget(self.logging_cb)
        
        from utils.config import BASE_DATA_DIR
        log_path = BASE_DATA_DIR / "logs"
        log_path_label = QLabel(f"Log location: {log_path}")
        log_path_label.setStyleSheet("color: gray; font-size: 10px;")
        log_path_label.setWordWrap(True)
        logging_layout.addWidget(log_path_label)
        
        open_logs_btn = QPushButton("📂 Open Logs Folder")
        open_logs_btn.clicked.connect(lambda: self._open_folder(log_path))
        logging_layout.addWidget(open_logs_btn)
        
        layout.addWidget(logging_group)
        
        # Save button
        save_btn = QPushButton("💾 Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 10px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        save_btn.clicked.connect(self._save_settings)
        layout.addWidget(save_btn)
        
        self.save_status = QLabel("")
        layout.addWidget(self.save_status)
        
        layout.addStretch()
        return widget
    
    def _reset_hotkeys(self):
        """Reset hotkeys to defaults."""
        self.hotkey_cursor.set_hotkey(DEFAULT_HOTKEYS["cursor_mode"])
        self.hotkey_editor.set_hotkey(DEFAULT_HOTKEYS["editor_mode"])
        self.hotkey_meeting.set_hotkey(DEFAULT_HOTKEYS["meeting_mode"])
        self.hotkey_hud.set_hotkey(DEFAULT_HOTKEYS["hud_mode"])
        self.hotkey_record.set_hotkey(DEFAULT_HOTKEYS["toggle_record"])
        self.hotkey_dashboard.set_hotkey(DEFAULT_HOTKEYS["open_dashboard"])
        self.save_status.setText("Hotkeys reset to defaults. Click Save to apply.")
        self.save_status.setStyleSheet("color: #6c757d;")
        
    def _create_session_tab(self) -> QWidget:
        """Create the session management tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Session info
        info_group = QGroupBox("Current Session")
        info_layout = QVBoxLayout(info_group)
        
        self.session_label = QLabel("No active session")
        info_layout.addWidget(self.session_label)
        
        self.recording_count_label = QLabel("Recordings: 0")
        info_layout.addWidget(self.recording_count_label)
        
        layout.addWidget(info_group)
        
        # Session hygiene
        hygiene_group = QGroupBox("Session Hygiene")
        hygiene_layout = QVBoxLayout(hygiene_group)
        
        hygiene_info = QLabel(
            "Clear all session data to prevent data bleeding between interviews.\n"
            "This will wipe the vector store (ChromaDB) and transcripts."
        )
        hygiene_info.setWordWrap(True)
        hygiene_info.setStyleSheet("color: gray;")
        hygiene_layout.addWidget(hygiene_info)
        
        clear_btn = QPushButton("🗑️ Clear Session")
        clear_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold; padding: 10px;")
        clear_btn.clicked.connect(self._clear_session)
        hygiene_layout.addWidget(clear_btn)
        
        layout.addWidget(hygiene_group)
        
        layout.addStretch()
        return widget
        
    def _toggle_advanced_mode(self, checked: bool):
        """Toggle advanced mode for manual model entry."""
        self.manual_model_input.setVisible(checked)
        self.config.advanced_mode = checked
        
    def _toggle_cloud_mode(self, checked: bool):
        """Toggle Cloud Mode."""
        self._update_cloud_fields(checked)
        
    def _update_cloud_fields(self, enabled: bool):
        """Enable/disable cloud fields based on toggle."""
        self.cloud_base_url.setEnabled(enabled)
        self.cloud_model.setEnabled(enabled)
        self.cloud_api_key.setEnabled(enabled)
        
    def _save_settings(self):
        """Save all settings to config, storing sensitive data securely."""
        # Store HuggingFace token securely
        hf_token = self.hf_token_input.text()
        if hf_token:
            store_huggingface_token(hf_token)
            self.config.huggingface_token_set = True
            self.hf_token_input.clear()
            self.hf_token_input.setPlaceholderText("••••••••• (token saved)")
        
        # Store Cloud API key securely
        cloud_key = self.cloud_api_key.text()
        if cloud_key:
            store_cloud_api_key(cloud_key)
            self.config.cloud_api_key_set = True
            self.cloud_api_key.clear()
            self.cloud_api_key.setPlaceholderText("••••••••• (key saved)")
        
        # Update config with non-sensitive data
        self.config.cloud_mode_enabled = self.cloud_mode_cb.isChecked()
        self.config.cloud_api_base_url = self.cloud_base_url.text()
        self.config.cloud_api_model = self.cloud_model.text()
        
        # Hotkeys - get from HotkeySelector widgets
        self.config.hotkeys = {
            "cursor_mode": self.hotkey_cursor.get_hotkey(),
            "editor_mode": self.hotkey_editor.get_hotkey(),
            "meeting_mode": self.hotkey_meeting.get_hotkey(),
            "hud_mode": self.hotkey_hud.get_hotkey(),
            "toggle_record": self.hotkey_record.get_hotkey(),
            "open_dashboard": self.hotkey_dashboard.get_hotkey(),
        }
        
        # Update hotkey labels in Modes tab for all modes
        for mode_id in ["cursor", "editor", "meeting", "hud"]:
            hotkey = self.config.hotkeys.get(f"{mode_id}_mode", "")
            if mode_id in self.mode_hotkey_labels:
                self.mode_hotkey_labels[mode_id].setText(f"Hotkey: {hotkey}")
        
        # Vocabulary
        self.config.vocabulary = [v.strip() for v in self.vocab_edit.toPlainText().split(",") if v.strip()]
        
        # Recording mode (toggle vs push-to-talk)
        if self.ptt_radio.isChecked():
            self.config.recording_mode = "push_to_talk"
        else:
            self.config.recording_mode = "toggle"
        
        # Logging
        self.config.logging_enabled = self.logging_cb.isChecked()
        
        # Advanced mode model
        if self.advanced_mode_cb.isChecked():
            self.config.custom_llm_model = self.manual_model_input.text().strip() or None
        
        # Emit signal and show confirmation
        self.config_changed_signal.emit(self.config)
        
        self.save_status.setText("✅ Settings saved!")
        self.save_status.setStyleSheet("color: #28a745;")
        
        # Clear status after 3 seconds
        QTimer.singleShot(3000, lambda: self.save_status.setText(""))
        
    def _clear_session(self):
        """Clear the current session data."""
        reply = QMessageBox.question(
            self,
            "Clear Session",
            "Are you sure you want to clear all session data?\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.clear_session_signal.emit()
            self.session_label.setText("Session cleared")
            self.recording_count_label.setText("Recordings: 0")
            QMessageBox.information(self, "Session Cleared", "All session data has been cleared.")
    
    def update_mode(self, mode: str):
        """Update the displayed current mode (called from outside)."""
        self.current_mode = mode
        self._update_mode_buttons()
        self.current_mode_label.setText(f"🎯 Active Mode: {mode.upper()}")
        self.mode_indicator.setText(f"Mode: {mode.upper()}")
        
    def _open_folder(self, path):
        """Open a folder in Finder."""
        import subprocess
        from pathlib import Path
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(path)])

