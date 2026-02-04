"""
TommyTalker Setup Guide
Permission wizard shown on first run if Microphone or Accessibility permissions are missing.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from utils.permissions import PermissionStatus, check_permissions, open_system_preferences


class SetupGuideWindow(QMainWindow):
    """
    Setup wizard that blocks the main app until required permissions are granted.
    
    Required permissions:
    - Microphone: For audio capture
    - Accessibility: For typing at cursor (pyautogui) and global hotkeys
    """
    
    # Emitted when all permissions are granted
    permissions_granted = pyqtSignal()
    
    def __init__(self, initial_status: PermissionStatus):
        super().__init__()
        self.perm_status = initial_status
        
        self.setWindowTitle("TommyTalker Setup")
        self.setFixedSize(550, 520)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        
        self._setup_ui()
        
        # Start polling for permission changes
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_permissions)
        self.check_timer.start(1000)  # Check every second
        
    def _setup_ui(self):
        """Setup the permission wizard UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)
        
        # Header
        title = QLabel("🔐 TommyTalker Setup")
        title.setFont(QFont("Helvetica Neue", 22, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("TommyTalker needs 2 permissions to function properly.")
        subtitle.setFont(QFont("Helvetica Neue", 13))
        subtitle.setStyleSheet("color: #666666;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(10)
        
        # Microphone permission
        self.mic_frame = self._create_permission_card(
            title="🎤 Microphone Access",
            description="Required to capture your voice for transcription.",
            instructions="Click 'Grant' → Find 'Terminal' or 'Python' → Toggle ON",
            is_granted=self.perm_status.microphone,
            on_grant_click=lambda: open_system_preferences("microphone")
        )
        layout.addWidget(self.mic_frame)
        
        # Accessibility permission
        self.access_frame = self._create_permission_card(
            title="⌨️ Accessibility Access",
            description="Required for global hotkeys and typing text at your cursor.",
            instructions="Click 'Grant' → Click '+' → Add Terminal/Python → Toggle ON",
            is_granted=self.perm_status.accessibility,
            on_grant_click=lambda: open_system_preferences("accessibility")
        )
        layout.addWidget(self.access_frame)
        
        layout.addSpacing(5)
        
        # Help text
        help_frame = QFrame()
        help_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        help_layout = QVBoxLayout(help_frame)
        help_layout.setContentsMargins(15, 10, 15, 10)
        
        help_title = QLabel("💡 Can't find TommyTalker in the list?")
        help_title.setFont(QFont("Helvetica Neue", 12, QFont.Weight.Bold))
        help_layout.addWidget(help_title)
        
        help_text = QLabel(
            "When running from Terminal, grant permissions to <b>Terminal.app</b> "
            "(or <b>iTerm.app</b>). When running the bundled .app, grant to <b>TommyTalker.app</b>."
        )
        help_text.setFont(QFont("Helvetica Neue", 11))
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #856404;")
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_frame)
        
        layout.addStretch()
        
        # Continue button (disabled until permissions granted)
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setEnabled(False)
        self.continue_btn.setMinimumHeight(44)
        self.continue_btn.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Medium))
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #0066cc;
                color: white;
                border-radius: 8px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
            QPushButton:hover:!disabled {
                background-color: #0055aa;
            }
        """)
        self.continue_btn.clicked.connect(self._on_continue)
        layout.addWidget(self.continue_btn)
        
    def _create_permission_card(self, title: str, description: str, 
                                 instructions: str, is_granted: bool, 
                                 on_grant_click) -> QFrame:
        """Create a permission status card with detailed instructions."""
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 10px;
                border: 1px solid #dee2e6;
            }
        """)
        
        main_layout = QVBoxLayout(frame)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(8)
        
        # Top row: title + status/button
        top_layout = QHBoxLayout()
        
        title_label = QLabel(title)
        title_label.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        top_layout.addWidget(title_label)
        
        top_layout.addStretch()
        
        # Status/action section
        if is_granted:
            status = QLabel("✅ Granted")
            status.setFont(QFont("Helvetica Neue", 13, QFont.Weight.Medium))
            status.setStyleSheet("color: #28a745;")
            top_layout.addWidget(status)
            frame._status_widget = status
        else:
            grant_btn = QPushButton("Grant")
            grant_btn.setMinimumWidth(80)
            grant_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    border-radius: 5px;
                    padding: 6px 16px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            grant_btn.clicked.connect(on_grant_click)
            top_layout.addWidget(grant_btn)
            frame._status_widget = grant_btn
            
        main_layout.addLayout(top_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setFont(QFont("Helvetica Neue", 12))
        desc_label.setStyleSheet("color: #495057;")
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Instructions (if not granted)
        if not is_granted:
            instr_label = QLabel(f"📋 {instructions}")
            instr_label.setFont(QFont("Helvetica Neue", 11))
            instr_label.setStyleSheet("color: #6c757d; font-style: italic;")
            instr_label.setWordWrap(True)
            main_layout.addWidget(instr_label)
            frame._instr_widget = instr_label
        else:
            frame._instr_widget = None
            
        return frame
        
    def _check_permissions(self):
        """Poll for permission changes."""
        self.perm_status = check_permissions()
        
        # Update UI based on current status
        self._update_permission_card(self.mic_frame, self.perm_status.microphone)
        self._update_permission_card(self.access_frame, self.perm_status.accessibility)
        
        # Enable continue if all permissions granted
        if self.perm_status.all_granted:
            self.continue_btn.setEnabled(True)
            self.check_timer.stop()
            
    def _update_permission_card(self, frame: QFrame, is_granted: bool):
        """Update a permission card's status."""
        if not hasattr(frame, '_status_widget'):
            return
            
        status_widget = frame._status_widget
        
        if is_granted and isinstance(status_widget, QPushButton):
            # Replace button with checkmark
            status_widget.deleteLater()
            status = QLabel("✅ Granted")
            status.setFont(QFont("Helvetica Neue", 13, QFont.Weight.Medium))
            status.setStyleSheet("color: #28a745;")
            
            # Find the top layout and add the status
            top_layout = frame.layout().itemAt(0).layout()
            top_layout.addWidget(status)
            frame._status_widget = status
            
            # Hide instructions if present
            if hasattr(frame, '_instr_widget') and frame._instr_widget:
                frame._instr_widget.hide()
            
    def _on_continue(self):
        """Handle continue button click."""
        self.check_timer.stop()
        self.permissions_granted.emit()
        self.close()
        
    def closeEvent(self, event):
        """Prevent closing if permissions not granted."""
        if not self.perm_status.all_granted:
            event.ignore()
        else:
            self.check_timer.stop()
            event.accept()
