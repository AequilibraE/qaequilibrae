"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Transportation graph class
 Purpose:    Implement a standard graph class to support all network computation

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camargo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    June/05/2015
 Updated:    25/02/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

import numpy as np
import csv
import cPickle
from datetime import datetime
import uuid

VERSION = "0.3.5"


'''description: Description of the graph (OPTIONAL)
    num_links: Number of directed links in the graph
    num_nodes: number of nodes in the graph

    nodes_fs: Numpy array with the indices of each node in the forward star.
                       DIMENSION: # Of nodes +1
                       TYPE: numpy.int32

    network:  Numpy record array with arbitrary number of fields (and titles of columns) corresponding to each link
                       DIMENSION: # Of links
                       TYPE: mixed

    cost:     Name of the field to be minimized.
                       TYPE: String

    skims:    Name of the skim fields.
                       TYPE: String list  (OPTIONAL)
'''


class Graph:
    def __init__(self):
        """
        @type graph: Numpy record array
        """

        self.required_default_fields = ['link_id', 'a_node', 'b_node', 'direction']
        self.other_fields = ''
        self.date = str(datetime.now())

        self.description = 'No description added so far'

        self.num_links = -1
        self.num_nodes = -1
        self.network = False  # This method will hold ALL information on the network
        self.graph = False  # This method will hold an array with ALL fields in the graph.

        # These are the fields actually used in computing paths
        self.fs = False      # This method will hold the forward star for the graph
        self.b_node = False  # b node for each directed link
        self.cost = None    # This array holds the values being used in the shortest path routine
        self.skims = False   # 2-D Array with the fields to be computed as skims
        self.skim_fields = False # List of skim fields to be used in computation
        self.cost_field = False # Name of the cost field
        self.ids = False     # 1-D Array with link IDs (sequence from 0 to N-1)

        self.block_centroid_flows = False
        self.penalty_through_centroids = np.inf

        self.centroids = 0  # ID of the highest node in the network that is a centroid

        self.status = 'NO network loaded'
        self.network_ok = False
        self.type_loaded = False
        self.__version__ = VERSION

        # Randomly generate a unique Graph ID randomly
        self.__id__ = uuid.uuid4().hex
        self.__source__ = None    # Name of the file that originated the graph

        # In case the graph is generated in QGIS, it is useful to have the name of the layer and fields that originated
        # it
        self.__field_name__ = None
        self.__layer_name__ = None

    # Create a graph from a shapefile. To be upgraded to ANY geographic file in the future
    def create_from_geography(self, geo_file, id_field, dir_field, cost_field, skim_fields = [], anode="A_NODE", bnode="B_NODE"):
        #try:
        import shapefile
        #try:
        error = None
        geo_file_records = shapefile.Reader(geo_file)
        records = geo_file_records.records()

        a = []
        def find_field_index(fields, field_name):
            for i, f in enumerate(fields):
                if f[0] == field_name:
                    return i - 1
            return -1

        # collect the fields in the network
        check_titles = [id_field, dir_field, anode, bnode, cost_field]
        id_field = find_field_index(geo_file_records.fields, id_field)
        dir_field = find_field_index(geo_file_records.fields, dir_field)
        cost_field = find_field_index(geo_file_records.fields, cost_field)
        anode = find_field_index(geo_file_records.fields, anode)
        bnode = find_field_index(geo_file_records.fields, bnode)

        # Appends all fields to the list of fields to be used
        all_types = [np.int32, np.int32, np.int32, np.float64, np.float64, np.int8]
        all_titles = ['link_id', 'a_node', 'b_node', 'length_ab', 'length_ba', 'direction']
        check_fields = [id_field, dir_field, anode, bnode, cost_field]
        types_to_check = [int, int, int, int, float]

        # Loads the skim index fields
        dict_field = {}
        for k in skim_fields:
            skim_index = find_field_index(geo_file_records.fields, k)
            check_fields.append(skim_index)
            check_titles.append(k)
            types_to_check.append(float)

            all_types.append(np.float64)
            all_types.append(np.float64)
            all_titles.append((k + '_ab').encode('ascii', 'ignore'))
            all_titles.append((k + '_ba').encode('ascii', 'ignore'))
            dict_field[k + '_ab'] = skim_index
            dict_field[k + '_ba'] = skim_index

        dt = [(t, d) for t, d in zip(all_titles, all_types)]

        # Check ID uniqueness and if there are any non-valid values
        all_ids = []
        for feat in records:
            for i, j in enumerate(check_fields):
                k = feat[j]
                if not isinstance(k, types_to_check[i]):
                    error = check_titles[i], "field has wrong type or empty values"
                    break
            all_ids.append(feat[check_fields[0]])
            if error is not None:
                break

        if error is None:
            # Checking uniqueness
            all_ids = np.array(all_ids, np.int)
            y = np.bincount(all_ids)
            if np.max(y) > 1:
                error = 'IDs are not unique.'

        if error is None:
            data = []

            for feat in records:
                line = []
                line.append(feat[id_field])
                line.append(feat[anode])
                line.append(feat[bnode])
                line.append(feat[cost_field])
                line.append(feat[cost_field])
                line.append(feat[dir_field])

                # We append the skims now
                for k in all_titles:
                    if k in dict_field:
                        line.append(feat[dict_field[k]])
                data.append(line)

            network = np.asarray(data)
            del data

            self.network = np.zeros(network.shape[0], dtype=dt)
            for k, t in enumerate(dt):
                self.network[t[0]] = network[:, k].astype(t[1])
            del network

            self.type_loaded = 'SHAPEFILE'
            self.status = 'OK'
            self.network_ok = True
            self.prepare_graph()
            self.__source__ = geo_file
            self.__field_name__ = None
            self.__layer_name__ = None
            # except:
            #     print "Unidentified error occurred"
            #     print "Try creating a graph using AequilibraE's GUI in QGIS"
        # except:
        #     print "No Pyshp module available"

    # Procedure to load csv network from disk
    def load_network_from_csv(self, netw):
        self.network_ok = False
        self.type_loaded = 'NET'

        with open(netw, 'r') as n:
            net_iter = csv.reader(n,
                                  delimiter=',',
                                  quotechar='"')

            data = [data for data in net_iter]

        all_titles = [x.lower() for x in data[0]]
        data.pop(0)

        # Check if all dual fields are provided
        for i in all_titles:
            if i not in self.required_default_fields:
                if i[-3:] == '_ab':
                    f = False
                    for j in all_titles:
                        if i[0:-3] + '_ba' == j:
                            f = True
                    if not f:
                        self.status = 'Dual field for ' + i + ' was not provided'
                        raise ValueError(self.status)
                elif i[-3:] == '_ba':
                    f = False
                    for j in all_titles:
                        if i[0:-3] + '_ab' == j:
                            f = True
                    if not f:
                        self.status = 'Dual field for ' + i + ' was not provided'
                        raise ValueError(self.status)
                else:
                    raise ValueError('Non permitted field ' + i + ' in the network')

        # determining types.  We analyze the first ten links of the network to determine type of each field
        all_types = []
        for k in range(len(data[0])):
            all_types.append(long)
        for i in range(10):
            for k in range(len(data[i])):
                all_types[k] = self.__determine_types__(data[i][k], all_types[k])

        for k in range(len(all_types)):
            if all_types[k] == long:
                all_types[k] = np.int32
            elif all_types[k] == float:
                all_types[k] = np.float64
            elif all_types[k] == str:
                all_types[k] = np.dtype('a256')

        dt = [(t, d) for t, d in zip(all_titles, all_types)]
        network = np.asarray(data)
        del data
        self.network = np.zeros(network.shape[0], dtype=dt)
        for k, t in enumerate(dt):
            self.network[t[0]] = network[:, k].astype(t[1])
        del network

        self.type_loaded = 'NETWORK'
        self.status = 'Network Loaded'

        if self.status != 'Network Loaded':
            raise ValueError(self.status)

        # We check for errors
        self.__network_error_checking__()
        if self.status != 'Network Loaded':
            raise ValueError(self.status)
        else:
            self.network_ok = True
            self.status = 'OK'

    def load_graph_from_csv(self, netw):
        self.add_single_field('id')
        self.network_ok = False
        self.type_loaded = 'GRAPH'

        with open(netw, 'r') as n:
            net_iter = csv.reader(n,
                                  delimiter=',',
                                  quotechar='"')
            data = [data for data in net_iter]

        all_titles = [x.lower() for x in data[0]]
        data.pop(0)

        # Check if all dual fields are provided
        for i in all_titles:
            if i not in self.required_default_fields:
                raise ValueError('Non permitted field ' + i + ' in the network')

        # determining types.  We analyze the first ten links of the network to determine type of each field
        all_types = []
        for k in range(len(data[0])):
            all_types.append(long)
        for i in range(10):
            for k in range(len(data[i])):
                all_types[k] = self.__determine_types__(data[i][k], all_types[k])

        for k in range(len(all_types)):
            if all_types[k] == long:
                all_types[k] = np.int32
            elif all_types[k] == float:
                all_types[k] = np.float64
            elif all_types[k] == str:
                all_types[k] = np.dtype('a256')

        dt = [(t, d) for t, d in zip(all_titles, all_types)]
        network = np.asarray(data)
        del data
        self.graph = np.zeros(network.shape[0], dtype=dt)
        for k, t in enumerate(dt):
            self.graph[t[0]] = network[:, k].astype(t[1])
        del network

        self.type_loaded = 'GRAPH'

        # We check for errors
        self.__graph_error_checking__()
        if self.status != 'graph loaded':
            raise ValueError(self.status)
        else:
            self.network_ok = True

        self.num_links = self.graph.shape[0]
        self.num_nodes = max(np.max(self.graph['a_node']), np.max(self.graph['b_node']))

        ind = np.lexsort((self.graph['b_node'], self.graph['a_node']))
        self.graph = self.graph[ind]

        self.fs = np.zeros(self.num_nodes +2, dtype=np.int32)

        a = self.graph['a_node'][0]
        p = 0
        k = 0
        for i in xrange(1, self.num_links):
            if a != self.graph['a_node'][i]:
                for j in xrange(p, self.graph['a_node'][i]):
                    self.fs[j + 1] = k
                p = a
                a = self.graph['a_node'][i]
                k = i

        for j in xrange(p, self.graph['a_node'][i-1]):
            self.fs[j + 1] = k

        self.fs[-1] = self.num_links
        self.ids = self.graph['id']
        self.b_node = self.graph['b_node']

    def prepare_graph(self):
        if not self.network_ok:
            raise ValueError('Network not yet properly loaded')
        else:
            all_titles = self.network.dtype.names

            if self.status == 'OK':
                negs = self.network[self.network['direction'] == -1]
                poss = self.network[self.network['direction'] == 1]
                zers = self.network[self.network['direction'] == 0]

                self.num_links = negs.shape[0] + poss.shape[0]
                self.num_links += zers.shape[0] * 2

                dtype = [('link_id', np.int32),
                         ('a_node', np.int32),
                         ('b_node', np.int32),
                         ('direction', np.int8),
                         ('id', np.int32)]

                for i in all_titles:
                    if i not in self.required_default_fields and i[0:-3] not in self.required_default_fields:
                        if i[-3:] != '_ab':
                            dtype.append((i[0:-3], self.network[i].dtype))

                self.graph = np.zeros(self.num_links, dtype=dtype)

                a1 = negs.shape[0]
                a2 = a1 + poss.shape[0]
                a3 = a2 + zers.shape[0]
                a4 = a3 + zers.shape[0]

                for i in all_titles:
                    if i == 'link_id':
                        self.graph[i][0:a1] = negs[i]
                        self.graph[i][a1:a2] = poss[i]
                        self.graph[i][a2:a3] = zers[i]
                        self.graph[i][a3:a4] = zers[i]

                    elif i == 'a_node':
                        self.graph[i][0:a1] = negs['b_node']
                        self.graph[i][a1:a2] = poss[i]
                        self.graph[i][a2:a3] = zers['b_node']
                        self.graph[i][a3:a4] = zers[i]

                    elif i == 'b_node':
                        self.graph[i][0:a1] = negs['a_node']
                        self.graph[i][a1:a2] = poss[i]
                        self.graph[i][a2:a3] = zers['a_node']
                        self.graph[i][a3:a4] = zers[i]

                    elif i == 'direction':
                        self.graph[i][0:a1] = -1
                        self.graph[i][a1:a2] = 1
                        self.graph[i][a2:a3] = -1
                        self.graph[i][a3:a4] = 1
                    else:
                        if i[-3:] == '_ab':
                            self.graph[i[0:-3]][0:a1] = negs[i[0:-3] + '_ba']
                            self.graph[i[0:-3]][a1:a2] = poss[i]
                            self.graph[i[0:-3]][a2:a3] = zers[i[0:-3] + '_ba']
                            self.graph[i[0:-3]][a3:a4] = zers[i]

                ind = np.lexsort((self.graph['b_node'], self.graph['a_node']))
                self.graph = self.graph[ind]
                del ind

                self.graph['id'] = np.arange(self.num_links)
                self.num_nodes = max(np.max(self.graph['a_node']), np.max(self.graph['b_node']))
                self.fs = np.zeros(self.num_nodes + 2, dtype=np.int32)  # NOT SURE IF IT SHOULD BE +1 OR +2. SINCE IT IS WORKING AND DOES NOT AFFECT RESULTS, LEAVING AS +2 FOR NOW

                a = self.graph['a_node'][0]
                p = 0
                k = 0
                for i in xrange(1, self.num_links):
                    if a != self.graph['a_node'][i]:
                        for j in xrange(p, self.graph['a_node'][i]):
                            self.fs[j + 1] = k
                        p = a
                        a = self.graph['a_node'][i]
                        k = i

                self.fs[self.num_nodes +1] = self.graph.shape[0]  # IF ENDS UP BEING +2 IN THE COMMENT ON LINE 299, THEN THIS LINE BECOMES IRRELEVANT
                self.ids = self.graph['id']
                self.b_node = self.graph['b_node']

    # We set which are the fields that are going to be minimized in this file
    def set_graph(self, centroids=None, cost_field=None, skim_fields=False, block_centroid_flows=False):
        """
        :type self: object
        :type skim_fields: list of fields for skims
        """
        if centroids is not None:
            self.centroids = centroids
        self.block_centroid_flows = block_centroid_flows

        if cost_field is not None:
            self.cost_field = cost_field
            if self.graph[cost_field].dtype == np.float64:
                self.cost = self.graph[cost_field]
            else:
                print 'Cost field with wrong type. Converting to float64'
                self.cost = self.graph[cost_field].astype(np.float64)

        skim_fields = []
        if self.cost is not None:
            if not skim_fields:
                skim_fields = [self.cost_field, self.cost_field]
            else:
                s = [self.cost_field]
                for i in skim_fields:
                    s.append(i)
                skim_fields = s
        else:
            if skim_fields:
                print 'Before setting skims, you need to set the cost field'

        t = False
        print skim_fields
        for i in skim_fields:
            if self.graph[i].dtype != np.float64:
                t = True

        self.skims = np.zeros((self.num_links, len(skim_fields)), np.float64)

        if t:
            print 'Some skim field with wrong type. Converting to float64'
            for i, j in enumerate(skim_fields):
                self.skims[:, i] = self.graph[j].astype(np.float64)
        else:
            for i, j in enumerate(skim_fields):
                self.skims[:, i] = self.graph[j]
        self.skim_fields = skim_fields

    # Procedure to pickle graph and save to disk
    def save_to_disk(self, filename):
        mygraph = {}
        mygraph['description'] = self.description
        mygraph['num_links'] = self.num_links
        mygraph['num_nodes'] = self.num_nodes
        mygraph['network'] = self.network
        mygraph['graph'] = self.graph
        mygraph['fs'] = self.fs
        mygraph['b_node'] = self.b_node
        mygraph['cost'] = self.cost
        mygraph['skims'] = self.skims
        mygraph['ids'] = self.ids
        mygraph['block_centroid_flows'] = self.block_centroid_flows
        mygraph['centroids'] = self.centroids
        mygraph['status'] = self.status
        mygraph['network_ok'] = self.network_ok
        mygraph['type_loaded'] = self.type_loaded

        cPickle.dump(mygraph, open(filename, 'wb'))

    def load_from_disk(self, filename):
        mygraph = cPickle.load(open(filename, 'rb'))
        self.description = mygraph['description']
        self.num_links = mygraph['num_links']
        self.num_nodes = mygraph['num_nodes']
        self.network = mygraph['network']
        self.graph = mygraph['graph']
        self.fs = mygraph['fs']
        self.b_node = mygraph['b_node']
        self.cost = mygraph['cost']
        self.skims = mygraph['skims']
        self.ids = mygraph['ids']
        self.block_centroid_flows = mygraph['block_centroid_flows']
        self.centroids = mygraph['centroids']
        self.status = mygraph['status']
        self.network_ok = mygraph['network_ok']
        self.type_loaded = mygraph['type_loaded']
        del mygraph

    # We return the list of the fields that are the same for both directions to their initial states
    def reset_single_fields(self):
        self.required_default_fields = ['link_id', 'a_node', 'b_node', 'direction', 'length']

    # We add a new fields that is the same for both directions
    def add_single_field(self, new_field):
        if new_field not in self.required_default_fields:
            self.required_default_fields.append(new_field)

    def available_skims(self):
        graph_fields = list(self.graph.dtype.names)
        return [x for x in graph_fields if x not in ['link_id', 'a_node', 'b_node', 'direction', 'id']]

    # We check if all minimum fields are there
    def __network_error_checking__(self):

        # Checking field names
        has_fields = self.network.dtype.names
        must_fields = ['link_id', 'a_node', 'b_node', 'direction']
        for field in must_fields:
            if field not in has_fields:
                self.status = 'could not find field "%s" in the network array' % field

                # checking data types
        must_types = [np.int32, np.int32, np.int32, np.int32]
        for field, ytype in zip(must_fields, must_types):
            if self.network[field].dtype != ytype:
                self.status = 'Field "%s" in the network array has the wrong type. Please refer to the documentation' % field

                # Uniqueness of the id
        link_ids = self.network['link_id'].astype(np.int)
        a = np.bincount(link_ids)
        if np.max(a) > 1:
            self.status = '"link_id" field not unique'

            # Direction values
        if np.max(self.network['direction']) > 1 or np.min(self.network['direction']) < -1:
            self.status = '"direction" field not limited to (-1,0,1) values'

    # Needed for when we load the graph directly
    def __graph_error_checking__(self):
        # Checking field names
        self.status = 'graph loaded'
        has_fields = self.graph.dtype.names
        must_fields = ['link_id', 'a_node', 'b_node', 'id']
        for field in must_fields:
            if field not in has_fields:
                self.status = 'could not find field "%s" in the network array' % field

                # checking data types
        must_types = [np.int32, np.int32, np.int32, np.int32]
        for field, ytype in zip(must_fields, must_types):
            if self.graph[field].dtype != ytype:
                self.status = 'Field "%s" in the network array has the wrong type. Please refer to the documentation' % field

                # Uniqueness of the graph id
        a = np.bincount(self.graph['id'].astype(np.int))
        if np.max(a) > 1:
            self.status = '"id" field not unique'

        a = np.bincount(self.graph['link_id'].astype(np.int))
        if np.max(a) > 2:
            self.status = '"link_id" field has more than one link per direction'

        if np.min(self.graph['id']) != 0:
            self.status = '"id" field needs to start in 0 and go to number of links - 1'

        if np.max(self.graph['id']) > self.graph['id'].shape[0]-1:
            self.status = '"id" field needs to start in 0 and go to number of links - 1'

    def __determine_types__(self, new_type, current_type):

        if new_type.isdigit():
            new_type = int(new_type)
        else:
            try:
                new_type = float(new_type)
            except:
                pass
        nt = type(new_type)
        def_type = None
        if nt == int or nt == int:
            def_type = long
            if current_type == float:
                def_type == float
            elif current_type == str:
                def_type = str
        elif nt == float:
            def_type = float
            if current_type == str:
                def_type = str
        elif nt == str:
            def_type = str
        else:
            raise ValueError('WRONG TYPE OR NULL VALUE')
        return def_type
