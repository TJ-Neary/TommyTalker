"""
TommyTalker Menu Bar Application
System tray integration with session recording and quick controls.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QRect

from tommy_talker.utils.config import UserConfig
from tommy_talker.utils.hardware_detect import HardwareProfile


class MenuBarApp(QObject):
    """System tray menu bar application."""

    # Signals
    open_dashboard_signal = pyqtSignal()
    session_recording_toggled_signal = pyqtSignal()

    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware
        self._is_session_recording = False
        self._any_recording = False

        # Create system tray icon
        self.tray_icon = QSystemTrayIcon()
        self._setup_icon(recording=False)
        self._setup_menu()

    def _create_tt_pixmap(self, text_color: QColor) -> QPixmap:
        """Create the TT icon: white filled square with TT letters.

        Uses 2x resolution (44x44 pixels) for Retina clarity, displayed
        at 22x22 logical points via devicePixelRatio.
        """
        scale = 2  # Retina
        size = 22 * scale  # 44x44 actual pixels

        pixmap = QPixmap(size, size)
        pixmap.setDevicePixelRatio(scale)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # White filled square
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(1, 1, 20, 20, 4, 4)

        # TT letters
        font = QFont("Helvetica Neue", 12, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(text_color)
        painter.drawText(QRect(1, 1, 20, 20), Qt.AlignmentFlag.AlignCenter, "TT")

        painter.end()
        return pixmap

    def _setup_icon(self, recording: bool = False):
        """Setup the tray icon - red TT when recording, dark TT otherwise."""
        if recording:
            text_color = QColor(220, 53, 69)  # Red (#dc3545)
            tooltip = "TommyTalker - RECORDING"
        else:
            text_color = QColor(30, 30, 30)  # Near-black
            tooltip = "TommyTalker - Click for menu"

        pixmap = self._create_tt_pixmap(text_color)
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(tooltip)

    def _setup_menu(self):
        """Create the dropdown menu."""
        menu = QMenu()

        # Recording status
        self.status_action = QAction("Idle", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)

        menu.addSeparator()

        # Session recording toggle
        self.session_action = QAction("Start Session Recording", menu)
        self.session_action.triggered.connect(self.session_recording_toggled_signal.emit)
        menu.addAction(self.session_action)

        menu.addSeparator()

        # Dashboard
        dashboard_action = QAction("Settings...", menu)
        dashboard_action.triggered.connect(self.open_dashboard_signal.emit)
        menu.addAction(dashboard_action)

        menu.addSeparator()

        # Quit
        quit_action = QAction("Quit TommyTalker", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)

    def set_session_recording_state(self, is_recording: bool):
        """Update UI for session recording state."""
        self._is_session_recording = is_recording
        if is_recording:
            self.session_action.setText("Stop Session Recording")
            self.status_action.setText("Session Recording...")
        else:
            self.session_action.setText("Start Session Recording")
            if not self._any_recording:
                self.status_action.setText("Idle")

    def set_recording_state(self, is_recording: bool):
        """Update status text for push-to-talk recording state."""
        if is_recording:
            self.status_action.setText("Push-to-Talk...")
        elif self._is_session_recording:
            self.status_action.setText("Session Recording...")
        else:
            self.status_action.setText("Idle")

    def set_any_recording_state(self, any_active: bool):
        """Update icon color based on any recording activity."""
        self._any_recording = any_active
        self._setup_icon(recording=any_active)

    def show(self):
        """Show the tray icon."""
        self.tray_icon.show()

    def hide(self):
        """Hide the tray icon."""
        self.tray_icon.hide()
