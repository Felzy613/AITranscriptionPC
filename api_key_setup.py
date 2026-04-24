from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QMessageBox, QProgressBar,
)
from PyQt6.QtCore import pyqtSignal, QThread
from PyQt6.QtGui import QFont
from openai import OpenAI, AuthenticationError


class APIKeyVerifier(QThread):
    success = pyqtSignal()
    error   = pyqtSignal(str)

    def __init__(self, api_key: str):
        super().__init__()
        self.api_key = api_key

    def run(self):
        try:
            client = OpenAI(api_key=self.api_key)
            client.models.list()
            self.success.emit()
        except AuthenticationError:
            self.error.emit("Invalid API key. Please check and try again.")
        except Exception as e:
            self.error.emit(f"Error verifying API key: {str(e)}")


class APIKeySetupDialog(QDialog):
    api_key_set = pyqtSignal(str)

    def __init__(self, parent=None, storage_description: str = ""):
        super().__init__(parent)
        self.setWindowTitle("API Key Setup - AI Transcription PC")
        self.setModal(True)
        self.setMinimumWidth(500)
        self._verifier: APIKeyVerifier | None = None
        self._is_verifying = False
        self._storage_description = storage_description
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("API Key Required")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title)

        instructions = QLabel(
            "This app requires an OpenAI API key to transcribe audio.\n\n"
            "1. Get your key at: https://platform.openai.com/api-keys\n"
            "2. Paste it below\n"
            f"3. {self._storage_description or 'Stored locally on your computer.'}\n"
            "4. Never shared with anyone except OpenAI"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        layout.addWidget(QLabel("OpenAI API Key:"))

        self._key_input = QLineEdit()
        self._key_input.setPlaceholderText("sk-proj-...")
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.returnPressed.connect(self._verify_and_save)
        layout.addWidget(self._key_input)

        self._show_btn = QPushButton("Show")
        self._show_btn.setMaximumWidth(80)
        self._show_btn.clicked.connect(self._toggle_show)
        layout.addWidget(self._show_btn)

        self._progress = QProgressBar()
        self._progress.setMaximum(0)
        self._progress.setVisible(False)
        layout.addWidget(self._progress)

        self._status = QLabel("")
        self._status.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._status)

        btn_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._cancel_btn)
        btn_row.addStretch()
        self._verify_btn = QPushButton("Verify & Continue")
        self._verify_btn.setMinimumWidth(150)
        self._verify_btn.clicked.connect(self._verify_and_save)
        btn_row.addWidget(self._verify_btn)
        layout.addLayout(btn_row)

        self.setLayout(layout)

    def _toggle_show(self):
        if self._key_input.echoMode() == QLineEdit.EchoMode.Password:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self._show_btn.setText("Hide")
        else:
            self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self._show_btn.setText("Show")

    def _verify_and_save(self):
        api_key = self._key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Required", "Please enter your API key.")
            return
        if not api_key.startswith("sk-"):
            QMessageBox.warning(
                self, "Invalid Format",
                "API key should start with 'sk-'.\n"
                "Get one at: https://platform.openai.com/api-keys",
            )
            return

        self._set_verifying(True)
        self._verifier = APIKeyVerifier(api_key)
        self._verifier.success.connect(lambda: self._on_success(api_key))
        self._verifier.error.connect(self._on_error)
        self._verifier.start()

    def _set_verifying(self, active: bool) -> None:
        self._is_verifying = active
        self._verify_btn.setEnabled(not active)
        self._cancel_btn.setEnabled(not active)
        self._key_input.setEnabled(not active)
        self._progress.setVisible(active)
        self._status.setText("Verifying API key..." if active else "")

    def _on_success(self, api_key: str) -> None:
        self._is_verifying = False
        self._progress.setVisible(False)
        self._status.setText("API key verified!")
        self.api_key_set.emit(api_key)
        self.accept()

    def _on_error(self, msg: str) -> None:
        self._set_verifying(False)
        QMessageBox.critical(self, "Verification Failed", msg)

    def reject(self):
        if self._is_verifying and self._verifier:
            self._verifier.terminate()
            self._verifier.wait(500)
        super().reject()
