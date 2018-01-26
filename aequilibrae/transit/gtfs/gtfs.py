import numpy as np
import os
from collections import OrderedDict
import codecs
from agency import Agency
from calendar_dates import CalendarDates
from stop import Stop
from route import Route


class GTFS:
    """
     Reader for GTFS (from https://developers.google.com/transit/gtfs/reference/)

     .

     Objective
     _________
     To provide a memory container for GTFS that can be:
        * Passed to transit assignment algorithms in memory
        * Edited and saved back to disk
        * Displayed in a GIS environment
    """

    def __init__(self):
        self.source_folder = None
        self.agency = Agency()
        self.num_routes = None
        self.routes = {}
        self.stops = {}
        self.calendar_dates = {}
        self.schedule_exceptions = None
    
    def load(self, path_to_folder):
        self.source_folder = path_to_folder
        self.load_stops()
        self.load_agency()
        self.load_calendar_dates()
        self.load_routes()

    def load_calendar_dates(self):
        agency_file = os.path.join(self.source_folder, 'calendar_dates.txt')
        if not os.path.isfile(agency_file):
            return

        data = self.open(agency_file)
        all_exceptions = []
        for i in range(data.shape[0]):
            cd = CalendarDates()
            # Required fields
            cd.service_id = data['service_id'][i]
            cd.date = data['date'][i]
            cd.exception_type = data['exception_type'][i]
            all_exceptions.append(cd.service_id)
            self.calendar_dates[i] = cd
        self.schedule_exceptions = set(all_exceptions)
        del all_exceptions
        del data

    def load_agency(self):
        agency_file = os.path.join(self.source_folder, 'agency.txt')
        data = self.open(agency_file)
        self.agency.email = data['agency_id']
        self.agency.name = data['agency_name']
        self.agency.url = data['agency_url']
        self.agency.timezone = data['agency_timezone']
        self.agency.lang = data['agency_lang']
        self.agency.phone = data['agency_phone']
        del(data)

    def load_stops(self):
        stops_file = os.path.join(self.source_folder, 'stops.txt')
        data = self.open(stops_file)

        # Iterate over all the stops and puts them in the stops dictionary
        for i in range(data.shape[0]):
            stop = Stop()
            # Required fields
            stop.id = data['stop_id'][i]
            stop.name = data['stop_name'][i]
            stop.lat = data['stop_lat'][i]
            stop.lon = data['stop_lon'][i]

            # optional fields
            available_fields = data.dtype.names
            if 'stop_code' in available_fields: stop.code = data['stop_code'][i]
            if 'stop_desc' in available_fields: stop.desc = data['stop_desc'][i]
            if 'zone_id' in available_fields: stop.zone_id = data['zone_id'][i]
            if 'stop_url' in available_fields: stop.url = data['stop_url'][i]
            if 'zone_id' in available_fields: stop.zone_id = data['zone_id'][i]
            if 'location_type' in available_fields: stop.location_type = data['location_type'][i]
            if 'parent_station' in available_fields: stop.parent_station = data['parent_station'][i]
            if 'timezone' in available_fields: stop.timezone = data['timezone'][i]
            if 'wheelchair_boarding' in available_fields: stop.wheelchair_boarding = data['wheelchair_boarding'][i]

            self.stops[stop.id] = stop
        del(data)

    def load_routes(self):
        routes_file = os.path.join(self.source_folder, 'routes.txt')
        data = self.open(routes_file)

        # Iterate over all the stops and puts them in the stops dictionary
        for i in range(data.shape[0]):
            r = Route()
            # Required fields
            r.id = data['route_id'][i]
            r.short_name = data['route_short_name'][i]
            r.long_name = data['route_long_name'][i]
            r.type = data['route_type'][i]

            # optional fields
            available_fields = data.dtype.names
            if 'agency_id' in available_fields: r.agency_id = data['agency_id'][i]
            if 'route_desc' in available_fields: r.desc = data['route_desc'][i]
            if 'route_url' in available_fields: r.url = data['route_url'][i]
            if 'route_color' in available_fields: r.color = data['route_color'][i]
            if 'route_text_color' in available_fields: r.text_color = data['route_text_color'][i]
            if 'route_sort_order' in available_fields: r.sort_order = data['route_sort_order'][i]
            self.routes[r.id] = r

        del data

    def load_trips(self):
        pass

    @staticmethod
    def open(file_name):
        # Read the stops and cleans the names of the columns
        data = np.genfromtxt(file_name, delimiter=',', names=True, dtype=None,)
        content = [str(unicode(x.strip(codecs.BOM_UTF8), 'utf-8')) for x in data.dtype.names]
        data.dtype.names = content
        return data
        

    
    

        