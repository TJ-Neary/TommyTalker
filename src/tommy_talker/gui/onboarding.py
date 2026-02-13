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

from tommy_talker.utils.config import UserConfig, save_config
from tommy_talker.utils.hardware_detect import HardwareProfile


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
        title = QLabel("TommyTalker")
        title.setFont(QFont("Helvetica Neue", 28, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Privacy-First Voice-to-Text")
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
            f"Chip: {self.hardware.chip_type}\n"
            f"RAM: {self.hardware.ram_gb} GB\n"
            f"Performance Tier: {self.hardware.tier}"
        )
        hw_info.setFont(QFont("Helvetica Neue", 12))
        hw_layout.addWidget(hw_info)

        layout.addWidget(hw_frame)

        # Features list
        features = QLabel(
            "This wizard will help you:\n\n"
            "1. Select your speech-to-text model\n"
            "2. Test your microphone\n"
        )
        features.setFont(QFont("Helvetica Neue", 13))
        layout.addWidget(features)

        layout.addStretch()


class ModelsPage(QWizardPage):
    """Whisper model selection page."""

    def __init__(self, hardware: HardwareProfile):
        super().__init__()
        self.hardware = hardware
        self.setTitle("Select Speech-to-Text Model")
        self.setSubTitle("Choose a Whisper model based on your hardware tier.")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Whisper section
        whisper_group = QGroupBox("Speech-to-Text (mlx-whisper)")
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

        self.whisper_status = QLabel("Will download on first use")
        self.whisper_status.setStyleSheet("color: #17a2b8;")
        whisper_layout.addWidget(self.whisper_status)

        layout.addWidget(whisper_group)
        layout.addStretch()

    def get_whisper_model(self) -> str:
        """Get the selected Whisper model."""
        return self.whisper_combo.currentText()


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
        self.test_btn = QPushButton("Test Microphone")
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
        self.test_btn.setText("Recording...")
        self.status_label.setText("Recording for 2 seconds... speak now!")
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
            sd.wait()

            # Calculate RMS volume
            rms = np.sqrt(np.mean(audio**2))
            max_val = np.max(np.abs(audio))

            # Very low max value indicates permission denied (receiving silence)
            if max_val < 0.0001:
                self.status_label.setText(
                    "No audio input detected.\n"
                    "Enable Terminal in System Settings > Privacy > Microphone"
                )
                self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")
            elif rms > 0.02:
                self.status_label.setText("Microphone working! Audio detected.")
                self.status_label.setStyleSheet("color: #28a745; font-weight: bold;")
            elif rms > 0.005:
                self.status_label.setText("Low audio. Speak louder or move closer to mic.")
                self.status_label.setStyleSheet("color: #ffc107;")
            else:
                self.status_label.setText(
                    "Very low audio. Check mic permissions or settings."
                )
                self.status_label.setStyleSheet("color: #ffc107;")

        except Exception as e:
            self.status_label.setText(f"Error: {str(e)[:50]}")
            self.status_label.setStyleSheet("color: #dc3545;")
        finally:
            self.is_testing = False
            self.test_btn.setEnabled(True)
            self.test_btn.setText("Test Microphone")


class CompletePage(QWizardPage):
    """Setup complete page."""

    def __init__(self):
        super().__init__()
        self.setTitle("Setup Complete!")
        self.setSubTitle("You're all set to use TommyTalker.")
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Quick start guide
        guide_frame = QFrame()
        guide_frame.setStyleSheet("background: #e8f5e9; border-radius: 10px; padding: 15px;")
        guide_layout = QVBoxLayout(guide_frame)
        guide_layout.setSpacing(8)

        guide_title = QLabel("Quick Start Guide")
        guide_title.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        guide_layout.addWidget(guide_title)

        hotkey_info = QLabel(
            "<b>Push-to-Talk:</b> Hold <b>Right Command</b> to record, release to paste"
        )
        hotkey_info.setFont(QFont("Helvetica Neue", 12))
        hotkey_info.setWordWrap(True)
        guide_layout.addWidget(hotkey_info)

        menu_info = QLabel(
            "<b>Menu Bar:</b> Click the TT icon for settings and controls"
        )
        menu_info.setFont(QFont("Helvetica Neue", 12))
        menu_info.setWordWrap(True)
        guide_layout.addWidget(menu_info)

        context_info = QLabel(
            "<b>App-Aware:</b> Text formatting adapts to the active app automatically"
        )
        context_info.setFont(QFont("Helvetica Neue", 12))
        context_info.setWordWrap(True)
        guide_layout.addWidget(context_info)

        layout.addWidget(guide_frame)

        # Don't show again checkbox
        self.dont_show_cb = QCheckBox("Don't show this setup wizard again")
        layout.addWidget(self.dont_show_cb)

        layout.addStretch()


class OnboardingWizard(QWizard):
    """
    First-run onboarding wizard.

    Steps:
    1. Welcome - Overview and hardware info
    2. Select Model - Choose Whisper model
    3. Test Microphone - Verify audio
    4. Done - Quick start guide
    """

    # Emitted when wizard completes with updated config
    setup_complete = pyqtSignal(UserConfig)

    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware

        self.setWindowTitle("TommyTalker Setup")
        self.setWizardStyle(QWizard.WizardStyle.ModernStyle)
        self.setMinimumSize(600, 500)

        # Add pages
        self.welcome_page = WelcomePage(hardware)
        self.addPage(self.welcome_page)

        self.models_page = ModelsPage(hardware)
        self.addPage(self.models_page)

        self.mic_page = MicTestPage()
        self.addPage(self.mic_page)

        self.complete_page = CompletePage()
        self.addPage(self.complete_page)

        # Connect finish
        self.finished.connect(self._on_finish)

    def _on_finish(self, result: int):
        """Handle wizard completion."""
        if result == QWizard.DialogCode.Accepted:
            # Save model selection
            self.config.whisper_model = self.models_page.get_whisper_model()

            # Set skip_onboarding if checkbox checked
            if self.complete_page.dont_show_cb.isChecked():
                self.config.skip_onboarding = True

            # Save config
            save_config(self.config)

            self.setup_complete.emit(self.config)
