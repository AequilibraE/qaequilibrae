from unittest import TestCase
from aequilibrae.transit.gtfs import create_gtfsdb
import os, sys

lib_path = os.path.abspath(os.path.join('..', '..'))
sys.path.append(lib_path)
from data import gtfs_folder, gtfs_db_output


class TestCreate_gtfsdb(TestCase):
    def test_create_database(self):
        self.gtfs = create_gtfsdb()
        self.gtfs.create_database(save_db=gtfs_db_output, overwrite=True, spatialite_enabled=True)

    def test_create_agency_table(self):
        # self.fail()
        pass

    def test_create_route_table(self):
        # self.fail()
        pass

    def test_load_from_folder(self):
        self.gtfs = create_gtfsdb()
        self.gtfs.load_from_folder(gtfs_folder, save_db=gtfs_db_output, overwrite=True)
