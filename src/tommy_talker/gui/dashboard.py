"""
TommyTalker Dashboard Window
Settings panel with vocabulary, logging, model selection, and session recording.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QRadioButton,
    QCheckBox, QTextEdit, QButtonGroup,
    QGroupBox, QFormLayout, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from tommy_talker.utils.config import UserConfig, BASE_DATA_DIR
from tommy_talker.utils.hardware_detect import HardwareProfile


class DashboardWindow(QMainWindow):
    """Main dashboard control panel."""

    # Signals
    config_changed_signal = pyqtSignal(UserConfig)

    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware

        self.setWindowTitle("TommyTalker Settings")
        self.setMinimumSize(480, 620)

        self._setup_ui()

    def bring_to_front(self):
        """Show and bring window to foreground (needed with LSUIElement=True)."""
        self.show()
        self.raise_()
        self.activateWindow()

    def _setup_ui(self):
        """Setup the single-page settings UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.setCentralWidget(scroll)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        # Header
        header = QLabel(f"TommyTalker — Tier {self.hardware.tier}")
        header.setFont(QFont("Helvetica Neue", 18, QFont.Weight.Bold))
        layout.addWidget(header)

        # Hardware info
        hw_group = QGroupBox("Hardware")
        hw_layout = QFormLayout(hw_group)
        hw_layout.addRow("Chip:", QLabel(self.hardware.chip_type))
        hw_layout.addRow("RAM:", QLabel(f"{self.hardware.ram_gb} GB"))
        tier_label = "Pro" if self.hardware.tier == 3 else "Standard" if self.hardware.tier == 2 else "Basic"
        hw_layout.addRow("Tier:", QLabel(f"{self.hardware.tier} ({tier_label})"))
        layout.addWidget(hw_group)

        # Whisper model
        whisper_group = QGroupBox("Speech-to-Text (mlx-whisper)")
        whisper_layout = QVBoxLayout(whisper_group)

        whisper_info = QLabel("Models download automatically on first use from HuggingFace.")
        whisper_info.setStyleSheet("color: gray; font-size: 11px;")
        whisper_info.setWordWrap(True)
        whisper_layout.addWidget(whisper_info)

        self.whisper_combo = QComboBox()
        self.whisper_combo.addItems([
            "mlx-community/distil-whisper-small",
            "mlx-community/distil-whisper-medium.en",
            "mlx-community/distil-whisper-large-v3",
        ])
        idx = self.whisper_combo.findText(self.hardware.whisper_model)
        if idx >= 0:
            self.whisper_combo.setCurrentIndex(idx)
        whisper_layout.addWidget(self.whisper_combo)

        layout.addWidget(whisper_group)

        # Hotkey
        hotkey_group = QGroupBox("Hotkey")
        hotkey_layout = QVBoxLayout(hotkey_group)
        hotkey_label = QLabel("Push-to-Talk: <b>Right Command</b> (hold to record, release to paste)")
        hotkey_label.setWordWrap(True)
        hotkey_layout.addWidget(hotkey_label)
        layout.addWidget(hotkey_group)

        # Session Recording
        session_group = QGroupBox("Session Recording")
        session_layout = QVBoxLayout(session_group)

        session_info = QLabel("Record audio sessions to WAV files. Push-to-talk dictation is excluded from session recordings.")
        session_info.setStyleSheet("color: gray; font-size: 11px;")
        session_info.setWordWrap(True)
        session_layout.addWidget(session_info)

        # Audio source radio buttons
        source_label = QLabel("Audio Source:")
        session_layout.addWidget(source_label)

        self.source_group = QButtonGroup(self)
        self.radio_mic = QRadioButton("Microphone")
        self.radio_system = QRadioButton("System Audio")
        self.radio_both = QRadioButton("System Audio + Microphone")
        self.source_group.addButton(self.radio_mic)
        self.source_group.addButton(self.radio_system)
        self.source_group.addButton(self.radio_both)

        current_source = self.config.session_audio_source
        if current_source == "system":
            self.radio_system.setChecked(True)
        elif current_source == "system_and_mic":
            self.radio_both.setChecked(True)
        else:
            self.radio_mic.setChecked(True)

        session_layout.addWidget(self.radio_mic)
        session_layout.addWidget(self.radio_system)
        session_layout.addWidget(self.radio_both)

        # System audio device selector
        device_form = QFormLayout()
        self.device_combo = QComboBox()
        self._populate_audio_devices()
        device_form.addRow("System Audio Device:", self.device_combo)
        session_layout.addLayout(device_form)

        # Enable/disable device combo based on source selection
        self.source_group.buttonClicked.connect(self._on_source_changed)
        self._on_source_changed()

        system_hint = QLabel(
            'To capture system audio, install a virtual audio device like '
            '<a href="https://existential.audio/blackhole/">BlackHole</a> '
            'and select it here.'
        )
        system_hint.setOpenExternalLinks(True)
        system_hint.setStyleSheet("color: gray; font-size: 10px;")
        system_hint.setWordWrap(True)
        session_layout.addWidget(system_hint)

        # Recordings folder
        recordings_path = BASE_DATA_DIR / "Recordings"
        rec_path_label = QLabel(f"Save location: {recordings_path}")
        rec_path_label.setStyleSheet("color: gray; font-size: 10px;")
        rec_path_label.setWordWrap(True)
        session_layout.addWidget(rec_path_label)

        open_rec_btn = QPushButton("Open Recordings Folder")
        open_rec_btn.clicked.connect(lambda: self._open_folder(recordings_path))
        session_layout.addWidget(open_rec_btn)

        layout.addWidget(session_group)

        # Vocabulary
        vocab_group = QGroupBox("Custom Vocabulary")
        vocab_layout = QVBoxLayout(vocab_group)

        vocab_info = QLabel("Words injected into Whisper's initial_prompt for better recognition:")
        vocab_info.setWordWrap(True)
        vocab_layout.addWidget(vocab_info)

        self.vocab_edit = QTextEdit()
        self.vocab_edit.setPlainText(", ".join(self.config.vocabulary))
        self.vocab_edit.setMaximumHeight(60)
        vocab_layout.addWidget(self.vocab_edit)

        layout.addWidget(vocab_group)

        # Logging
        logging_group = QGroupBox("Logging")
        logging_layout = QVBoxLayout(logging_group)

        self.logging_cb = QCheckBox("Enable Logging")
        self.logging_cb.setChecked(self.config.logging_enabled)
        logging_layout.addWidget(self.logging_cb)

        log_path = BASE_DATA_DIR / "logs"
        log_path_label = QLabel(f"Log location: {log_path}")
        log_path_label.setStyleSheet("color: gray; font-size: 10px;")
        log_path_label.setWordWrap(True)
        logging_layout.addWidget(log_path_label)

        open_logs_btn = QPushButton("Open Logs Folder")
        open_logs_btn.clicked.connect(lambda: self._open_folder(log_path))
        logging_layout.addWidget(open_logs_btn)

        layout.addWidget(logging_group)

        # Save button
        save_btn = QPushButton("Save Settings")
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
        scroll.setWidget(container)

    def _populate_audio_devices(self):
        """Populate the audio device dropdown with available input devices."""
        self.device_combo.clear()
        self.device_combo.addItem("(select a device)", None)

        try:
            import sounddevice as sd_query
            devices = sd_query.query_devices()
            for i, dev in enumerate(devices):
                if dev["max_input_channels"] > 0:
                    self.device_combo.addItem(dev["name"], dev["name"])
        except Exception:
            pass

        current = self.config.session_system_device
        if current:
            idx = self.device_combo.findData(current)
            if idx >= 0:
                self.device_combo.setCurrentIndex(idx)

    def _on_source_changed(self):
        """Enable/disable system device combo based on audio source."""
        needs_system = self.radio_system.isChecked() or self.radio_both.isChecked()
        self.device_combo.setEnabled(needs_system)

    def _save_settings(self):
        """Save all settings to config."""
        # Vocabulary
        self.config.vocabulary = [v.strip() for v in self.vocab_edit.toPlainText().split(",") if v.strip()]

        # Logging
        self.config.logging_enabled = self.logging_cb.isChecked()

        # Session recording source
        if self.radio_system.isChecked():
            self.config.session_audio_source = "system"
        elif self.radio_both.isChecked():
            self.config.session_audio_source = "system_and_mic"
        else:
            self.config.session_audio_source = "mic"

        # System audio device
        self.config.session_system_device = self.device_combo.currentData()

        self.config_changed_signal.emit(self.config)

        self.save_status.setText("Settings saved!")
        self.save_status.setStyleSheet("color: #28a745;")
        QTimer.singleShot(3000, lambda: self.save_status.setText(""))

    def _open_folder(self, path):
        """Open a folder in Finder."""
        import subprocess
        from pathlib import Path
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", str(path)])
