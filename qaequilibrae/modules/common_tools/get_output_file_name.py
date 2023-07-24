from qgis.PyQt.QtWidgets import QFileDialog
import tempfile


def GetOutputFileName(clss, box_name, file_types, default_type, start_path):
    dlg = QFileDialog(clss)
    dlg.setDirectory(start_path)
    dlg.setWindowTitle(box_name)
    dlg.setViewMode(QFileDialog.Detail)
    a = []
    for i in file_types:
        a.append(clss.tr(i))
    dlg.setNameFilters(a)
    dlg.setDefaultSuffix(default_type)
    new_name = None
    extension = None
    if dlg.exec_():
        new_name = dlg.selectedFiles()[0]
        new_name = new_name.replace("..", ".")
        if new_name[-4] == ".":
            extension = new_name[-3:]
        else:
            extension = new_name[-4:]
    return new_name, extension


def GetOutputFolderName(base_path=None, message="Select a folder:"):
    if base_path is None:
        base_path = tempfile.gettempdir()
    return QFileDialog.getExistingDirectory(None, message, base_path, QFileDialog.ShowDirsOnly)
