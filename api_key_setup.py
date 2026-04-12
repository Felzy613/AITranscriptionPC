"""
API Key Setup Dialog - appears on first launch
Forces user to enter and verify their OpenAI API key before app can run
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon
from openai import OpenAI, AuthenticationError


class APIKeyVerifier(QThread):
    """Verify API key is valid by making a test API call"""
    success = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key
    
    def run(self):
        try:
            # Test the API key with a minimal request
            client = OpenAI(api_key=self.api_key)
            # Just check if the key is valid - don't actually transcribe
            client.models.list()
            self.success.emit()
        except AuthenticationError:
            self.error.emit("Invalid API key. Please check and try again.")
        except Exception as e:
            self.error.emit(f"Error verifying API key: {str(e)}")


class APIKeySetupDialog(QDialog):
    """Modal dialog for entering and verifying OpenAI API key"""
    
    api_key_set = pyqtSignal(str)  # Emitted when key is successfully set
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Key Setup - AI Transcription PC")
        self.setModal(True)
        self.setMinimumWidth(500)
        self.verifier = None
        
        # Don't allow closing without entering key
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowCloseButtonHint)
        
        self.init_ui()
    
    def init_ui(self):
        """Create the UI"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("API Key Required")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "This app requires an OpenAI API key to transcribe audio.\n\n"
            "1. Get your free API key at: https://platform.openai.com/api-keys\n"
            "2. Paste it below\n"
            "3. The key is encrypted and stored locally on your computer\n"
            "4. Never shared with anyone except OpenAI"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # API Key input
        key_label = QLabel("OpenAI API Key:")
        layout.addWidget(key_label)
        
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("sk-proj-...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.returnPressed.connect(self.verify_and_save)
        layout.addWidget(self.key_input)
        
        # Show/hide password toggle
        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setMaximumWidth(80)
        self.show_key_btn.clicked.connect(self.toggle_show_key)
        layout.addWidget(self.show_key_btn)
        
        # Progress bar (hidden)
        self.progress = QProgressBar()
        self.progress.setMaximum(0)  # Indeterminate
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.verify_btn = QPushButton("Verify & Continue")
        self.verify_btn.setMinimumWidth(150)
        self.verify_btn.clicked.connect(self.verify_and_save)
        button_layout.addWidget(self.verify_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def toggle_show_key(self):
        """Toggle showing/hiding the API key"""
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Hide")
        else:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Show")
    
    def verify_and_save(self):
        """Verify API key and save it"""
        api_key = self.key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Required", "Please enter your API key")
            return
        
        if not api_key.startswith("sk-"):
            QMessageBox.warning(
                self, 
                "Invalid Format", 
                "API key should start with 'sk-'\n"
                "Get one at: https://platform.openai.com/api-keys"
            )
            return
        
        # Verify the key is valid
        self.verify_btn.setEnabled(False)
        self.key_input.setEnabled(False)
        self.progress.setVisible(True)
        self.status_label.setText("Verifying API key...")
        
        self.verifier = APIKeyVerifier(api_key)
        self.verifier.success.connect(lambda: self._on_verify_success(api_key))
        self.verifier.error.connect(self._on_verify_error)
        self.verifier.start()
    
    def _on_verify_success(self, api_key: str):
        """Called when API key is verified"""
        self.progress.setVisible(False)
        self.status_label.setText("✓ API key verified!")
        self.api_key_set.emit(api_key)
        self.accept()
    
    def _on_verify_error(self, error_msg: str):
        """Called when API key verification fails"""
        self.verify_btn.setEnabled(True)
        self.key_input.setEnabled(True)
        self.progress.setVisible(False)
        self.status_label.setText("")
        QMessageBox.critical(self, "Verification Failed", error_msg)
    
    def closeEvent(self, event):
        """Prevent closing without entering key"""
        event.ignore()
