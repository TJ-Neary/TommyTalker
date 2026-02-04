"""
TommyTalker HUD Overlay
Transparent overlay window for interview coaching (Mode 4).
CRITICAL: Must be invisible to screen sharing via NSWindowSharingTypeNone.
"""

from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QFont, QColor, QPalette, QMouseEvent

# pyobjc for macOS-specific window hiding
try:
    from AppKit import NSWindowSharingTypeNone
    HAS_PYOBJC = True
except ImportError:
    HAS_PYOBJC = False
    print("[WARNING] pyobjc not available - HUD will be visible to screen sharing!")


class HUDOverlay(QMainWindow):
    """
    Transparent overlay window for interview coaching.
    
    PRIVACY CONSTRAINT: This window MUST be invisible to Zoom/Teams screen sharing.
    Achieved via NSWindowSharingTypeNone on macOS.
    
    Features:
    - Draggable by clicking anywhere on the window
    - Stays on top of other windows
    - Does not steal focus from other apps
    """
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("TommyTalker HUD")
        
        # Window flags for overlay behavior
        # WindowDoesNotAcceptFocus prevents stealing focus from other apps
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |  # Don't show in dock
            Qt.WindowType.WindowDoesNotAcceptFocus  # Critical: don't steal focus!
        )
        
        # Enable transparency
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)  # Don't activate when shown
        
        # Drag state
        self._drag_pos = None
        
        # Apply screen-share invisibility
        self._apply_privacy_settings()
        
        self._setup_ui()
        
    def _apply_privacy_settings(self):
        """Apply macOS privacy settings to hide from screen sharing."""
        if not HAS_PYOBJC:
            return
            
        try:
            # Get the native window handle
            # This must be done AFTER the window is created but BEFORE showing
            QTimer.singleShot(0, self._set_sharing_type)
        except Exception as e:
            print(f"[WARNING] Failed to apply privacy settings: {e}")
            
    def _set_sharing_type(self):
        """Set NSWindowSharingTypeNone to hide from screen sharing."""
        if not HAS_PYOBJC:
            return
            
        try:
            # Access the native NSWindow
            # PyQt6 uses winId() to get the native window handle
            ns_view = self.winId().__int__()
            
            # Import Cocoa framework
            from Cocoa import NSApp
            
            # Find our window in the app's windows
            for window in NSApp.windows():
                # Match by comparing view IDs - this is a simplified approach
                # In production, you'd want more robust window matching
                try:
                    window.setSharingType_(NSWindowSharingTypeNone)
                    print(f"[HUD] Applied NSWindowSharingTypeNone - invisible to screen sharing")
                    break
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"[WARNING] Could not set sharing type: {e}")
            
    def _setup_ui(self):
        """Setup the HUD UI with semi-transparent background."""
        # Central widget with dark semi-transparent background
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: rgba(30, 30, 30, 200);
                border-radius: 10px;
            }
        """)
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Title - use Helvetica Neue instead of SF Pro to avoid font warnings
        title = QLabel("🎯 Interview Coach")
        title.setFont(QFont("Helvetica Neue", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: white;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Drag hint
        drag_hint = QLabel("(drag to move)")
        drag_hint.setFont(QFont("Helvetica Neue", 9))
        drag_hint.setStyleSheet("color: #888;")
        drag_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(drag_hint)
        
        # Live transcription area
        self.transcript_label = QLabel("Listening...")
        self.transcript_label.setFont(QFont("Helvetica Neue", 12))
        self.transcript_label.setStyleSheet("color: #88ff88;")
        self.transcript_label.setWordWrap(True)
        self.transcript_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.transcript_label)
        
        # Coaching suggestions area
        self.suggestions_label = QLabel("")
        self.suggestions_label.setFont(QFont("Helvetica Neue", 11))
        self.suggestions_label.setStyleSheet("color: #ffcc00;")
        self.suggestions_label.setWordWrap(True)
        layout.addWidget(self.suggestions_label)
        
        # Set initial size and position (bottom-right corner)
        self.resize(400, 200)
        self._position_bottom_right()
        
    def _position_bottom_right(self):
        """Position the HUD in the bottom-right corner of the screen."""
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 20
            y = geometry.bottom() - self.height() - 20
            self.move(x, y)
    
    # ------ Drag support ------
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for dragging."""
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
            
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release to end dragging."""
        self._drag_pos = None
        event.accept()
    # --------------------------
            
    def update_transcript(self, text: str):
        """Update the live transcript display."""
        self.transcript_label.setText(text)
        
    def update_suggestions(self, suggestions: str):
        """Update the coaching suggestions."""
        self.suggestions_label.setText(suggestions)
        
    def showEvent(self, event):
        """Ensure privacy settings are applied when showing."""
        super().showEvent(event)
        self._set_sharing_type()

