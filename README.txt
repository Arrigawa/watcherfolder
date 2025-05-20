Plugin Builder Results

Cara mengaktifkan plugin ini di QGIS (simpan sebagai file .py di folder plugin Anda):
1. Buka QGIS.
2. Buka Plugin Manager (Plugins -> Manage and Install Plugins...).
3. Cari dan aktifkan plugin Anda (misalnya, "FileSystemWatcherPlugin").
4. Pastikan Anda telah mengganti "/path/ke/folder/yang/dipantau" dengan path folder sebenarnya.

how to use :
1. make your destination from watcher settings or add watcher folder
2. when location is added the plugin will automaticly take all the LAS file from your local folder

What's Next:

  * Copy the entire directory containing your new plugin to the QGIS plugin
    directory

  * Compile the resources file using pyrcc5

  * Run the tests (``make test``)

  * Test the plugin by enabling it in the QGIS plugin manager

  * Customize it by editing the implementation file: ``WatcherFolder.py``

  * Create your own custom icon, replacing the default icon.png

  * Modify your user interface by opening fodler_dialog_base.ui in Qt Designer

  * You can use the Makefile to compile your Ui and resource files when
    you make changes. This requires GNU make (gmake)

For more information, see the PyQGIS Developer Cookbook at:
http://www.qgis.org/pyqgis-cookbook/index.html

(C) 2011-2018 GeoApt LLC - geoapt.com
