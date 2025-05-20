from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox
from PyQt5.QtCore import Qt
from qgis.core import QgsSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setWindowTitle("Watcher Settings")
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # LAS folder input
        folder_layout = QHBoxLayout()
        self.las_path = QLineEdit()
        folder_layout.addWidget(QLabel("Default LAS Folder:"))
        folder_layout.addWidget(self.las_path)
        
        # Browse button
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_folder)
        folder_layout.addWidget(browse_button)
        
        layout.addLayout(folder_layout)
        
        # OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)

    def browse_folder(self):
        from PyQt5.QtWidgets import QFileDialog
        folder = QFileDialog.getExistingDirectory(self, "Select LAS Folder")
        if folder:
            self.las_path.setText(folder)

    def load_settings(self):
        settings = QgsSettings()
        las_path = settings.value("watcherfolder/las_folder", "")
        self.las_path.setText(las_path)

    def accept(self):
        settings = QgsSettings()
        settings.setValue("watcherfolder/las_folder", self.las_path.text())
        super().accept()
