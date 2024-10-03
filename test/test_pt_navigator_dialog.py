import pytest

from qaequilibrae.modules.public_transport_procedures.transit_navigator_dialog import TransitNavigatorDialog


@pytest.fixture
def dialog(pt_project):
    dialog = TransitNavigatorDialog(pt_project)
    return dialog


def layer_labels(layer, chbox):
    assert not layer.labelsEnabled()

    # Adds labels
    chbox.setChecked(True)
    assert layer.labelsEnabled()

    # Removes labels
    chbox.setChecked(False)
    assert not layer.labelsEnabled()


def test_show_label_stops(dialog):
    dialog.map_stops()
    layer_labels(dialog.stops_layer, dialog.chb_label_stops)


def test_show_label_zones(dialog):
    dialog.map_zones()
    layer_labels(dialog.zones_layer, dialog.chb_label_zones)


def test_allow_filters(dialog):
    for mode in [True, False, True]:
        dialog.chb_agency.setChecked(mode)
        assert dialog.cob_agency.isEnabled() == mode

        dialog.chb_type.setChecked(mode)
        assert dialog.cob_type.isEnabled() == mode

        dialog.chb_time.setChecked(mode)
        for item in [dialog.lbl_time1, dialog.lbl_time2, dialog.time_from, dialog.time_to]:
            assert item.isEnabled() == mode


def test_search_stop(dialog):
    assert dialog.stops.shape[0] > 10
    dialog.ln_stop_id.setText("10000000028")

    assert dialog.stops.shape[0] == 1
    assert dialog.routes.shape[0] == 2

    dialog.reset_global()
    assert dialog.stops.shape[0] > 10
    dialog.ln_stop_name.setText("Unimarc")
    assert dialog.stops.shape[0] == 1

    dialog.reset_global()
    assert dialog.stops.shape[0] > 10
    dialog.ln_stop.setText("1804695")
    assert dialog.stops.shape[0] == 1


def test_search_route(dialog):
    assert dialog.routes.shape[0] == 2

    dialog.ln_route_id.setText("10001000000")
    assert dialog.routes.shape[0] == 2
    assert dialog.stops.shape[0] == 78

    dialog.reset_global()
    assert dialog.routes.shape[0] == 2

    dialog.ln_route.setText("101387")
    assert dialog.routes.shape[0] == 2
    assert dialog.stops.shape[0] == 78


def test_filter_direction(dialog):
    dialog.chb_agency.setChecked(True)
    dialog.cob_agency.setCurrentText("Liserco")

    assert dialog.all_routes.shape[0] == 2

    dialog.rdo_ab_direction.setChecked(True)
    assert dialog.all_routes.shape[0] == 2


def test_select_element(dialog):
    dialog.reset_global()
    dialog.list_routes.selectRow(0)
    assert dialog.routes.shape[0] == 2

    dialog.reset_global()
    dialog.list_stops.selectRow(0)
    assert dialog.routes.shape[0] == 2


def test_enable_stop_mapping(dialog):
    # Enable zone mapping
    dialog.rdo_map_zones.setChecked(True)


def test_drap_maps(dialog):
    dialog.but_map_zones.click()


def all_items(cob):
    return [cob.itemText(i) for i in range(cob.count())]


def test_map_stops(dialog):
    for map_type in all_items(dialog.cob_stops_map_type):
        dialog.cob_stops_map_type.setCurrentText(map_type)
        for metric in all_items(dialog.cob_stops_map_info):
            dialog.cob_stops_map_info.setCurrentText(metric)
            dialog.but_map_stops.click()


def test_map_lines(dialog):
    for metric in all_items(dialog.cob_routes_map_info):
        dialog.cob_routes_map_info.setCurrentText(metric)
        dialog.but_map_routes.click()


def test_map_zones(dialog):
    dialog.but_map_zones.click()
