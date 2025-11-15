# receiver.py
"""
Secure Vault Receiver GUI using PyQt6.
Decrypts ZIP vault temporarily, shows files with thumbnails (images & PDFs), opens on click, auto-deletes on close.
Requires pdf2image for PDF thumbnails (install poppler-utils separately).
Updated for 2025: Enhanced drag-drop, better thumbnail fallbacks, concise status updates.
"""

import os
import zipfile
import sys
import tempfile
import shutil
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QLabel, QLineEdit, QPushButton, QFileDialog, 
                             QProgressBar, QMessageBox, QTreeWidget, QTreeWidgetItem)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QMimeData, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon
from PIL import Image
from pdf2image import convert_from_path
import webbrowser

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

class UnlockThread(QThread):
    """Thread for decrypting vault."""
    populated = pyqtSignal(dict)  # Dict of name: path, with 'temp_dir'
    error = pyqtSignal(str)

    def __init__(self, vault, password):
        super().__init__()
        self.vault = vault
        self.password = password

    def run(self):
        try:
            temp_dir = tempfile.mkdtemp()
            key = None
            decrypted_files = {}
            with zipfile.ZipFile(self.vault, 'r') as zf:
                salt = zf.read('salt.bin')
                key = derive_key(self.password, salt)
                fernet = Fernet(key)
                
                for info in zf.infolist():
                    if info.filename.endswith('.enc'):
                        encrypted_data = zf.read(info)
                        decrypted_data = fernet.decrypt(encrypted_data)
                        original_name = info.filename.replace('.enc', '')
                        output_path = os.path.join(temp_dir, original_name)
                        with open(output_path, 'wb') as f:
                            f.write(decrypted_data)
                        decrypted_files[original_name] = output_path
            
            self.populated.emit({**decrypted_files, 'temp_dir': temp_dir})
        except Exception as e:
            self.error.emit(str(e))

class DropZone(QWidget):
    """Drop zone for ZIP file with drag-drop support."""
    file_dropped = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setStyleSheet("border: 2px dashed #aaa; background: #f9f9f9; padding: 20px;")
        self.setMinimumHeight(50)
        layout = QVBoxLayout(self)
        self.label = QLabel("Drop ZIP vault here or click Browse")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files and files[0].endswith('.zip'):
            self.file_dropped.emit(files[0])
            self.label.setText(f"Dropped: {os.path.basename(files[0])}")
        else:
            QMessageBox.warning(self, "Error", "Drop a ZIP file.")

class ReceiverGUI(QMainWindow):
    """Main GUI for receiver: Unlock, list files with thumbs, view, auto-cleanup."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Secure Vault Viewer")
        self.setGeometry(100, 100, 800, 600)  # Concise size
        self.setStyleSheet("QMainWindow { background-color: #f0f0f0; }")
        
        self.temp_dir = None
        self.decrypted_files = {}
        self.vault_path = None  # Fixed: Track vault path
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("View Secure Vault")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Drop zone / Vault selection
        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self.set_vault)
        self.browse_btn = QPushButton("Browse ZIP")  # Fixed: self.browse_btn
        self.browse_btn.clicked.connect(self.browse_vault)
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.drop_zone)
        h_layout.addWidget(self.browse_btn)
        layout.addLayout(h_layout)
        
        # Password
        pass_layout = QHBoxLayout()
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Enter password")
        self.unlock_btn = QPushButton("Unlock")  # Fixed: self.unlock_btn
        self.unlock_btn.clicked.connect(self.unlock_vault)
        pass_layout.addWidget(QLabel("Password:"))
        pass_layout.addWidget(self.pass_edit)
        pass_layout.addWidget(self.unlock_btn)
        layout.addLayout(pass_layout)
        
        # Files list with thumbnails (using QTreeWidget for icon column)
        self.files_tree = QTreeWidget()
        self.files_tree.setHeaderLabels(["Thumbnail", "Name", "Type"])
        self.files_tree.setColumnWidth(0, 80)  # Thumb size
        self.files_tree.itemClicked.connect(self.open_file)
        layout.addWidget(self.files_tree)
        
        # Status
        self.status_label = QLabel("Ready to unlock vault.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Progress
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        layout.addStretch()
    
    def set_vault(self, path):
        """Set vault path from drop."""
        self.vault_path = path
        self.drop_zone.label.setText(f"Vault: {os.path.basename(path)}")
    
    def browse_vault(self):
        """Browse for ZIP."""
        filename, _ = QFileDialog.getOpenFileName(self, "Select Vault", "", "ZIP Files (*.zip)")
        if filename:
            self.set_vault(filename)
    
    def unlock_vault(self):
        """Start decryption."""
        if not self.vault_path or not os.path.exists(self.vault_path):
            QMessageBox.warning(self, "Error", "Select a valid ZIP vault.")
            return
        password = self.pass_edit.text()
        if not password:
            QMessageBox.warning(self, "Error", "Enter password.")
            return
        
        self.unlock_btn.setEnabled(False)  # Fixed: Use self.unlock_btn
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self.thread = UnlockThread(self.vault_path, password)
        self.thread.populated.connect(self.populate_files)
        self.thread.error.connect(self.on_error)
        self.thread.start()
    
    def populate_files(self, files_dict):
        """Populate tree with files and generate thumbnails."""
        self.decrypted_files = {k: v for k, v in files_dict.items() if k != 'temp_dir'}
        self.temp_dir = files_dict['temp_dir']
        
        self.files_tree.clear()
        for name, path in self.decrypted_files.items():
            ext = os.path.splitext(name)[1].lower()
            item = QTreeWidgetItem(["", name, ext.upper() if ext else "File"])  # Fixed: Empty text for thumb column
            pixmap = None
            
            try:
                if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp']:
                    # Image thumbnail
                    img = Image.open(path)
                    img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                    pixmap = QPixmap.fromImage(img.toqimage())  # Fixed: toqimage() -> fromImage
                elif ext == '.pdf':
                    # PDF thumbnail (first page)
                    images = convert_from_path(path, first_page=1, last_page=1, dpi=100)
                    if images:
                        img = images[0]
                        img.thumbnail((64, 64), Image.Resampling.LANCZOS)
                        pixmap = QPixmap.fromImage(img.toqimage())
                
                if pixmap:
                    icon = QIcon(pixmap.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
                    item.setIcon(0, icon)
                else:
                    # Placeholder icon
                    item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                
                self.files_tree.addTopLevelItem(item)
            except Exception as e:
                # Fallback icon on error
                item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                print(f"Thumbnail error for {name}: {e}")
        
        self.progress.setVisible(False)
        self.unlock_btn.setEnabled(True)
        self.status_label.setText("Vault unlocked. Click files to view. Close to delete.")
    
    def open_file(self, item):
        """Open selected file with default viewer."""
        name = item.text(1)  # Fixed: text(1) for Name column
        path = self.decrypted_files.get(name)
        if path:
            try:
                if os.name == 'nt':
                    os.startfile(path)
                else:
                    webbrowser.open(f'file://{path}')
            except Exception as e:
                QMessageBox.warning(self, "Open Error", f"Failed to open {name}: {e}")
    
    def on_error(self, err):
        """Handle decryption error."""
        self.progress.setVisible(False)
        self.unlock_btn.setEnabled(True)
        QMessageBox.critical(self, "Error", f"Decryption failed: {err}")
    
    def closeEvent(self, event):
        """Cleanup on close."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        if self.vault_path and os.path.exists(self.vault_path):
            try:
                os.remove(self.vault_path)
            except Exception:
                pass  # Ignore delete errors
        self.status_label.setText("All traces deleted.")  # Fixed: Set after cleanup
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ReceiverGUI()
    window.show()
    sys.exit(app.exec())
