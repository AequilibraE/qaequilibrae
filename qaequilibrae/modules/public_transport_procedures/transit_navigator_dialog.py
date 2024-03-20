from functools import partial
from math import ceil
from os.path import dirname, join

import pandas as pd
from qgis.PyQt import uic, QtGui
from qgis.PyQt.QtCore import QSizeF
from qgis.PyQt.QtWidgets import QDialog, QAbstractItemView
from qgis.core import QgsDiagramSettings, QgsDiagramLayerSettings, QgsRendererRange, QgsStackedBarDiagram
from qgis.core import QgsProject, QgsStyle, QgsVectorLayerJoinInfo, QgsGraduatedSymbolRenderer, QgsApplication
from qgis.core import QgsSymbol, QgsLinearlyInterpolatedDiagramRenderer, QgsPalLayerSettings, QgsTextFormat
from qgis.core import QgsTextBufferSettings, QgsVectorLayerSimpleLabeling, QgsPieDiagram

from qaequilibrae.modules.common_tools import layer_from_dataframe, PandasModel
from qaequilibrae.modules.gis.color_ramp_shades import color_ramp_shades
from qaequilibrae.modules.public_transport_procedures.transit_supply_metrics import SupplyMetrics
from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import read_and_close


FORM_CLASS, _ = uic.loadUiType(join(dirname(__file__), "forms/transit_navigator.ui"))


class TransitNavigatorDialog(QDialog, FORM_CLASS):
    def __init__(self, qgis_project):
        QDialog.__init__(self)
        self.setupUi(self)
        self.iface = qgis_project.iface
        self.feed = None
        self.qgis_project = qgis_project
        self.project = qgis_project.project
        self._p = self.project.network
        self.mapped_stops = False
        self.mapped_lines = False
        self.mapped_zones = False
        self.line_target_metric = ""
        self.line_map_layer = ""
        self.stop_target_metric = ""
        self.zone_target_metric = ""
        self.filtered = {}

        self.sm = SupplyMetrics(None)
        self.sm_alt: SupplyMetrics = None
        self._testing = False
        self.gtfs_types = {
            0: "Light rail",
            1: "Subway/Metro",
            2: "Rail",
            3: "Bus",
            4: "Ferry",
            5: "Cable tram",
            6: "Aerial lift",
            7: "Funicular",
            11: "Trolleybus",
            12: "Monorail",
        }

        fldr = join(dirname(dirname(__file__)), "style_loader")
        self.stops_layer = qgis_project.layers["transit_stops"][0]
        self.stops_layer.loadNamedStyle(join(fldr, "stops.qml"), True)

        self.zones_layer = qgis_project.layers["zones"][0]
        self.zones_layer.loadNamedStyle(join(fldr, "zones.qml"), True)

        self.routes_layer = qgis_project.layers["transit_routes"][0]
        self.routes_layer.loadNamedStyle(join(fldr, "routes.qml"), True)

        for layer in [self.zones_layer, self.routes_layer, self.stops_layer]:
            QgsProject.instance().addMapLayer(layer)

        agency_sql = f"Select agency_id, agency from agencies"
        sql = """SELECT route_id, cast(pattern_id as text) pattern_id, 
                        coalesce(ST_X(ST_StartPoint(geometry))-ST_X(ST_EndPoint(geometry)),0) dx,
                        coalesce(ST_Y(ST_StartPoint(geometry))-ST_Y(ST_EndPoint(geometry)),0) dy
                 FROM routes"""
        with read_and_close(database_connection("transit")) as conn:
            self.all_agencies = {ag: ag_id for ag_id, ag in conn.execute(agency_sql)}
            route_df = pd.read_sql(sql, conn)

        route_df = route_df.assign(direction=pd.NA)
        route_df.loc[(route_df.dy.abs() >= route_df.dx.abs()) & (route_df.dy < 0), "direction"] = "N"
        route_df.loc[(route_df.dy.abs() >= route_df.dx.abs()) & (route_df.dy > 0), "direction"] = "S"
        route_df.loc[(route_df.dy.abs() < route_df.dx.abs()) & (route_df.dx > 0), "direction"] = "W"
        route_df.loc[(route_df.dy.abs() < route_df.dx.abs()) & (route_df.dx < 0), "direction"] = "E"
        self.route_directions = route_df[["route_id", "pattern_id", "direction"]]
        if max(route_df.dx.max(), route_df.dy.max()) == 0:
            self.rdo_ab_direction.setEnabled(False)
            self.rdo_ba_direction.setEnabled(False)

        self.all_routes = pd.DataFrame([])
        self.route_patterns = pd.DataFrame([])
        self.all_stops = pd.DataFrame([])
        self.stop_pattern = pd.DataFrame([])
        self.zones = pd.DataFrame([])
        self.reset_data_global()
        self.cob_agency.addItems(list(self.all_agencies.keys()))

        self.cob_type.addItems([self.gtfs_types[tp] for tp in self.all_routes["route_type"].unique()])
        self.gtfs_types = {v: k for k, v in self.gtfs_types.items()}

        for table in [self.list_routes, self.list_stops]:
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.chb_agency.toggled.connect(self.allow_filter_by_agency)
        self.chb_type.toggled.connect(self.allow_filter_by_gtfs_type)
        self.chb_time.toggled.connect(self.allow_filter_by_time)
        self.but_reset.clicked.connect(self.reset)
        self.but_reset_global.clicked.connect(self.reset_global)
        self.reset()

        self.chb_label_stops.toggled.connect(self.show_label_stops)
        self.chb_label_lines.toggled.connect(self.show_label_lines)
        self.chb_label_zones.toggled.connect(self.show_label_zones)

        self.ln_route_id.textChanged.connect(partial(self.search_route, "route_id"))
        self.ln_route.textChanged.connect(partial(self.search_route, "route"))

        self.ln_stop_id.textChanged.connect(partial(self.search_stop, "stop_id"))
        self.ln_stop.textChanged.connect(partial(self.search_stop, "stop"))
        self.ln_stop_name.textChanged.connect(partial(self.search_stop, "stop_name"))

        self.cob_agency.currentIndexChanged.connect(self.filter_direction)
        self.cob_type.currentIndexChanged.connect(self.filter_direction)

        # Direction filtering
        self.rdo_all_directions.toggled.connect(self.filter_direction)
        self.rdo_ab_direction.toggled.connect(self.filter_direction)
        self.rdo_ba_direction.toggled.connect(self.filter_direction)

        # Sets mapping objects
        self.rdo_map_stops.toggled.connect(self.enable_stop_mapping)
        self.rdo_no_map_stops.toggled.connect(self.enable_stop_mapping)
        self.cob_stops_map_type.currentIndexChanged.connect(self.allows_colors_stops)
        self.enable_stop_mapping()
        self.but_map_stops.clicked.connect(self.map_stops)
        self.sld_stop_scale.valueChanged.connect(self.draw_stop_styles)
        self.stop_metric_layer = None

        # ZONES
        self.rdo_no_map_zones.toggled.connect(self.enable_zone_mapping)
        self.rdo_map_zones.toggled.connect(self.enable_zone_mapping)
        self.cob_zones_map_type.currentIndexChanged.connect(self.allows_colors_zones)
        self.enable_zone_mapping()
        self.but_map_zones.clicked.connect(self.map_zones)
        self.sld_zone_scale.valueChanged.connect(self.draw_zone_styles)
        self.zone_metric_layer = None

        self.rdo_no_map_routes.toggled.connect(self.enable_line_mapping)
        self.rdo_map_routes.toggled.connect(self.enable_line_mapping)
        self.cob_routes_map_type.currentIndexChanged.connect(self.allows_colors_line)
        self.enable_line_mapping()
        self.but_map_routes.clicked.connect(self.map_lines)
        self.sld_route_scale.valueChanged.connect(self.draw_line_styles)
        self.line_metric_layer = None
        self.time_from.timeChanged.connect(self.update_time)
        self.time_to.timeChanged.connect(self.update_time)

        self.glob_filter_box.setCollapsed(True)
        self.glob_stop_map.setCollapsed(True)
        self.glob_route_map.setCollapsed(True)
        self.glob_zone_map.setCollapsed(True)

        self.selected_stops = None
        self.selected_patterns = None
        self.selected_routes = None
        self.selected_from_time = None
        self.selected_to_time = None

    def show_label_stops(self):
        self.build_label(
            self.stops_layer,
            f"metrics_{self.stop_target_metric}",
            self.chb_label_stops.isChecked(),
            self.mapped_stops,
            QgsPalLayerSettings.AroundPoint,
        )

    def show_label_lines(self):
        self.build_label(
            self.line_map_layer,
            f"metrics_{self.line_target_metric}",
            self.chb_label_lines.isChecked(),
            self.mapped_lines,
            QgsPalLayerSettings.Line,
        )

    def show_label_zones(self):
        self.build_label(
            self.zones_layer,
            f"metrics_{self.zone_target_metric}",
            self.chb_label_zones.isChecked(),
            self.mapped_zones,
            QgsPalLayerSettings.AroundPoint,
        )

    def build_label(self, layer, field, active_label, active_map, placement):
        if not active_map and not self._testing:
            return
        if not active_label:
            layer.setLabelsEnabled(False)
            layer.triggerRepaint()
            return

        label = QgsPalLayerSettings()
        txt_format = QgsTextFormat()
        txt_format.setFont(QtGui.QFont("Arial", 10))
        txt_format.setColor(QtGui.QColor("Black"))
        buff = QgsTextBufferSettings()
        buff.setSize(1)
        buff.setEnabled(True)
        txt_format.setBuffer(buff)
        label.setFormat(txt_format)
        label.fieldName = f"""to_int(round("{field}",0))"""
        label.isExpression = True
        label.placement = placement
        layer.setLabelsEnabled(True)
        layer.setLabeling(QgsVectorLayerSimpleLabeling(label))
        layer.triggerRepaint()

    def search_route(self, field: str):
        rt = str(self.ln_route_id.text()) if field == "route_id" else str(self.ln_route.text())
        self.routes = self.routes[self.routes[field].astype(str).str.contains(rt, case=False)]
        self.patterns = self.patterns[self.patterns.route_id.isin(self.routes.route_id)]

        filtered = self.stop_pattern[self.stop_pattern.route_id.isin(self.patterns.route_id)]
        self.stops = self.all_stops[self.all_stops.stop_id.isin(filtered.stop_id)]

        self.populate_routes()
        self.populate_stops()
        self.redo_map()

    def search_stop(self, field: str):
        stop = str(self.ln_stop_id.text()) if field == "stop_id" else str(self.ln_stop.text())
        stop = str(self.ln_stop_name.text()) if field == "stop_name" else stop

        filtered = self.stop_pattern[self.stop_pattern[field].astype(str).str.contains(stop, case=False)]
        self.patterns = self.route_patterns[self.route_patterns.route_id.isin(filtered.route_id)]
        self.routes = self.all_routes[self.all_routes.route_id.isin(self.patterns.route_id)]
        self.stops = self.all_stops[self.all_stops.stop_id.isin(filtered.stop_id)]
        self.populate_routes()
        self.populate_stops()
        self.redo_map()

    def reset_global(self):
        for item in [self.chb_agency, self.chb_type]:
            item.setChecked(False)
        self.reset_data_global()

    def reset_data_global(self):
        self.all_routes = self.sm.route_metrics()
        self.route_patterns = self.all_routes.merge(self.route_directions, on="route_id", how="left")

        self.all_stops = self.sm.stop_metrics()
        self.stop_pattern = self.sm._stop_pattern.copy(True)

        # If empty, we just throw in some arbitrary direction
        self.route_patterns.loc[self.route_patterns.direction.isna(), "direction"] = "S"

        self.zones = self.sm.zone_metrics()

        self.reset()

    def reset(self):
        self.filtered.clear()
        self.reset_lists()

        if self.mapped_stops:
            self.map_stops()

        if self.mapped_lines:
            self.map_lines()

    def filter_direction(self):
        self.reset_data_global()
        if self.rdo_ab_direction.isChecked():
            self.route_patterns = self.route_patterns[self.route_patterns.direction.isin(["S", "W"])]
        elif self.rdo_ba_direction.isChecked():
            self.route_patterns = self.route_patterns[self.route_patterns.direction.isin(["N", "E"])]

        self.all_routes = self.all_routes[self.all_routes.route_id.isin(self.route_patterns.route_id)]
        filtered = self.stop_pattern[self.stop_pattern.route_id.isin(self.route_patterns.route_id)]
        self.stops = self.all_stops[self.all_stops.stop_id.isin(filtered.stop_id)]
        self.global_filters_only()

    def reset_lists(self):
        self.routes = self.all_routes.copy(True)
        self.patterns = self.route_patterns.copy(True)
        self.stops = self.all_stops.copy(True)
        self.populate_routes()
        self.populate_stops()
        self.routes_layer.setSubsetString("")
        self.stops_layer.setSubsetString("")

    def allow_filter_by_agency(self):
        self.cob_agency.setEnabled(self.chb_agency.isChecked())
        self.global_filters()

    def global_filters(self):
        self.reset_data_global()
        self.global_filters_only()

    def global_filters_only(self):
        if self.chb_agency.isChecked():
            agency_id = self.all_agencies[self.cob_agency.currentText()]

            self.all_routes = self.all_routes[self.all_routes.agency_id == agency_id]
            self.route_patterns = self.route_patterns[self.route_patterns.route_id.isin(self.all_routes.route_id)]
            self.all_stops = self.all_stops[self.all_stops.agency_id == agency_id]
            self.stop_pattern = self.stop_pattern[self.stop_pattern.agency_id == agency_id]
        if self.chb_type.isChecked():
            gtfs_tp = self.gtfs_types[self.cob_type.currentText()]

            self.all_routes = self.all_routes[self.all_routes.route_type == gtfs_tp]
            self.route_patterns = self.route_patterns[self.route_patterns.route_id.isin(self.all_routes.route_id)]
            self.all_stops = self.all_stops[self.all_stops.route_type == gtfs_tp]
            self.stop_pattern = self.stop_pattern[self.stop_pattern.route_type == gtfs_tp]
        self.reset()
        self.redo_map()

    def allow_filter_by_gtfs_type(self):
        self.cob_type.setEnabled(self.chb_type.isChecked())
        self.global_filters()

    def allow_filter_by_time(self):
        for item in [self.lbl_time1, self.lbl_time2, self.time_from, self.time_to]:
            item.setEnabled(self.chb_time.isChecked())
        self.global_filters()

    def select_route(self):
        idx = [x.row() for x in list(self.list_routes.selectionModel().selectedRows())][0]

        route_id = self.routes.route_id.values[idx]
        self.filtered = {"routes": [route_id]}

        self.patterns = self.route_patterns[self.route_patterns.route_id == route_id]

        filtered = self.stop_pattern[self.stop_pattern.route_id.isin(self.patterns.route_id)]
        self.stops = self.all_stops[self.all_stops.stop_id.isin(filtered.stop_id)]

        self.populate_stops()
        self.redo_map()
        self.routes_layer.setSubsetString(f'"route_id" = {route_id}')
        self.iface.mapCanvas().setExtent(self.routes_layer.extent())
        self.iface.mapCanvas().refresh()

    def select_stop(self):
        idx = [x.row() for x in list(self.list_stops.selectionModel().selectedRows())][0]

        stop_id = self.stops.stop_id.values[idx]
        self.filtered = {"stops": [stop_id]}
        filtered = self.stop_pattern[self.stop_pattern.stop_id == stop_id]
        self.patterns = self.route_patterns[self.route_patterns.route_id.isin(filtered.route_id)]
        self.routes = self.all_routes[self.all_routes.route_id.isin(self.patterns.route_id)]
        self.populate_routes()
        self.redo_map()
        self.stops_layer.setSubsetString(f'"stop_id" = {stop_id}')

    def populate_routes(self):
        self.routes_model = PandasModel(self.routes[["route_id", "route"]])
        self.list_routes.setModel(self.routes_model)
        self.list_routes.setVerticalHeader(None)
        self.list_routes.selectionModel().selectionChanged.connect(self.select_route)

    def populate_stops(self):
        fields = ["stop_id", "stop", "stop_name"]
        fields += ["stop_order"] if "stop_order" in self.stops else []
        self.stops_model = PandasModel(self.stops[fields])
        self.list_stops.setModel(self.stops_model)
        self.list_stops.setVerticalHeader(None)
        self.list_stops.selectionModel().selectionChanged.connect(self.select_stop)

    def redo_map(self):
        if self.stops.shape[0] > 0:
            stops = tuple(self.stops.stop_id.tolist())
            fltr = f'"stop_id" IN {str(stops)}' if len(stops) > 1 else f'"stop_id" = {stops[0]}'
            self.stops_layer.setSubsetString(fltr)
        else:
            self.stops_layer.setSubsetString('"stop_id"=-999999')

        if self.routes.shape[0] > 0:
            rt = tuple(self.routes.route_id.tolist())
            fltr = f'"route_id" IN {str(rt)}' if len(rt) > 1 else f'"route_id" = {rt[0]}'
            self.routes_layer.setSubsetString(fltr)
        else:
            self.routes_layer.setSubsetString('"route_id"=-999999')

        if self.mapped_stops:
            self.map_stops()
        if self.mapped_lines:
            self.map_lines()
        if self.mapped_zones:
            self.map_zones()

        for lyr in [self.stops_layer, self.routes_layer, self.zones_layer]:
            lyr.triggerRepaint()
        ext = self.routes_layer.extent()
        ext.combineExtentWith(self.stops_layer.extent())
        self.iface.mapCanvas().setExtent(ext)
        self.iface.mapCanvas().refresh()

    def enable_stop_mapping(self):
        default_style = QgsStyle().defaultStyle()
        for item in [
            self.cob_stops_map_type,
            self.cob_stops_map_info,
            self.cob_stops_color,
            self.sld_stop_scale,
            self.but_map_stops,
            self.lbl_scl_stop,
        ]:
            item.setEnabled(self.rdo_map_stops.isChecked())

        for cob in [self.cob_stops_map_type, self.cob_stops_map_info, self.cob_stops_color]:
            cob.clear()
        if self.rdo_map_stops.isChecked():
            self.cob_stops_map_type.addItems(["Color", "Thickness"])
            self.cob_stops_map_info.addItems(self.sm.list_stop_metrics())
            self.cob_stops_color.addItems(list(default_style.colorRampNames()))
        else:
            self.mapped_stops = False
            fldr = join(dirname(dirname(__file__)), "style_loader")
            self.stops_layer.loadNamedStyle(join(fldr, "stops.qml"), True)
            self.stops_layer.triggerRepaint()
        self.allows_colors_stops()
        self.iface.mapCanvas().refresh()

    def enable_zone_mapping(self):
        default_style = QgsStyle().defaultStyle()
        for item in [
            self.cob_zones_map_type,
            self.cob_zones_map_info,
            self.cob_zones_color,
            self.sld_zone_scale,
            self.but_map_zones,
            self.lbl_scl_zone,
        ]:
            item.setEnabled(self.rdo_map_zones.isChecked())

        for cob in [self.cob_zones_map_type, self.cob_zones_map_info, self.cob_zones_color]:
            cob.clear()

        if self.rdo_map_zones.isChecked():
            self.cob_zones_map_type.addItems(["Color", "Pie chart", "Stacked bars"])
            self.cob_zones_map_info.addItems(self.sm.list_zone_metrics())
            self.cob_zones_color.addItems(list(default_style.colorRampNames()))
        else:
            self.mapped_zones = False
            fldr = join(dirname(dirname(__file__)), "style_loader")
            self.zones_layer.loadNamedStyle(join(fldr, "zones.qml"), True)
            self.zones_layer.triggerRepaint()

        self.allows_colors_zones()
        self.but_map_zones.setEnabled(True)
        self.iface.mapCanvas().refresh()

    def allows_colors_stops(self):
        self.cob_stops_color.setVisible(self.cob_stops_map_type.currentText() == "Color")
        self.sld_stop_scale.setEnabled(self.cob_stops_map_type.currentText() != "Color")

    def allows_colors_zones(self):
        self.cob_zones_color.setVisible(self.cob_zones_map_type.currentText() == "Color")
        self.sld_zone_scale.setEnabled(self.cob_zones_map_type.currentText() != "Color")

    def map_stops(self):
        self.mapped_stops = True
        self.but_map_stops.setEnabled(False)
        if self.stop_metric_layer is not None:
            QgsProject.instance().removeMapLayers([self.stop_metric_layer.id()])
            rem = [lien.joinLayerId() for lien in self.stops_layer.vectorJoins()]
            for lien_id in rem:
                self.stops_layer.removeJoin(lien_id)

        minutes_from = self.time_from.time().hour() * 60 + self.time_from.time().minute()
        minutes_to = self.time_to.time().hour() * 60 + self.time_to.time().minute()
        from_time = minutes_from if self.chb_time.isChecked() else None
        to_time = minutes_to if self.chb_time.isChecked() else None

        stops = self.filtered.get("stops", self.stops.stop_id.tolist())
        routes = self.filtered.get("routes", self.routes.route_id.tolist())

        self.stop_target_metric = self.cob_stops_map_info.currentText()
        if self.stop_target_metric in self.sm.list_stop_metrics():
            df = self.sm.stop_metrics(from_minute=from_time, to_minute=to_time, routes=routes, stops=stops)

        self.stop_metric_layer = layer_from_dataframe(df, "stop_metrics")

        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName("stop_id")
        lien.setTargetFieldName("stop_id")
        lien.setJoinLayerId(self.stop_metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(self.stop_metric_layer)
        lien.setPrefix("metrics_")
        self.stops_layer.addJoin(lien)
        self.draw_stop_styles()
        self.but_map_stops.setEnabled(True)
        self.show_label_stops()

    def map_zones(self):
        self.mapped_zones = True
        self.but_map_zones.setEnabled(False)
        if self.zone_metric_layer is not None:
            QgsProject.instance().removeMapLayers([self.zone_metric_layer.id()])
            rem = [lien.joinLayerId() for lien in self.zones_layer.vectorJoins()]
            for lien_id in rem:
                self.zones_layer.removeJoin(lien_id)

        minutes_from = self.time_from.time().hour() * 60 + self.time_from.time().minute()
        minutes_to = self.time_to.time().hour() * 60 + self.time_to.time().minute()
        from_time = minutes_from if self.chb_time.isChecked() else None
        to_time = minutes_to if self.chb_time.isChecked() else None

        stops = self.filtered.get("stops", self.stops.stop_id.tolist())
        routes = self.filtered.get("routes", self.routes.route_id.tolist())

        self.zone_target_metric = self.cob_zones_map_info.currentText()
        sample = self.sb_sample.value() / 100

        df = self.sm.zone_metrics(from_minute=from_time, to_minute=to_time, routes=routes, stops=stops)
        df.loc[:, self.sm.list_zone_metrics()] /= sample

        self.zone_metric_layer = layer_from_dataframe(df, "zone_metrics")

        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName("zone_id")
        lien.setTargetFieldName("zone_id")
        lien.setJoinLayerId(self.zone_metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(self.zone_metric_layer)
        lien.setPrefix("metrics_")
        self.zones_layer.addJoin(lien)
        self.show_label_zones()
        self.draw_zone_styles()
        self.but_map_zones.setEnabled(True)

    def draw_stop_styles(self):
        fld = f"metrics_{self.stop_target_metric}"
        idx = self.stops_layer.fields().indexFromName(fld)
        max_metric = self.stops_layer.maximumValue(idx)
        method = self.cob_stops_map_type.currentText()

        val = self.sld_stop_scale.value() / 2
        color_ramp_name = "Blues" if method != "Color" else self.cob_stops_color.currentText()
        self.map_ranges(fld, max_metric, method, self.stops_layer, val, color_ramp_name)
        self.but_map_stops.setEnabled(True)

    def draw_zone_styles(self):
        fld = f"metrics_{self.zone_target_metric}"
        idx = self.zones_layer.fields().indexFromName(fld)
        max_metric = self.zones_layer.maximumValue(idx)
        method = self.cob_zones_map_type.currentText()

        val = self.sld_zone_scale.value()
        color_ramp_name = "Blues" if method != "Color" else self.cob_zones_color.currentText()

        if method == "Color":
            self.map_ranges(fld, max_metric, method, self.zones_layer, val / 2, color_ramp_name)
        else:
            self.map_diagram(fld, max_metric, method, self.zones_layer, val)

        self.but_map_zones.setEnabled(True)

    def update_time(self):
        if self.mapped_stops:
            self.map_stops()

        if self.mapped_lines:
            self.map_lines()

    def enable_line_mapping(self):
        default_style = QgsStyle().defaultStyle()
        for item in [
            self.cob_routes_element,
            self.cob_routes_map_type,
            self.cob_routes_map_info,
            self.cob_routes_color,
            self.sld_route_scale,
            self.but_map_routes,
            self.lbl_scl_line,
        ]:
            item.setEnabled(self.rdo_map_routes.isChecked())

        for cob in [self.cob_routes_map_type, self.cob_routes_map_info, self.cob_routes_color, self.cob_routes_element]:
            cob.clear()
        if self.rdo_map_routes.isChecked():
            self.cob_routes_element.addItems(["Routes"])
            self.cob_routes_map_type.addItems(["Color", "Thickness"])
            self.cob_routes_map_info.addItems(self.sm.list_route_metrics())
            self.cob_routes_color.addItems(list(default_style.colorRampNames()))
        else:
            self.mapped_lines = False
            fldr = join(dirname(dirname(__file__)), "style_loader")
            self.routes_layer.loadNamedStyle(join(fldr, "routes.qml"), True)
            self.routes_layer.triggerRepaint()
        self.allows_colors_line()
        self.iface.mapCanvas().refresh()

    def allows_colors_line(self):
        self.cob_routes_color.setVisible(self.cob_routes_map_type.currentText() == "Color")

    def map_lines(self):
        self.mapped_lines = True
        self.but_map_routes.setEnabled(False)
        if self.line_metric_layer is not None:
            QgsProject.instance().removeMapLayers([self.line_metric_layer.id()])

            for lyr in [self.routes_layer]:
                rem = [lien.joinLayerId() for lien in lyr.vectorJoins()]
                for lien_id in rem:
                    lyr.removeJoin(lien_id)

        element = self.cob_routes_element.currentText()

        minutes_from = self.time_from.time().hour() * 60 + self.time_from.time().minute()
        minutes_to = self.time_to.time().hour() * 60 + self.time_to.time().minute()
        from_time = minutes_from if self.chb_time.isChecked() else None
        to_time = minutes_to if self.chb_time.isChecked() else None

        stops = self.filtered.get("stops", self.stops.stop_id.tolist())
        routes = self.filtered.get("routes", self.routes.route_id.tolist())
        self.line_target_metric = self.cob_routes_map_info.currentText()

        par = {"from_minute": from_time, "to_minute": to_time, "routes": routes, "stops": stops}

        if self.line_target_metric in self.sm.list_route_metrics():
            df = self.sm.route_metrics(**par)

        self.line_metric_layer = layer_from_dataframe(df, f"{element}_metrics")

        lien = QgsVectorLayerJoinInfo()
        lien.setJoinFieldName("route_id")
        lien.setTargetFieldName("route_id")
        lien.setJoinLayerId(self.line_metric_layer.id())
        lien.setUsingMemoryCache(True)
        lien.setJoinLayer(self.line_metric_layer)
        lien.setPrefix("metrics_")
        self.routes_layer.addJoin(lien)

        self.line_map_layer = self.routes_layer
        self.draw_line_styles()
        self.but_map_routes.setEnabled(True)
        self.show_label_lines()

    def draw_line_styles(self):
        fld = f"metrics_{self.line_target_metric}"
        idx = self.line_map_layer.fields().indexFromName(fld)
        max_metric = self.line_map_layer.maximumValue(idx)
        method = self.cob_routes_map_type.currentText()

        val = self.sld_route_scale.value() / 2
        color_ramp_name = "Blues" if method != "Color" else self.cob_routes_color.currentText()
        self.map_ranges(fld, max_metric, method, self.line_map_layer, val, color_ramp_name)

    def map_diagram(self, fld, max_metric, method, layer, val):
        if method == "Pie chart":
            diagram = QgsPieDiagram()
        elif method == "Stacked bars":
            diagram = QgsStackedBarDiagram()

        ds = QgsDiagramSettings()
        dColors = {fld: QtGui.QColor("#5a09a6")}

        ds.categoryColors = dColors.values()
        ds.categoryAttributes = dColors.keys()
        ds.categoryLabels = ds.categoryAttributes
        ds.sizeType = 0  # 0 = Millimeters, 1 = Map Units, 2 = Pixels, 4 = Points, 5 = Inches

        # Set renderer:
        dr = QgsLinearlyInterpolatedDiagramRenderer()
        dr.setLowerValue(0)
        dr.setUpperValue(max_metric or 0)
        dr.setUpperSize(QSizeF(val, val))
        dr.setClassificationField(fld)
        dr.setDiagram(diagram)
        dr.setDiagramSettings(ds)

        layer.setDiagramRenderer(dr)
        dls = QgsDiagramLayerSettings()
        dls.setPlacement(4)
        layer.setDiagramLayerSettings(dls)
        layer.triggerRepaint()

    def map_ranges(self, fld, max_metric, method, layer, val, color_ramp_name):
        intervals = 5
        max_metric = intervals if max_metric is None else max_metric
        values = [ceil(i * (max_metric / intervals)) for i in range(1, intervals + 1)]
        values = [0, 0.000001] + values
        color_ramp = color_ramp_shades(color_ramp_name, intervals)
        ranges = []
        for i in range(intervals):
            myColour = QtGui.QColor("#1e00ff") if method != "Color" else color_ramp[i]
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(myColour)
            symbol.setOpacity(1)

            if i == 0:
                label = f"0/Null ({fld.replace('metrics_', '')})"
            elif i == 1:
                label = f"Up to {values[i + 1]:,.0f}"
            else:
                label = f"{values[i]:,.0f} to {values[i + 1]:,.0f}"

            ranges.append(QgsRendererRange(values[i], values[i + 1], symbol, label))

        sizes = [0, val] if method != "Color" else [val, val]
        renderer = QgsGraduatedSymbolRenderer("", ranges)
        renderer.setSymbolSizes(*sizes)
        renderer.setClassAttribute(f"""coalesce("{fld}", 0)""")

        if method != "Color":
            renderer.setGraduatedMethod(QgsGraduatedSymbolRenderer.GraduatedSize)

        classific_method = QgsApplication.classificationMethodRegistry().method("EqualInterval")
        renderer.setClassificationMethod(classific_method)

        layer.setRenderer(renderer)
        layer.triggerRepaint()
        self.iface.mapCanvas().setExtent(layer.extent())
