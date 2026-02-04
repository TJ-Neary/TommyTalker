"""
TommyTalker Hotkey Selector Widget
3-dropdown cascade for selecting valid hotkey combinations.
"""

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QComboBox, QLabel
)
from PyQt6.QtCore import pyqtSignal, Qt


# Valid modifiers (first dropdown)
FIRST_MODIFIERS = ["Ctrl", "Cmd", "Option"]

# Letters that are SAFE to use (excludes Z, C, V, X, Q, W, A, S which conflict with system shortcuts)
SAFE_LETTERS = ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "R", "T", "U", "Y"]

# Punctuation keys that can be used
PUNCTUATION_KEYS = [",", ".", "/"]

# Second key options (second dropdown) 
SECOND_OPTIONS = ["Shift", "Option", "Ctrl", "Cmd"] + SAFE_LETTERS + \
                 [str(i) for i in range(10)] + ["Space"] + PUNCTUATION_KEYS

# Third key options (third dropdown) - includes "Not Used" for 2-key combos
THIRD_OPTIONS = ["Not Used"] + SAFE_LETTERS + \
                [str(i) for i in range(10)] + ["Space"] + PUNCTUATION_KEYS


class HotkeySelector(QWidget):
    """
    3-dropdown cascade hotkey selector.
    
    Format: Modifier1 + Modifier2/Key + Key (optional)
    Examples: Cmd+Shift+Space, Ctrl+Option+R, Cmd+.
    """
    
    # Emitted when hotkey changes
    hotkey_changed = pyqtSignal(str)
    
    def __init__(self, current_hotkey: str = "", parent=None):
        super().__init__(parent)
        self.setMinimumHeight(30)  # Ensure visible height
        self._setup_ui()
        self._load_hotkey(current_hotkey)
        
    def _setup_ui(self):
        """Setup the 3-dropdown UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        
        # First dropdown (primary modifier)
        self.combo1 = QComboBox()
        self.combo1.addItems(FIRST_MODIFIERS)
        self.combo1.setFixedWidth(70)
        self.combo1.setMinimumHeight(25)
        self.combo1.currentTextChanged.connect(self._on_combo1_changed)
        layout.addWidget(self.combo1)
        
        # Plus label
        plus1 = QLabel("+")
        plus1.setFixedWidth(12)
        plus1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plus1)
        
        # Second dropdown (second modifier or key) - pre-populate with options
        self.combo2 = QComboBox()
        self.combo2.addItems(SECOND_OPTIONS)
        self.combo2.setFixedWidth(70)
        self.combo2.setMinimumHeight(25)
        self.combo2.currentTextChanged.connect(self._on_combo2_changed)
        layout.addWidget(self.combo2)
        
        # Plus label
        self.plus2 = QLabel("+")
        self.plus2.setFixedWidth(12)
        self.plus2.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.plus2)
        
        # Third dropdown (final key, optional) - pre-populate
        self.combo3 = QComboBox()
        self.combo3.addItems(THIRD_OPTIONS)
        self.combo3.setFixedWidth(70)
        self.combo3.setMinimumHeight(25)
        self.combo3.currentTextChanged.connect(self._on_combo3_changed)
        layout.addWidget(self.combo3)
        
        layout.addStretch()
        
    def _on_combo1_changed(self, text: str):
        """Handle first dropdown change."""
        if not text:
            return
            
        # Update second dropdown options
        self._update_combo2_options(text)
        self.combo2.setEnabled(True)
        
        # Reset third dropdown
        self.combo3.clear()
        self.combo3.setEnabled(False)
        self.plus2.setVisible(True)
        
        self._emit_hotkey()
        
    def _update_combo2_options(self, first_choice: str):
        """Update second dropdown based on first choice."""
        self.combo2.blockSignals(True)
        self.combo2.clear()
        
        # Available options exclude the first choice
        options = [opt for opt in SECOND_OPTIONS if opt != first_choice]
        self.combo2.addItems(options)
        
        self.combo2.blockSignals(False)
        
    def _on_combo2_changed(self, text: str):
        """Handle second dropdown change."""
        if not text:
            return
            
        first = self.combo1.currentText()
        
        # Update third dropdown options
        self._update_combo3_options(first, text)
        self.combo3.setEnabled(True)
        
        self._emit_hotkey()
        
    def _update_combo3_options(self, first: str, second: str):
        """Update third dropdown based on previous choices."""
        self.combo3.blockSignals(True)
        self.combo3.clear()
        
        # If second choice is a letter/number, "Not Used" is default
        is_second_key = len(second) == 1 or second == "Space"
        
        if is_second_key:
            # Second is already a key, third is optional
            self.combo3.addItem("Not Used")
            self.plus2.setVisible(False)
        else:
            # Second is a modifier, third is required (no "Not Used")
            options = [opt for opt in THIRD_OPTIONS if opt != "Not Used" and opt != first and opt != second]
            self.combo3.addItems(options)
            self.plus2.setVisible(True)
            
        self.combo3.blockSignals(False)
        
    def _on_combo3_changed(self, text: str):
        """Handle third dropdown change."""
        self._emit_hotkey()
        
    def _emit_hotkey(self):
        """Build and emit the current hotkey string."""
        hotkey = self.get_hotkey()
        if hotkey:
            self.hotkey_changed.emit(hotkey)
            
    def get_hotkey(self) -> str:
        """Get the current hotkey string."""
        parts = [self.combo1.currentText()]
        
        second = self.combo2.currentText()
        if second:
            parts.append(second)
            
        third = self.combo3.currentText()
        if third and third != "Not Used":
            parts.append(third)
            
        if len(parts) < 2:
            return ""
            
        return "+".join(parts)
        
    def _load_hotkey(self, hotkey: str):
        """Load and display an existing hotkey."""
        if not hotkey:
            return
            
        parts = hotkey.split("+")
        if len(parts) < 2:
            return
            
        # Set first dropdown
        first = parts[0].strip()
        idx = self.combo1.findText(first)
        if idx >= 0:
            self.combo1.setCurrentIndex(idx)
            
        # Set second dropdown
        if len(parts) >= 2:
            second = parts[1].strip()
            self._update_combo2_options(first)
            self.combo2.setEnabled(True)
            idx = self.combo2.findText(second)
            if idx >= 0:
                self.combo2.setCurrentIndex(idx)
                
        # Set third dropdown
        if len(parts) >= 3:
            third = parts[2].strip()
            self._update_combo3_options(first, second)
            self.combo3.setEnabled(True)
            idx = self.combo3.findText(third)
            if idx >= 0:
                self.combo3.setCurrentIndex(idx)
        elif len(parts) == 2:
            # Two-part hotkey, set "Not Used" for third
            self._update_combo3_options(first, second)
            self.combo3.setEnabled(True)
            
    def set_hotkey(self, hotkey: str):
        """Set the hotkey externally."""
        self._load_hotkey(hotkey)
