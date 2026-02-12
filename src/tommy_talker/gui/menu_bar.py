"""
TommyTalker Menu Bar Application
System tray integration with mode selection and quick controls.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QPen, QFont
from PyQt6.QtCore import pyqtSignal, QObject, Qt, QRect

from tommy_talker.utils.config import UserConfig
from tommy_talker.utils.hardware_detect import HardwareProfile


class MenuBarApp(QObject):
    """System tray menu bar application."""
    
    # Signals
    open_dashboard_signal = pyqtSignal()
    mode_changed_signal = pyqtSignal(str)
    recording_toggled_signal = pyqtSignal(bool)
    
    def __init__(self, config: UserConfig, hardware: HardwareProfile):
        super().__init__()
        self.config = config
        self.hardware = hardware
        self.is_recording = False
        self.current_mode = "cursor"
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon()
        self._setup_icon(recording=False)
        self._setup_menu()
        
    def _create_tt_pixmap(self, text_color: QColor) -> QPixmap:
        """Create the TT icon: white filled square with TT letters."""
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # White filled square with slight rounding
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255))
        painter.drawRoundedRect(1, 1, 20, 20, 3, 3)

        # TT letters
        font = QFont("Helvetica Neue", 11, QFont.Weight.Bold)
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
        self.recording_status_action = QAction("🔴 Recording..." if self.is_recording else "⚪ Idle", menu)
        self.recording_status_action.setEnabled(False)
        menu.addAction(self.recording_status_action)

        menu.addSeparator()
        
        # Recording toggle
        self.record_action = QAction("🔴 Stop Recording" if self.is_recording else "🎙️ Start Recording", menu)
        self.record_action.triggered.connect(self._toggle_recording)
        menu.addAction(self.record_action)
        
        menu.addSeparator()
        
        # Dashboard
        dashboard_action = QAction("⚙️ Open Dashboard", menu)
        dashboard_action.triggered.connect(self.open_dashboard_signal.emit)
        menu.addAction(dashboard_action)
        
        menu.addSeparator()
        
        # Quit
        quit_action = QAction("Quit TommyTalker", menu)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(menu)
        
    def _set_mode(self, mode: str):
        """Change the current operating mode."""
        self.current_mode = mode
        self.mode_changed_signal.emit(mode)
        print(f"[MenuBar] Mode changed to: {mode}")
        
    def _toggle_recording(self):
        """Toggle recording state."""
        self.is_recording = not self.is_recording
        self._update_recording_ui()
        self.recording_toggled_signal.emit(self.is_recording)
        
    def set_recording_state(self, is_recording: bool):
        """Set the recording state (called from controller)."""
        self.is_recording = is_recording
        self._update_recording_ui()
        
    def _update_recording_ui(self):
        """Update UI elements based on recording state."""
        # Update icon color
        self._setup_icon(recording=self.is_recording)
        
        # Update menu items
        self.record_action.setText("🔴 Stop Recording" if self.is_recording else "🎙️ Start Recording")
        self.recording_status_action.setText("🔴 Recording..." if self.is_recording else "⚪ Idle")
        
    def update_mode(self, mode: str):
        """Update the current mode (called from outside)."""
        self.current_mode = mode
        
    def show(self):
        """Show the tray icon."""
        self.tray_icon.show()
        
    def hide(self):
        """Hide the tray icon."""
        self.tray_icon.hide()
