"""
TommyTalker Menu Bar Application
System tray integration with mode selection and quick controls.
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QPen
from PyQt6.QtCore import pyqtSignal, QObject, Qt

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
        self.current_mode = config.default_mode
        
        # Create system tray icon
        self.tray_icon = QSystemTrayIcon()
        self._setup_icon(recording=False)
        self._setup_menu()
        
    def _create_microphone_pixmap(self, color: QColor) -> QPixmap:
        """Create a microphone icon pixmap with the specified color."""
        pixmap = QPixmap(22, 22)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set color
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(color)
        
        # Microphone body (rounded rectangle/capsule)
        painter.drawRoundedRect(7, 2, 8, 10, 3, 3)
        
        # Microphone stand (arc + stem)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(4, 6, 14, 12, 0, -180 * 16)
        
        # Stem
        painter.drawLine(11, 14, 11, 17)
        
        # Base
        painter.drawLine(6, 17, 16, 17)
        
        painter.end()
        return pixmap
        
    def _setup_icon(self, recording: bool = False):
        """Setup the tray icon - red when recording, black otherwise."""
        if recording:
            color = QColor(220, 53, 69)  # Red (#dc3545)
            tooltip = "TommyTalker - RECORDING"
        else:
            color = QColor(0, 0, 0)  # Black
            tooltip = "TommyTalker - Click for menu"
            
        pixmap = self._create_microphone_pixmap(color)
        icon = QIcon(pixmap)
        self.tray_icon.setIcon(icon)
        self.tray_icon.setToolTip(tooltip)
        
    def _setup_menu(self):
        """Create the dropdown menu."""
        menu = QMenu()
        
        # Current mode indicator
        self.mode_status_action = QAction(f"Mode: {self.current_mode.upper()}", menu)
        self.mode_status_action.setEnabled(False)
        menu.addAction(self.mode_status_action)
        
        # Recording status
        self.recording_status_action = QAction("🔴 Recording..." if self.is_recording else "⚪ Idle", menu)
        self.recording_status_action.setEnabled(False)
        menu.addAction(self.recording_status_action)
        
        menu.addSeparator()
        
        # Mode selection
        modes_menu = menu.addMenu("🎤 Mode")
        
        self.mode_actions = {}
        for mode in ["cursor", "editor", "scribe", "hud"]:
            action = QAction(mode.title(), modes_menu)
            action.setCheckable(True)
            action.setChecked(mode == self.current_mode)
            action.triggered.connect(lambda checked, m=mode: self._set_mode(m))
            modes_menu.addAction(action)
            self.mode_actions[mode] = action
        
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
        self._update_menu()
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
        
    def _update_menu(self):
        """Update menu to reflect current state."""
        # Update mode status
        self.mode_status_action.setText(f"Mode: {self.current_mode.upper()}")
        
        # Update mode checkmarks
        for mode, action in self.mode_actions.items():
            action.setChecked(mode == self.current_mode)
            
    def update_mode(self, mode: str):
        """Update the current mode (called from outside)."""
        self.current_mode = mode
        self._update_menu()
        
    def show(self):
        """Show the tray icon."""
        self.tray_icon.show()
        
    def hide(self):
        """Hide the tray icon."""
        self.tray_icon.hide()
