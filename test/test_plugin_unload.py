"""QGIS calls unload() when the plugin is disabled, reloaded or uninstalled."""


def test_unload_takes_the_panel_down(ae, qgis_iface, monkeypatch):
    """The panel is docked to the QGIS window, so it outlives the plugin unless it is removed"""
    removed = []
    monkeypatch.setattr(qgis_iface, "removeDockWidget", removed.append)
    dock = ae.dock

    ae.unload()

    assert removed == [dock], "the panel was left docked to the QGIS window"
    assert dock.parent() is None


def test_unload_closes_an_open_project(ae_with_project, qgis_iface, monkeypatch):
    """The panel is the only way of closing a project, so an open one has to go with it"""
    monkeypatch.setattr(qgis_iface, "removeDockWidget", lambda dock: None)
    assert ae_with_project.project is not None

    ae_with_project.unload()

    assert ae_with_project.project is None
    assert ae_with_project.available_scenarios == []
    assert not ae_with_project.layers


def test_unload_stops_qgis_from_signalling_into_the_plugin(ae, qgis_iface, monkeypatch):
    """A connected signal keeps the menu alive and calls into it long after it was unloaded"""
    from qgis.core import QgsProject

    monkeypatch.setattr(qgis_iface, "removeDockWidget", lambda dock: None)

    ae.unload()

    # Nothing left to disconnect is precisely what unload has to leave behind
    for signal, slot in [
        (QgsProject.instance().layerRemoved, ae.layerRemoved),
        (QgsProject.instance().readProject, ae.reload_project),
    ]:
        try:
            signal.disconnect(slot)
            raise AssertionError(f"{slot.__name__} is still connected to QGIS")
        except TypeError:
            pass
