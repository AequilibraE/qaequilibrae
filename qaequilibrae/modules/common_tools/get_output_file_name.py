from os import path
import tempfile

from qgis.PyQt.QtWidgets import QFileDialog


LAST_FOLDER_FILE = "aequilibrae_last_folder.txt"


def _breadcrumb_path():
    return path.join(tempfile.gettempdir(), LAST_FOLDER_FILE)


def _existing_folder(folder_path):
    if folder_path is None:
        return None

    folder_path = str(folder_path).strip()
    if not folder_path:
        return None

    folder_path = path.expanduser(folder_path)
    if path.isdir(folder_path):
        return path.abspath(folder_path)
    if path.isfile(folder_path):
        return path.abspath(path.dirname(folder_path))

    parent = path.dirname(folder_path)
    if parent and path.isdir(parent):
        return path.abspath(parent)

    return None


def remember_folder(folder_path):
    folder = _existing_folder(folder_path)
    if folder is None:
        return None

    try:
        with open(_breadcrumb_path(), "w") as file:
            file.write(folder)
    except OSError:
        pass

    return folder


def last_accessed_folder(default_path=None):
    try:
        with open(_breadcrumb_path(), "r") as file:
            folder = _existing_folder(file.readline())
    except OSError:
        folder = None

    for candidate in (folder, default_path, tempfile.gettempdir()):
        folder = _existing_folder(candidate)
        if folder is not None:
            return folder

    return tempfile.gettempdir()


def GetOutputFileName(clss, box_name, file_types, default_type, start_path):
    dlg = QFileDialog(clss)
    dlg.setDirectory(last_accessed_folder(start_path))
    dlg.setWindowTitle(box_name)
    dlg.setViewMode(QFileDialog.ViewMode.Detail)
    a = []
    for i in file_types:
        a.append(clss.tr(i))
    dlg.setNameFilters(a)
    dlg.setDefaultSuffix(default_type)
    new_name = None
    extension = None
    if dlg.exec():
        new_name = dlg.selectedFiles()[0]
        new_name = new_name.replace("..", ".")
        remember_folder(new_name)
        last_dot = new_name.rfind(".")
        extension = new_name[last_dot + 1 :]
        return new_name, extension.upper()
    else:
        return None, None


def GetOutputFolderName(base_path=None, message="Select a folder:"):
    folder = QFileDialog.getExistingDirectory(
        None, message, last_accessed_folder(base_path), QFileDialog.Option.ShowDirsOnly
    )
    remember_folder(folder)
    return folder
