import numpy as np
import pandas as pd
from aequilibrae.parameters import Parameters
from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QApplication, QMessageBox

from qaequilibrae.modules.project_procedures.run_module_dialog import RunModuleDialog
from .utilities import create_matrix

functions = {0: "matrix_summary", 1: "graph_summary", 2: "results_summary", 3: "example_function_with_kwargs"}


def create_dialog_with_matrix(project):
    pth = project.project.project_base_path / "matrices" / "demand.aem"
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return RunModuleDialog(project)


def test_example_function_with_kwargs(coquimbo_project, qtbot, timeoutDetector):
    dialog = RunModuleDialog(coquimbo_project)

    dialog.cob_function.setCurrentIndex(0)
    assert dialog.cob_function.currentText() == functions[3]

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert messagebar.messages[3][0] == "example_function_with_kwargs executed:", "Level 3 error message is missing"


def test_new_function(coquimbo_project, qtbot, timeoutDetector):
    func_string = """from aequilibrae.context import get_active_project\n
def create_delaunay(source: str, name: str, computational_view: str, result_name: str, overwrite: bool=False):\n
\tfrom aequilibrae.utils.create_delaunay_network import DelaunayAnalysis\n
\tproject = get_active_project()\n
\tmatrix = project.matrices\n
\tmat = matrix.get_matrix(name)\n
\tmat.computational_view(computational_view)\n
\tda = DelaunayAnalysis(project)\n
\tda.create_network(source, overwrite)\n
\tda.assign_matrix(mat, result_name)\n
"""

    folder = coquimbo_project.project.project_base_path

    with open(folder / "run" / "create_delaunay.py", "w") as file:
        file.write(func_string)

    with open(folder / "run" / "__init__.py", "r") as file:
        lines = file.readlines()

    lines.insert(19, "from .create_delaunay import create_delaunay\n")

    with open(folder / "run" / "__init__.py", "w") as file:
        file.writelines(lines)

    p = Parameters()
    p.parameters["run"]["create_delaunay"] = {}
    p.parameters["run"]["create_delaunay"]["source"] = "zones"
    p.parameters["run"]["create_delaunay"]["name"] = "b''"
    p.parameters["run"]["create_delaunay"]["computational_view"] = "demand"
    p.parameters["run"]["create_delaunay"]["result_name"] = "delaunay_test"
    p.write_back()

    dialog = create_dialog_with_matrix(coquimbo_project)

    assert len(dialog.items) > 1

    dialog.cob_function.setCurrentIndex(0)
    assert dialog.cob_function.currentText() == "create_delaunay"

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    with coquimbo_project.project.results_connection as conn:
        results = pd.read_sql("SELECT * FROM delaunay_test", conn).set_index("link_id")

    assert results.shape != (0, 0)


def wait_for_active_window(qtbot):
    timeout = 3000
    window = QApplication.activeWindow()
    while window is None and timeout > 0:
        window = QApplication.activeWindow()
        qtbot.wait(100)
        timeout -= 100
    assert timeout > 0, "Waiting for window to open timed out after 3 seconds"
    return window


def test_install_external_libraries(coquimbo_project, qtbot):
    # This test is a bit time-consuming due to the second QTimer.singleShot waiting
    # 5 seconds for running the installation of the external library.
    folder = coquimbo_project.project.project_base_path

    with open(folder / "run" / "requirements.txt", "w") as file:
        file.write("seaborn")

    with open(folder / "run" / "seaborn_plot.py", "w") as file:
        file.write("import seaborn as sns\n")
        file.write("from aequilibrae.context import get_active_project\n")
        file.write("def seaborn_plot():\n")
        file.write("\tproject = get_active_project()\n")
        file.write("\tpath = project.project_base_path\n")
        file.write("\tsns.set_theme(style='ticks')")

    with open(folder / "run" / "__init__.py", "r") as file:
        lines = file.readlines()

    lines.insert(19, "from .seaborn_plot import seaborn_plot")

    with open(folder / "run" / "__init__.py", "w") as file:
        file.writelines(lines)

    p = Parameters()
    p.parameters["run"]["seaborn_plot"] = None
    p.write_back()

    def handle_dialog():
        dialog = wait_for_active_window(qtbot)
        ok_button = dialog.button(QMessageBox.Ok)
        qtbot.mouseClick(ok_button, Qt.LeftButton, delay=1)

    QTimer.singleShot(100, handle_dialog)
    QTimer.singleShot(5_000, handle_dialog)

    _ = RunModuleDialog(coquimbo_project)

    # We don't test if the '_dependencies' folder exist because the following
    # assertions can only be verified if the folder exists and the external library
    # is installed.
    dialog = RunModuleDialog(coquimbo_project)
    dialog.cob_function.setCurrentIndex(4)
    assert dialog.cob_function.currentText() == "seaborn_plot"

    qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

    messagebar = coquimbo_project.iface.messageBar()
    assert "seaborn_plot executed" in messagebar.messages[3][0]

    assert not dialog.isVisible()
