from typing import List, Optional

import pandas as pd

from aequilibrae.project.database_connection import database_connection
from aequilibrae.utils.db_utils import read_and_close


class SupplyMetrics:
    """Loads all data required for the computation of supply metrics and
    computes unfiltered metrics at instantiation.

    The behavior of time filtering consists of setting to instant zero
    whenever *from_time* is not provided and the end of simulation when
    *to_time* is not provided"""

    def __init__(self, path: None):
        """
        :param supply_file: Path to the supply file we want to compute metrics for
        """

        rt_sql = """Select route_id, route, agency_id, route_type, seated_capacity s_capacity, total_capacity t_capacity from routes"""

        patt_sql = """Select pattern_id, route_id, seated_capacity s_capacity, total_capacity t_capacity from routes"""

        stop_sql = (
            f"""Select stop_id, stop, name stop_name, agency_id, route_type, transit_fare_zone zone_id from stops"""
        )

        stop_pat_sql = """Select pattern_id, cast(from_stop as text) stop_id from route_links
                        UNION ALL
                        Select pattern_id, cast(to_stop as text) stop_id from route_links"""

        trip_sql = """select trip_id, pattern_id from trips"""

        trp_sch_sql = """Select trip_id, seq stop_order, arrival/60 arrival, departure/60 departure
                        from trips_schedule"""

        trp_pat_lnk_sql = """select pattern_id, seq stop_order, cast(from_stop as text) from_stop, 
                             cast(to_stop as text) to_stop from route_links"""

        connection = database_connection("transit") if path == None else path
        with read_and_close(connection) as conn:
            self.__raw_routes = pd.read_sql(rt_sql, conn).fillna(0)
            self.__raw_patterns = pd.read_sql(patt_sql, conn).fillna(0)
            self.__raw_stops = pd.read_sql(stop_sql, conn)

            self.__raw_stop_pattern = pd.read_sql(stop_pat_sql, conn).drop_duplicates()
            self.__raw_stop_pattern = self.__raw_stop_pattern.merge(self.__raw_stops, on="stop_id", how="left")
            self.__raw_stop_pattern.fillna(0, inplace=True)

            self.__raw_trips = pd.read_sql(trip_sql, conn).fillna(0)
            self.__raw_trips = self.__raw_trips.merge(
                self.__raw_patterns[["pattern_id", "route_id", "s_capacity", "t_capacity"]], on="pattern_id"
            )

            self.__trip_schedule = pd.read_sql(trp_sch_sql, conn)

            self.__pattern_links = pd.read_sql(trp_pat_lnk_sql, conn)
            cols = ["pattern_id", "stop_order", "from_node", "to_node"]
            self.__pattern_links.columns = cols

        self.__distribute_time_stamps()
        self.__compute_stop_order()
        self.__correct_capacities()

        self.__stops = self.__raw_stops.copy(True)
        self._stop_pattern = self.__raw_stop_pattern.copy(True)

        self.__routes = self.__compute_route_metrics(self.__raw_trips, self.__raw_routes)
        self.__patterns = self.__compute_pattern_metrics(self.__raw_trips, self.__raw_patterns)
        self.__stops = self.__compute_stop_metrics(self.__patterns, self.__raw_stops)
        self.__zones = self.__compute_zones_metrics(self.__patterns)

    def stop_metrics(
        self,
        from_minute: Optional[int] = None,
        to_minute: Optional[int] = None,
        routes: Optional[List[int]] = None,
        patterns: Optional[List[int]] = None,
        stops: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Returns a dataframe with all supported supply metrics for stops
            Capacities correspond to the sum of the capacities of all vehicles
            for all trips that went through the stop.

            :param from_minute: (`Optional`) Start of time window to compute metrics for
            :param to_minute: (`Optional`) End of time window to compute metrics for
            :param patterns: (`Optional`) List of patterns to consider
            :param routes: (`Optional`) List of routes to consider
            :param stops: (`Optional`) List of stops to consider

        :return: stop_metrics (`pd.DataFrame`)

        """
        if all(x is None for x in [from_minute, to_minute, routes, patterns, stops]):
            return self.__stops.copy(True)

        # Set the time for the interval we want
        from_minute, to_minute = self.__time_interval(from_minute, to_minute)

        trips = self.__filter_trips(from_minute, to_minute, routes, patterns, stops)

        pats = self.__compute_pattern_metrics(trips, self.__raw_patterns)
        stop_metrics = self.__compute_stop_metrics(pats, self.__raw_stops)
        return stop_metrics if stops is None else stop_metrics[stop_metrics.stop_id.isin(stops)]

    def pattern_metrics(
        self,
        from_minute: Optional[int] = None,
        to_minute: Optional[int] = None,
        patterns: Optional[List[int]] = None,
        routes: Optional[List[int]] = None,
        stops: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Returns a dataframe with all supported supply metrics for Patterns
        Capacities correspond to the sum of the capacities of all vehicles
        for all trips for each pattern

        :param from_minute: (`Optional`) Start of time window to compute metrics for
        :param to_minute: (`Optional`) End of time window to compute metrics for
        :param patterns: (`Optional`) List of patterns to consider
        :param routes: (`Optional`) List of routes to consider
        :param stops: (`Optional`) List of stops to consider

        :return: pattern_metrics (`pd.DataFrame`)

        """
        if all(x is None for x in [from_minute, to_minute, routes, patterns, stops]):
            return self.__patterns.copy(True)

        # Set the time for the interval we want
        from_minute, to_minute = self.__time_interval(from_minute, to_minute)

        trips = self.__filter_trips(from_minute, to_minute, routes, patterns, stops)
        patt_metric = self.__compute_pattern_metrics(trips, self.__raw_patterns)
        return patt_metric if patterns is None else patt_metric[patt_metric.pattern_id.isin(patterns)]

    def route_metrics(
        self,
        from_minute: Optional[int] = None,
        to_minute: Optional[int] = None,
        patterns: Optional[List[int]] = None,
        routes: Optional[List[int]] = None,
        stops: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Returns a dataframe with all supported supply metrics for Routes
        Capacities correspond to the sum of the capacities of all vehicles
        for all trips fort each route

        :param from_minute: (`Optional`) Start of time window to compute metrics for
        :param to_minute: (`Optional`) End of time window to compute metrics for
        :param patterns: (`Optional`) List of patterns to consider
        :param routes: (`Optional`) List of routes to consider
        :param stops: (`Optional`) List of stops to consider

        :return: route_metrics (`pd.DataFrame`)
        """

        if all(x is None for x in [from_minute, to_minute, routes, patterns, stops]):
            return self.__routes.copy(True)

        # Set the time for the interval we want
        from_minute, to_minute = self.__time_interval(from_minute, to_minute)
        trips = self.__filter_trips(from_minute, to_minute, routes, patterns, stops)
        route_metrics = self.__compute_route_metrics(trips, self.__raw_routes)
        return route_metrics if routes is None else route_metrics[route_metrics.route_id.isin(routes)]

    def zone_metrics(
        self,
        from_minute: Optional[int] = None,
        to_minute: Optional[int] = None,
        routes: Optional[List[int]] = None,
        patterns: Optional[List[int]] = None,
        stops: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """Computes metrics for all stop within each zone. Allows constraining to a given
        time interval, set of routes, set of patterns and/or transit agency.

            All parameters are optional.

        :param from_minute: Start of the interval for computation. Zero if not provided
        :param to_minute: End of the interval for computation. Maximum time from the dataset if not provided
        :param stops: List of stops we want to compute data for
        :param patterns: List of pattern_id to consider in the computation
        :param routes: List of route_id to consider in the computation
        :return: Statistics DataFrame
        """
        if all(x is None for x in [from_minute, to_minute, routes, patterns, stops]):
            return self.__zones.copy(True)

        # Set the time for the interval we want
        from_minute, to_minute = self.__time_interval(from_minute, to_minute)
        trips = self.__filter_trips(from_minute, to_minute, routes, patterns, stops)

        patt_metric = self.__compute_pattern_metrics(trips, self.__raw_patterns)
        zone_metrics = self.__compute_zones_metrics(patt_metric)
        return zone_metrics

    @staticmethod
    def list_stop_metrics():
        """Helper method to identify metrics available for transit stops
            Capacities correspond to the sum of the capacities of all vehicles
            for all trips that went through the stop

        :return: Lists of metrics available for stops
        """
        return ["routes", "patterns", "trips", "seated_capacity", "total_capacity"]

    @staticmethod
    def list_pattern_metrics():
        """Helper method to identify metrics available for transit patterns.
           Capacities correspond to the sum of the capacities of all vehicles
           for all trips for each pattern

        :return: Lists of metrics available for patterns
        """
        return ["trips", "seated_capacity", "total_capacity"]

    @staticmethod
    def list_route_metrics():
        """Helper method to identify metrics available for transit routes
            Capacities correspond to the sum of the capacities of all vehicles
            for all trips for each route

        :return: Lists of metrics available for routes
        """
        return ["trips", "seated_capacity", "total_capacity"]

    @staticmethod
    def list_zone_metrics():
        """Returns list of metrics available for traffic analysis zones

        :return: Lists of metrics available for zones
        """
        return ["routes", "patterns", "stops", "trips"]

    def __time_interval(self, from_minute, to_minute):
        from_minute = 0 if from_minute is None and to_minute is not None else from_minute
        to_minute = self.__trip_schedule.departure.max() if to_minute is None and from_minute is not None else to_minute
        return from_minute, to_minute

    def __filter_trips(self, from_minute, to_minute, routes, patterns, stops) -> pd.DataFrame:
        trips = self.__raw_trips
        if None not in [from_minute, to_minute]:
            crit1 = (from_minute < trips.begin_trip) & (trips.begin_trip < to_minute)
            crit2 = (from_minute < trips.end_trip) & (trips.end_trip < to_minute)
            crit3 = (from_minute < trips.begin_trip) & (to_minute > trips.end_trip)
            trips = trips[crit1 | crit2 | crit3]

        patts = self.__raw_patterns

        if stops is not None:
            filtered = self.__raw_stop_pattern[self.__raw_stop_pattern.stop_id.isin(stops)]
            patts = patts[patts.pattern_id.isin(filtered.pattern_id)]

        if patterns is not None:
            patts = patts[patts.pattern_id.isin(patterns)]
            trips = trips[trips.pattern_id.isin(patterns)]

        if routes is not None:
            patts = patts[patts.route_id.isin(routes)]
            trips = trips[trips.pattern_id.isin(patts.pattern_id)]

        return trips

    def __correct_capacities(self):
        """Brings capacities from patterns down to patterns and then trips when those are not available"""
        for field in ["s_capacity", "t_capacity"]:
            route_cap = self.__raw_routes[["route_id", field]]
            route_cap.columns = ["route_id", "route_cap"]
            self.__raw_patterns = self.__raw_patterns.merge(route_cap, on="route_id", how="left")
            self.__raw_patterns.fillna(0, inplace=True)
            self.__raw_patterns.loc[self.__raw_patterns[field] == 0, field] = self.__raw_patterns.route_cap
            self.__raw_patterns.drop(columns="route_cap", inplace=True)

            patt_cap = self.__raw_patterns[["pattern_id", field]]
            patt_cap.columns = ["pattern_id", "patt_cap"]
            self.__raw_trips = self.__raw_trips.merge(patt_cap, on="pattern_id", how="left")
            self.__raw_trips.fillna(0, inplace=True)
            self.__raw_trips.loc[self.__raw_trips[field] == 0, field] = self.__raw_trips.patt_cap
            self.__raw_trips.drop(columns="patt_cap", inplace=True)

    def __distribute_time_stamps(self):
        # Distribute mins and max time stamps for all elements
        trps = (
            self.__trip_schedule.groupby(["trip_id"])
            .agg(begin_trip=("arrival", "min"), end_trip=("departure", "max"))
            .reset_index()
        )
        self.__raw_trips = self.__raw_trips.merge(trps, on="trip_id", how="left")
        self.__raw_trips.fillna(0, inplace=True)

        patts = (
            self.__raw_trips.groupby(["pattern_id"])
            .agg(first_departure=("begin_trip", "min"), last_arrival=("end_trip", "max"))
            .reset_index()
        )

        self.__raw_patterns = self.__raw_patterns.merge(patts, on="pattern_id", how="left")
        self.__raw_patterns.fillna(0, inplace=True)

        rts = (
            self.__raw_patterns.groupby(["route_id"])
            .agg(first_departure=("first_departure", "min"), last_arrival=("last_arrival", "max"))
            .reset_index()
        )

        self.__raw_routes = self.__raw_routes.merge(rts, on="route_id", how="left")
        self.__raw_routes.fillna(0, inplace=True)

    def __compute_stop_order(self):
        aux = self.__pattern_links.groupby("pattern_id").max()[["stop_order"]].reset_index()
        aux = aux.merge(self.__pattern_links, on=["pattern_id", "stop_order"], how="left")
        aux = aux[["pattern_id", "stop_order", "to_node"]]
        aux.loc[:, "stop_order"] += 1
        aux.columns = ["pattern_id", "stop_order", "stop_id"]

        stop_order = self.__pattern_links[["pattern_id", "stop_order", "from_node"]]
        stop_order.columns = ["pattern_id", "stop_order", "stop_id"]
        stop_order = pd.concat([stop_order, aux])

        self.__raw_stop_pattern = self.__raw_stop_pattern.merge(stop_order, on=["pattern_id", "stop_id"], how="left")
        self.__raw_stop_pattern.fillna(0, inplace=True)

    def __compute_route_metrics(self, trips: pd.DataFrame, routes: pd.DataFrame) -> pd.DataFrame:
        trps = trips.assign(trip_count=1)

        trps = trps.groupby(["route_id"]).agg(
            trips=("trip_count", "sum"),
            seated_capacity=("s_capacity", "sum"),
            total_capacity=("t_capacity", "sum"),
            distinct_patterns=("pattern_id", "nunique"),
        )

        trps.reset_index(inplace=True)

        routes = routes.merge(trps, on="route_id", how="left")
        routes.drop(columns=["s_capacity", "t_capacity"], inplace=True)
        routes.fillna(0, inplace=True)
        routes = routes.drop_duplicates().reset_index(drop=True)
        return routes

    def __compute_pattern_metrics(self, trips: pd.DataFrame, patterns: pd.DataFrame) -> pd.DataFrame:
        trps = trips.assign(trip_count=1)
        trps = trps.groupby(["pattern_id"]).sum()[["trip_count", "s_capacity", "t_capacity"]]

        trps.columns = [
            "trips",
            "seated_capacity",
            "total_capacity",
        ]  # type: ignore # Recommended Pandas behaviour that should not trigger typing
        trps.reset_index(inplace=True)

        patterns = patterns.merge(trps, on="pattern_id", how="left")
        patterns.drop(columns=["s_capacity", "t_capacity"], inplace=True)
        patterns.fillna(0, inplace=True)
        patterns = patterns.drop_duplicates().reset_index(drop=True)
        return patterns.astype("int64")

    def __compute_stop_metrics(self, patterns: pd.DataFrame, stops: pd.DataFrame) -> pd.DataFrame:
        smetric = self.__raw_stop_pattern.merge(patterns, on="pattern_id", how="right")
        smetric = (
            smetric.groupby("stop_id")
            .agg(
                trips=("trips", "sum"),
                seated_capacity=("seated_capacity", "sum"),
                total_capacity=("total_capacity", "sum"),
                patterns=("pattern_id", "nunique"),
                routes=("route_id", "nunique"),
            )
            .reset_index()
        )

        return stops.merge(smetric, on="stop_id")

    def __compute_zones_metrics(self, patterns: pd.DataFrame) -> pd.DataFrame:

        zmetric = self.__raw_stop_pattern.merge(patterns, on="pattern_id", how="right")
        zmetric = (
            zmetric.groupby("zone_id")
            .agg(
                routes=("route_id", "nunique"),
                patterns=("pattern_id", "nunique"),
                stops=("stop_id", "nunique"),
                trips=("trips", "sum"),
            )
            .reset_index()
        )

        return zmetric
