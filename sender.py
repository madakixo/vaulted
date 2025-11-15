# sender.py
"""
Secure Vault Sender GUI using PyQt6.
Creates an encrypted ZIP vault from selected files using Fernet encryption.
Updated for 2025: Improved error handling, concise layout, and thread safety.
"""

import os
import zipfile
import sys
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QProgressBar, QMessageBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont

def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 32-byte key from password using PBKDF2."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

class EncryptThread(QThread):
    """Thread for encrypting files to avoid GUI freezing."""
    finished = pyqtSignal(str)  # Success message
    error = pyqtSignal(str)     # Error message

    def __init__(self, files, password, output):
        super().__init__()
        self.files = files
        self.password = password
        self.output = output

    def run(self):
        try:
            # Generate salt
            salt = os.urandom(16)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write salt
                with open(os.path.join(temp_dir, 'salt.bin'), 'wb') as f:
                    f.write(salt)
                
                key = derive_key(self.password, salt)
                fernet = Fernet(key)
                
                # Encrypt files
                with zipfile.ZipFile(self.output, 'w', zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr('salt.bin', salt)
                    for file_path in self.files:
                        if os.path.exists(file_path.strip()):
                            with open(file_path.strip(), 'rb') as f:
                                data = f.read()
                            encrypted_data = fernet.encrypt(data)
                            enc_name = os.path.basename(file_path.strip()) + '.enc'
                            zf.writestr(enc_name, encrypted_data)
            
            self.finished.emit(f"Vault created: {self.output}\nSend this ZIP securely.")
        except Exception as e:
            self.error.emit(str(e))

class SenderGUI(QMainWindow):
    """Main GUI for sender: Select files, password, create vault."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Vault Sender")
        self.setGeometry(100, 100, 500, 300)  # Concise size
        self.setStyleSheet("QMainWindow { background-color: #f0f0f0; }")  # Polished look
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)  # Concise spacing
        
        # Title
        title = QLabel("Create Secure Vault")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Files selection
        files_layout = QHBoxLayout()
        self.files_edit = QLineEdit()
        self.files_edit.setPlaceholderText("Selected files will appear here")
        self.files_edit.setReadOnly(True)
        browse_btn = QPushButton("Browse Files")
        browse_btn.clicked.connect(self.browse_files)
        files_layout.addWidget(QLabel("Files:"))
        files_layout.addWidget(self.files_edit)
        files_layout.addWidget(browse_btn)
        layout.addLayout(files_layout)
        
        # Password
        pass_layout = QHBoxLayout()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Enter password")
        self.confirm_edit = QLineEdit()  # Fixed: self.confirm_edit
        self.confirm_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_edit.setPlaceholderText("Confirm password")
        pass_layout.addWidget(QLabel("Password:"))
        pass_layout.addWidget(self.pass_edit)
        pass_layout.addWidget(self.confirm_edit)
        layout.addLayout(pass_layout)
        
        # Output
        output_layout = QHBoxLayout()
        self.output_edit = QLineEdit("secure_vault.zip")
        output_btn = QPushButton("Browse Output")
        output_btn.clicked.connect(self.browse_output)
        output_layout.addWidget(QLabel("Output ZIP:"))
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_btn)
        layout.addLayout(output_layout)
        
        # Encrypt button
        self.encrypt_btn = QPushButton("Create Vault")
        self.encrypt_btn.clicked.connect(self.encrypt_vault)
        layout.addWidget(self.encrypt_btn)
        
        # Progress bar
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        layout.addStretch()  # Push up for concise feel
    
    def browse_files(self):
        """Browse and select multiple files."""
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Files (*.*)")
        if files:
            self.files_edit.setText("; ".join(files))
    
    def browse_output(self):
        """Browse for output ZIP location."""
        filename, _ = QFileDialog.getSaveFileName(self, "Save Vault As", "secure_vault.zip", "ZIP Files (*.zip)")
        if filename:
            self.output_edit.setText(filename)
    
    def encrypt_vault(self):
        """Start encryption in thread."""
        files = self.files_edit.text().split(";")
        password = self.pass_edit.text()
        confirm = self.confirm_edit.text()  # Fixed: Use self.confirm_edit
        if not files or not files[0]:
            QMessageBox.warning(self, "Error", "Select files.")
            return
        if password != confirm:
            QMessageBox.warning(self, "Error", "Passwords do not match.")
            return
        if not password:
            QMessageBox.warning(self, "Error", "Enter password.")
            return
        output = self.output_edit.text()
        
        self.encrypt_btn.setEnabled(False)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)  # Indeterminate
        
        self.thread = EncryptThread(files, password, output)
        self.thread.finished.connect(self.on_finished)
        self.thread.error.connect(self.on_error)
        self.thread.start()
    
    def on_finished(self, msg):
        """Handle success."""
        self.progress.setVisible(False)
        self.encrypt_btn.setEnabled(True)
        QMessageBox.information(self, "Success", msg)
    
    def on_error(self, err):
        """Handle error."""
        self.progress.setVisible(False)
        self.encrypt_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Encryption failed: {err}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SenderGUI()
    window.show()
    sys.exit(app.exec())
