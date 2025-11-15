Secure Vault App (PyQt Edition - 2025 Update)Advanced secure file sharing app with PyQt6 GUI. Sender encrypts files into a self-destructing ZIP vault. Receiver decrypts temporarily, displays thumbnails (images & PDFs), supports drag-and-drop, and auto-deletes traces.FeaturesEncryption: Fernet symmetric with PBKDF2 key derivation (100k iterations for strength).
Advanced GUI: PyQt6 for polished, concise interface; threaded operations prevent freezing.
Thumbnails: Auto-generated for images (Pillow) and PDFs (pdf2image, first-page preview).
Self-Destruct: Temporary files and original ZIP auto-deleted on receiver close.
Media/PDF Support: Click files to open in default apps (e.g., media players, PDF readers).
Drag-and-Drop: Full support for dropping ZIP into receiver; multi-file select in sender.
Updates (2025): Enhanced error handling, smoother thumbnails, better cross-platform open commands.

InstallationEnsure Python 3.9+ installed.
pip install -r requirements.txt
For PDF thumbnails: Install poppler-utils system-wide (see note in requirements.txt).
Launch: python sender.py or python receiver.py.

How to Use sender.py with Media or PDFRun python sender.py – Compact window launches.
Browse Files: Click "Browse Files" for multi-select; supports images (.jpg/.png), media (.mp4/.avi), PDFs (.pdf).Files treated as binaries; ZIP compression applied during encryption.

Enter/confirm a strong password (mismatch warning shown).
Set output ZIP path (default: secure_vault.zip; browse optional).
Click Create Vault – Indeterminate progress bar; threaded for responsiveness.
On success: Message confirms; share ZIP via secure channel (e.g., encrypted email, USB).Recipient unlocks with same password.

Tips for Media/PDF:Large files: Encryption time scales with size; use fast storage.
Security: Unique, long passwords; avoid reusing vaults.
Thumbnails: Generated only on receiver; PDFs require poppler.

Step-by-Step: How to Use the AppAs Sender (Encrypt & Share):Execute python sender.py.
Select files via "Browse Files" (multi-select: Ctrl+click for media/PDFs/images).
Fill password fields – auto-validation on create.
Customize output ZIP if needed.
Hit "Create Vault" – Wait for "Success" dialog.
Distribute the generated ZIP securely.

As Receiver (Decrypt & View):Run python receiver.py.
Drag ZIP to the dashed drop zone (or click "Browse ZIP").
Enter password; click "Unlock" – Progress indicates decryption.
Files populate in tree view:Thumbnails: Images/PDFs show previews; others use file icons.
Columns: Thumbnail | Name | Type (e.g., PDF).

Click any file: Opens in system default (e.g., VLC for video, browser for PDF).
View content securely – all in temp dir.
Close app: Triggers cleanup; status confirms "All traces deleted."

Error Handling:Wrong password: "Decryption failed" – No files exposed.
Open failures: Warning dialog; file remains viewable manually.
Cleanup ignores errors (e.g., read-only files).

Security NotesOne-Time Use: Vault deletes post-view; recreate for reuse.
Key Strength: PBKDF2-SHA256 with random salt per vault.
No Persistence: Temps use tempfile.mkdtemp(); shredded on exit.
Platform: Tested Windows/Linux/macOS; adjust open_file for custom viewers if needed.

Extending the AppSender Drag-Drop: Add DropZone to files_edit for file drops.
Custom Thumbs: Tweak DPI in populate_files; add video frame extraction (e.g., via ffmpeg).
CLI Mode: Wrap GUIs in if __name__ == "__main__": args for headless use.

TroubleshootingDecryption Failed: Verify password/ZIP integrity; re-encrypt if corrupted.
No PDF Thumbs: Ensure poppler-utils installed; fallback to icon.
Import Errors: Check pip installs; PyQt6 requires Qt binaries.
Cross-Platform Opens: macOS may need subprocess.call(['open', path]) tweak.

