import numpy as np
import pandas as pd
import pytest
from aequilibrae.distribution import Ipf
from aequilibrae.paths import TrafficAssignment, TrafficClass
from qgis.core import QgsProject

from qaequilibrae.modules.gis.compare_scenarios_dialog import CompareScenariosDialog, directional_field_pairs
from qaequilibrae.modules.menu_actions.load_project_action import _run_load_project_from_path
from .utilities import run_sfalls_assignment


@pytest.fixture
def model_path(sf_project):
    path = str(sf_project.project.project_base_path)
    proj = run_sfalls_assignment(sf_project)
    proj = future_assignment(proj)

    proj.project.close()

    yield path


@pytest.mark.parametrize("composite", [True, False])
def test_compare_scenarios(ae, model_path, composite):

    _run_load_project_from_path(ae, model_path)

    dialog = CompareScenariosDialog(ae)
    dialog.cob_alternative_result.setCurrentText("future_assignment")
    dialog.radio_compo.setChecked(composite)
    dialog.radio_diff.setChecked(not composite)

    dialog.execute_comparison()

    prj_layers = [lyr.name() for lyr in QgsProject.instance().mapLayers().values()]
    assert prj_layers == ["scenario_comparison"]

    link_layer = QgsProject.instance().mapLayersByName("scenario_comparison")[0]
    field_names = link_layer.fields().names()
    fields = ["base_matrix_ab", "base_matrix_ba", "alternative_matrix_ab", "alternative_matrix_ba"]
    for f in fields:
        assert f in field_names


def test_directional_field_pairs():
    """Result tables mix cases, and the pair has to come back spelled as the table spells it"""
    fields = ["link_id", "matrix_ab", "matrix_ba", "matrix_tot", "VOC_AB", "VOC_BA", "VOC_max", "Preload_AB"]

    assert dict(directional_field_pairs(fields)) == {
        "matrix_*": ("matrix_ab", "matrix_ba"),
        "VOC_*": ("VOC_AB", "VOC_BA"),
    }, "a field without its counterpart, or without a direction at all, is not a pair"

    # Paired on the suffix, so the "ab" in the middle of a class called "cab" is left alone
    assert dict(directional_field_pairs(["cab_ab", "cab_ba"])) == {"cab_*": ("cab_ab", "cab_ba")}


@pytest.mark.parametrize("field", ["matrix_*", "Preload_*", "Congested_Time_*", "VOC_*"])
def test_compare_scenarios_on_every_offered_field(ae, model_path, field):
    """Only the flow columns are lower case; the rest used to reach the layer under a name it did not carry."""
    _run_load_project_from_path(ae, model_path)

    dialog = CompareScenariosDialog(ae)
    dialog.cob_alternative_result.setCurrentText("future_assignment")
    dialog.cob_base_data.setCurrentText(field)
    dialog.cob_alternative_data.setCurrentText(field)
    assert dialog.cob_base_data.currentText() == field, "the field is not on offer"
    base_pair = dialog.cob_base_data.currentData()
    alter_pair = dialog.cob_alternative_data.currentData()
    dialog.radio_compo.setChecked(True)

    dialog.execute_comparison()

    link_layer = QgsProject.instance().mapLayersByName("scenario_comparison")[0]
    names = link_layer.fields().names()
    # Off the combo, not the label: the label is the one thing that need not match the column
    for prefix, pair in [("base", base_pair), ("alternative", alter_pair)]:
        for column in pair:
            assert f"{prefix}_{column}" in names

    # The bandwidths only get built once the maximum is known, so the styling is the proof
    assert link_layer.renderer().symbol().symbolLayerCount() > 1


def future_assignment(aeq_from_qgis):

    project = aeq_from_qgis.project
    project.network.build_graphs()

    graph = project.network.graphs["c"]
    graph.set_graph("free_flow_time")
    graph.set_skimming(["free_flow_time", "distance"])
    graph.set_blocked_centroid_flows(False)

    demand = project.matrices.get_matrix("demand_omx")
    demand.computational_view(["matrix"])

    # Calibrate gravity model
    proj_matrices = project.matrices
    imped = proj_matrices.get_matrix("assignment_car")
    imped_core = "free_flow_time_final"
    imped.computational_view([imped_core])

    np.fill_diagonal(imped.matrix_view, 0)
    intrazonals = np.amin(imped.matrix_view, where=imped.matrix_view > 0, initial=imped.matrix_view.max(), axis=1)
    intrazonals *= 0.75
    np.fill_diagonal(imped.matrix_view, intrazonals)

    imped.save(names=["final_time_with_intrazonals"])

    # Adjust future demand with IPF
    origins = np.sum(demand.matrix_view, axis=1)
    destinations = np.sum(demand.matrix_view, axis=0)
    orig = origins * (1 + np.random.rand(origins.shape[0]) / 10)
    dest = destinations * (1 + np.random.rand(origins.shape[0]) / 10)
    dest *= orig.sum() / dest.sum()

    vectors = pd.DataFrame({"origins": orig, "destinations": dest}, index=demand.index[:])

    args = {
        "matrix": demand,
        "vectors": vectors,
        "column_field": "destinations",
        "row_field": "origins",
        "nan_as_zero": True,
    }

    ipf = Ipf(**args)
    ipf.fit()

    ipf.save_to_project(name="demand_ipfd", file_name="demand_ipfd.omx")

    imped = proj_matrices.get_matrix("assignment_car")
    imped.computational_view(["final_time_with_intrazonals"])

    # Future traffic assignment
    demand = proj_matrices.get_matrix("demand_ipfd")
    demand.computational_view("matrix")

    assigclass = TrafficClass("car", graph, demand)

    assig = TrafficAssignment()

    assig.set_classes([assigclass])
    assig.set_vdf("BPR")
    assig.set_vdf_parameters({"alpha": "b", "beta": "power"})
    assig.set_capacity_field("capacity")
    assig.set_time_field("free_flow_time")
    assig.set_algorithm("bfw")
    assig.max_iter = 5
    assig.rgap_target = 0.01
    assig.execute()

    assig.save_results("future_assignment")
    assig.save_skims("future_assignment", which_ones="all", format="omx")

    return aeq_from_qgis
