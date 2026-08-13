from time import monotonic

from aequilibrae.project import Project
from aequilibrae.project.network.osm.place_getter import placegetter
from aequilibrae.utils.interface.worker_thread import WorkerThread
from qgis.PyQt.QtCore import Qt, pyqtSignal
from shapely.geometry import box

from qaequilibrae.modules.common_tools import reporter

# AequilibraE reports progress once per network element, which is far more often than the
# progress bar can be repainted, so we only relay what the user will actually see
min_seconds_between_updates = 0.1


class ProjectFromOSMProcedure(WorkerThread):
    signal = pyqtSignal(object)

    def __init__(self, parentThread, output_path, bbox=None, place_name=None):
        WorkerThread.__init__(self, parentThread)

        self.output_path = output_path
        self.bbox = bbox
        self.place_name = place_name
        self.project = None
        self.report = []
        self.error = None
        self.__maximum = 0
        self.__last_update = 0.0

    def doWork(self):
        try:
            bbox = self.__area_to_download()
            if bbox is None:
                return

            self.signal.emit(["set_text", self.tr("Creating project")])
            self.project = Project()
            self.project.new(self.output_path)

            self.project.network.signal.connect(self.relay_progress, Qt.ConnectionType.DirectConnection)
            self.project.network.create_from_osm(box(*bbox))

            self.report.append(reporter(f"{self.project.network.count_links():,} links generated"))
            self.report.append(reporter(f"{self.project.network.count_nodes():,} nodes generated"))
        except Exception as e:
            # The dialog is the only one who can talk to the user, so we hand the failure over to it
            self.error = str(e) or e.__class__.__name__
        finally:
            self.signal.emit(["finished"])

    def __area_to_download(self):
        if self.bbox is not None:
            self.report.append(reporter("Chose to download network for canvas area"))
            return self.bbox

        self.report.append(reporter("Chose to download network for place"))
        self.signal.emit(["set_text", self.tr("Establishing area for download")])

        bbox, report = placegetter(self.place_name)
        self.report.extend(report)
        if bbox is None:
            self.error = self.tr("We could not find a reference for place name") + f' "{self.place_name}"'
        return bbox

    def relay_progress(self, val):
        """Relays the progress AequilibraE reports for the download and build stages as our own"""
        if val[0] == "start":
            # Zero whenever AequilibraE iterates over something it cannot take the length of,
            # which is the case for the busiest stage of all - the one reporting once per link
            self.__maximum = val[1]
            # A new stage starts on the screen right away, however recently the last one ended
            self.__last_update = 0.0
        elif val[0] == "update":
            now = monotonic()
            # The update completing a stage always goes through, so the bar does not stop short
            completes_stage = 0 < self.__maximum <= val[1]
            if not completes_stage and now - self.__last_update < min_seconds_between_updates:
                return
            self.__last_update = now
        elif val[0] == "finished":
            # Only means the download or the build is over, not the whole procedure
            return
        self.signal.emit(val)
