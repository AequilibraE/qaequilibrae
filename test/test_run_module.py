from os.path import join
from unittest import mock

import numpy as np
from aequilibrae.utils.create_delaunay_network import DelaunayAnalysis
from qgis.PyQt.QtCore import Qt

from qaequilibrae.modules.project_procedures.run_module_dialog import RunModuleDialog
from .utilities import create_matrix

functions = {0: "matrix_summary", 1: "graph_summary", 2: "results_summary", 3: "example_function_with_kwargs"}


def create_dialog_with_matrix(project):
    pth = join(project.project.project_base_path, "matrices/demand.aem")
    create_matrix(np.arange(1, 134), pth)

    matrices = project.project.matrices
    matrices.update_database()
    matrices.reload()

    return RunModuleDialog(project)


def test_matrix_summary(coquimbo_project, qtbot, timeoutDetector):
    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = create_dialog_with_matrix(coquimbo_project)

        dialog.cob_function.setCurrentIndex(0)
        assert dialog.cob_function.currentText() == functions[0]

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

        project_log = dialog.project.log()
        contents = project_log.contents()

        mat_info = """{"b\'\'": {\'demand\': {\'total\': 176890.0, \'min\': 10.0, \'max\': 10.0, \'nnz\': 17689}}}"""
        assert mat_info in contents[-1]


def test_graph_summary(coquimbo_project, qtbot, timeoutDetector):
    project = coquimbo_project.project

    network = project.network
    network.build_graphs(modes=["c"])

    graph = network.graphs["c"]
    graph.set_graph("distance")
    graph.set_skimming("distance")
    graph.set_blocked_centroid_flows(False)

    # Patch LogDialog to avoid modal exec_ blocking the test
    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = RunModuleDialog(coquimbo_project)

        dialog.cob_function.setCurrentIndex(1)
        assert dialog.cob_function.currentText() == functions[1]

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

        project_log = dialog.project.log()
        contents = project_log.contents()

        mat_info = """{'c': {'num_links': 34546, 'num_nodes': 15724, 'num_zones': 133, 'compact_num_links': 18375, 'compact_num_nodes': 6777}}"""
        assert mat_info in contents[-1]


def test_results_summary(coquimbo_project, qtbot, timeoutDetector):
    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = create_dialog_with_matrix(coquimbo_project)

        project = coquimbo_project.project
        da = DelaunayAnalysis(project)
        da.create_network("zones")

        demand = project.matrices.get_matrix("b''")
        demand.computational_view(["demand"])

        da.assign_matrix(demand, "delaunay_test")

        dialog.cob_function.setCurrentIndex(2)
        assert dialog.cob_function.currentText() == functions[2]

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

        project_log = dialog.project.log()
        contents = project_log.contents()

        assert """delaunay_test""" in contents


def test_example_function_with_kwargs(coquimbo_project, qtbot, timeoutDetector):
    # Patch LogDialog to avoid modal exec_ blocking the test
    with mock.patch("qaequilibrae.modules.project_procedures.run_module_dialog.LogDialog") as MockLogDialog:
        # Make exec_ do nothing
        MockLogDialog.return_value.exec_ = lambda *args, **kwargs: None
        MockLogDialog.return_value.show = lambda *args, **kwargs: None

        dialog = RunModuleDialog(coquimbo_project)

        dialog.cob_function.setCurrentIndex(3)
        assert dialog.cob_function.currentText() == functions[3]

        qtbot.mouseClick(dialog.but_run, Qt.LeftButton)

        project_log = dialog.project.log()
        contents = project_log.contents()

        assert "None" in contents[-1]
