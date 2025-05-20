import os
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsPointCloudLayer, QgsSettings
from PyQt5.QtCore import QFileSystemWatcher, QTimer
from PyQt5.QtWidgets import QMainWindow, QAction, QFileDialog
from PyQt5.QtGui import QIcon
from queue import Queue
from .settings_dialog import SettingsDialog

class FileSystemWatcherPlugin:
    def __init__(self, iface):
        # Basic setup
        self.iface = iface
        self.watcher = QFileSystemWatcher()
        self.watched_folders = set()
        self.settings_action = None
        self.toolbar = None
        self.folder_action = None
        
        # Get plugin directory and settings
        self.plugin_dir = os.path.dirname(__file__)
        self.settings = QgsSettings()
        
        # Initialize default settings if not exist
        if not self.settings.value("watcherfolder/folders"):
            self.settings.setValue("watcherfolder/folders", [])
        if not self.settings.value("watcherfolder/last_folder"):
            self.settings.setValue("watcherfolder/last_folder", "")
            
        # Queue system setup
        self.setup_queue_system()
        
        # Set folders to watch
        self.setup_watch_folders()
        
        # Enable drag and drop
        self.setup_drag_drop()

    def setup_queue_system(self):
        """Setup file processing queue"""
        self.file_queue = Queue()
        self.process_timer = QTimer()
        self.process_timer.timeout.connect(self.process_next_file)
        self.process_timer.setSingleShot(True)  # Timer fires only once
        self.process_timer.setInterval(10000)  # 10 seconds interval
        self.is_processing = False

    def setup_watch_folders(self):
        """Setup main folders to watch"""
        # Get last used folder and watched folders from settings
        self.las_folder = self.settings.value("watcherfolder/last_folder")
        watched_folders = self.settings.value("watcherfolder/folders", [])
        
        # Add last folder if exists
        if self.las_folder and os.path.exists(self.las_folder):
            self.watch_folder(self.las_folder, '.las')
            
        # Add all previously watched folders
        for folder in watched_folders:
            if folder != self.las_folder and os.path.exists(folder):
                self.watch_folder(folder, '.las')

    def watch_folder(self, folder, file_type):
        """Add folder to watch list and scan existing files"""
        self.add_folder_to_watch(folder)
        self.scan_folder_for_files(folder, file_type)

    def scan_folder_for_files(self, folder, file_type):
        """Scan folder for specific file types"""
        for filename in os.listdir(folder):
            if filename.lower().endswith(file_type):
                full_path = os.path.join(folder, filename)
                self.queue_file(full_path, 'las' if file_type == '.las' else 'regular')

    def setup_drag_drop(self):
        # Enable drag and drop for the main QGIS window
        self.iface.mainWindow().setAcceptDrops(True)
        self.iface.mainWindow().__class__.dragEnterEvent = self.dragEnterEvent
        self.iface.mainWindow().__class__.dropEvent = self.dropEvent

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = os.path.normpath(url.toLocalFile())
            if os.path.isdir(path):
                self.add_folder_to_watch(path)
            elif os.path.isfile(path):
                self.add_layer(path)

    def add_folder_to_watch(self, folder_path):
        """Add folder to watch list and connect signals"""
        if folder_path not in self.watched_folders and os.path.exists(folder_path):
            try:
                self.watched_folders.add(folder_path)
                self.watcher.addPath(folder_path)
                
                # Save folder as last used and add to watched folders list
                self.settings.setValue("watcherfolder/last_folder", folder_path)
                watched_folders = self.settings.value("watcherfolder/folders", [])
                if folder_path not in watched_folders:
                    watched_folders.append(folder_path)
                    self.settings.setValue("watcherfolder/folders", watched_folders)
                
                # Connect file system watcher signals
                self.watcher.directoryChanged.connect(self.on_directory_changed)
                
                # Scan existing files
                self.scan_folder_for_files(folder_path, '.txt')
                self.scan_folder_for_files(folder_path, '.las')
                
                self.show_success(f"Now watching folder: {folder_path}")
            except Exception as e:
                self.show_error(f"Failed to watch folder: {str(e)}")

    def on_directory_changed(self, path):
        """Handle directory changes"""
        try:
            # Scan for new LAS files
            for filename in os.listdir(path):
                if filename.lower().endswith('.las'):
                    full_path = os.path.join(path, filename)
                    
                    # Check if file is new or modified
                    if full_path not in [layer.source() for layer in QgsProject.instance().mapLayers().values()]:
                        # Queue new file for processing
                        self.queue_file(full_path, 'las')
                        self.show_message("Info", f"New LAS file detected: {filename}", 0, 3)
        except Exception as e:
            self.show_error(f"Error scanning directory changes: {str(e)}")

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI"""
        # Add settings action
        self.settings_action = QAction(
            # QIcon(os.path.join(self.plugin_dir, 'icons', 'settings.png')),  # Comment this line if no icon
            "Watcher Settings", 
            self.iface.mainWindow()
        )
        self.settings_action.triggered.connect(self.show_settings)
        self.iface.addToolBarIcon(self.settings_action)
        self.iface.addPluginToMenu("Watcher Folder", self.settings_action)

        # Add folder selection action
        self.folder_action = QAction(
            # QIcon(os.path.join(self.plugin_dir, 'icons', 'folder.png')),  # Comment this line if no icon
            "Add Watch Folder",
            self.iface.mainWindow()
        )
        self.folder_action.triggered.connect(self.add_watch_folder_dialog)
        self.iface.addToolBarIcon(self.folder_action)
        self.iface.addPluginToMenu("Watcher Folder", self.folder_action)

    def add_watch_folder_dialog(self):
        """Show dialog to add new watch folder"""
        folder = QFileDialog.getExistingDirectory(
            self.iface.mainWindow(),
            "Select Folder to Watch",
            ""
        )
        if folder:
            self.add_folder_to_watch(folder)

    def show_settings(self):
        """Show the settings dialog"""
        dialog = SettingsDialog(self.iface.mainWindow())
        if dialog.exec_():
            # Reload watched folders with new settings
            self.watcher.removePaths(self.watcher.directories())
            self.watched_folders.clear()
            self.setup_watch_folders()

    def unload(self):
        """Cleanup when plugin is unloaded"""
        # Remove toolbar icons
        if self.settings_action:
            self.iface.removeToolBarIcon(self.settings_action)
            self.iface.removePluginMenu("Watcher Folder", self.settings_action)
            self.settings_action = None
            
        if self.folder_action:
            self.iface.removeToolBarIcon(self.folder_action)
            self.iface.removePluginMenu("Watcher Folder", self.folder_action)
            self.folder_action = None
            
        # Remove all watched paths
        self.watcher.removePaths(self.watcher.files())
        self.watcher.removePaths(self.watcher.directories())
        
        # Restore original drag-drop behavior
        self.iface.mainWindow().__class__.dragEnterEvent = QMainWindow.dragEnterEvent
        self.iface.mainWindow().__class__.dropEvent = QMainWindow.dropEvent
        
        # Stop the process timer
        self.process_timer.stop()

    def add_layer(self, file_path):
        """Add any supported layer type to QGIS"""
        base_name = os.path.basename(file_path)
        
        # Handle different file types
        if file_path.lower().endswith('.las'):
            return self.add_point_cloud_layer(file_path)
        elif file_path.lower().endswith(('.csv', '.txt')):
            return self.add_text_layer(file_path)
        elif file_path.lower().endswith(('.shp', '.geojson', '.gpkg')):
            return self.add_vector_layer(file_path)
        elif file_path.lower().endswith(('.tif', '.jpg', '.png')):
            return self.add_raster_layer(file_path)

    def add_point_cloud_layer(self, file_path, retry_count=0):
        """Add LAS file as point cloud layer with visualization settings"""
        try:
            if not os.path.exists(file_path):
                self.show_error(f"File not found: {file_path}")
                return None

            # Check for duplicate layers
            base_name = os.path.basename(file_path)
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == base_name:
                    self.show_message("Info", f"Layer {base_name} already exists, skipping...", 1, 3)
                    return None
                    
            # Add small delay to ensure file is completely copied
            import time
            time.sleep(1)
            
            layer = QgsPointCloudLayer(file_path, base_name, "pdal")
            
            if layer.isValid():
                # Add layer to project
                QgsProject.instance().addMapLayer(layer)
                
                # Use basic renderer settings
                renderer = layer.renderer()
                if renderer:
                    renderer.setPointSize(2)
                    renderer.setMaximumScreenError(0.5)
                
                # Force refresh
                layer.triggerRepaint()
                self.iface.mapCanvas().refresh()
                
                self.show_success(f"Added point cloud layer: {base_name}")
                return layer
            else:
                # Handle invalid layer with retries
                if retry_count < 3:
                    self.show_message("Info", f"Retrying to load {base_name} (Attempt {retry_count + 1}/3)", 1, 2)
                    time.sleep(3)
                    return self.add_point_cloud_layer(file_path, retry_count + 1)
                else:
                    self.requeue_failed_layer(file_path)
                    return None
                    
        except Exception as e:
            return self.handle_layer_error(file_path, e, retry_count)

    def add_text_layer(self, file_path):
        """Add text/CSV file as vector layer"""
        try:
            base_name = os.path.basename(file_path)
            
            # Check for duplicate layers
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name() == base_name:
                    self.show_message("Info", f"Layer {base_name} already exists, skipping...", 1, 3)
                    return None
            
            # Create vector layer from text file
            uri = f"file:///{file_path}?delimiter=,&useHeader=yes&detectTypes=yes"
            layer = QgsVectorLayer(uri, base_name, "delimitedtext")
            
            if layer.isValid():
                # Add layer to project
                QgsProject.instance().addMapLayer(layer)
                self.show_success(f"Added text layer: {base_name}")
                return layer
            else:
                self.show_error(f"Failed to load text file: {base_name}")
                return None
                
        except Exception as e:
            self.show_error(f"Error loading text file {os.path.basename(file_path)}: {str(e)}")
            return None

    def finalize_layer_addition(self, layer):
        """Finalize adding layer to QGIS"""
        QgsProject.instance().addMapLayer(layer)
        self.iface.mapCanvas().refresh()
        return layer

    def retry_layer_load(self, file_path, retry_count):
        """Retry loading layer with delay"""
        import time
        time.sleep(3)  # Wait 3 seconds before retry
        return self.add_point_cloud_layer(file_path, retry_count + 1)

    def requeue_failed_layer(self, file_path):
        """Requeue failed layer for later processing"""
        self.show_error(f"Failed to load {os.path.basename(file_path)} after 3 attempts")
        self.queue_file(file_path, 'las')

    def handle_layer_error(self, file_path, error, retry_count):
        """Handle errors during layer loading"""
        if retry_count < 3:
            return self.retry_layer_load(file_path, retry_count)
        else:
            self.show_error(f"Error loading {os.path.basename(file_path)}: {str(error)}")
            self.requeue_failed_layer(file_path)
            return None

    def process_next_file(self):
        """Process one file from queue"""
        if self.is_processing:
            return
        
        if self.file_queue.empty():
            self.show_success("All files processed successfully!")
            return

        self.is_processing = True
        
        try:
            # Get next file
            file_path, file_type = self.file_queue.get()
            
            # Add layer
            layer = self.add_layer(file_path)
            
            # Update display if successful
            if layer and layer.isValid():
                self.update_display(layer, file_path)
                
            # Start timer for next file
            if not self.file_queue.empty():
                self.show_message("Info", 
                                f"Waiting 50 seconds before processing next file. {self.file_queue.qsize()} files remaining.", 
                                0, 3)
                self.process_timer.start()
                
        except Exception as e:
            self.show_error(f"Failed to process {os.path.basename(file_path)}: {str(e)}")
        finally:
            self.is_processing = False

    def update_display(self, layer, file_path):
        """Update display after adding layer"""
        layer.triggerRepaint()
        self.iface.mapCanvas().refresh()
        self.show_success(f"Added layer: {os.path.basename(file_path)}")

    def queue_file(self, file_path, file_type):
        """Add file to processing queue and start processing if not already running"""
        self.file_queue.put((file_path, file_type))
        if not self.is_processing and not self.process_timer.isActive():
            self.process_next_file()

    def show_message(self, title, message, level, duration):
        """Show message in QGIS message bar"""
        self.iface.messageBar().pushMessage(title, message, level, duration)

    def show_success(self, message):
        """Show success message"""
        self.show_message("Success", message, 0, 3)

    def show_error(self, message):
        """Show error message"""
        self.show_message("Error", message, 2, 5)


def classFactory(iface):
    """Load the plugin class."""
    return FileSystemWatcherPlugin(iface)