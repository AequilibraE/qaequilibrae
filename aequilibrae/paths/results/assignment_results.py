import multiprocessing as mp
import numpy as np
import warnings
import sqlite3
import sys
import os
from numpy.lib.format import open_memmap
from ...matrix import AequilibraeMatrix

"""
TO-DO:
1. Create a file type for memory-mapped path files
   Same idea of the AequilibraEData container, but using the format.memmap from NumPy
2. Make the writing to SQL faster by disabling all checks before the actual writing
"""

class AssignmentResults:
    def __init__(self):
        """
        @type graph: Set of numpy arrays to store Computation results
        self.critical={required:{"links":[lnk_id1, lnk_id2, ..., lnk_idn], "path file": False}, results:{}}
        """
        self.link_loads = None       # The actual results for assignment
        self.skims = None            # The array of skims
        self.no_path = None          # The list os paths
        self.num_skims = None        # number of skims that will be computed. Depends on the setting of the graph provided
        self.cores = mp.cpu_count()
        self.classes = {'number':1,
                        'names':['flow']}

        self.critical_links = {'save': False,
                               'queries': {},  # Queries are a dictionary
                               'results': False}

        self.link_extraction = {"save": False,
                                'queries': {},  # Queries are a dictionary
                                "output": None}

        self.path_file = {"save": False,
                          "results": None}

        self.nodes = -1
        self.zones = -1
        self.links = -1
        self.__graph_id__ = None

        self.lids = None
        self.direcs = None


    # In case we want to do by hand, we can prepare each method individually
    def prepare(self, graph, matrix):
        """
        :param graph: AequilibraE graph. Needs to have been set with number of centroids and list of skims (if any)
        :param matrix: AequilibraE Matrix properly set for computation using matrix.computational_view([matrix list])
        :return:
        """
        if matrix.view_names is None:
            raise ('Please set the matrix_procedures computational view')
        else:
            self.classes['number'] = matrix.matrix_view.shape[2]
            self.classes['names'] = matrix.view_names

        if graph is None:
            raise ('Please provide a graph')
        else:
            self.nodes = graph.num_nodes + 1
            self.zones = graph.centroids + 1
            self.links = graph.num_links + 1
            self.num_skims = graph.skims.shape[1]

            self.lids = graph.graph['link_id']
            self.direcs = graph.graph['direction']
            self.__redim()
            self.__graph_id__ = graph.__id__

            self.setSavePathFile(False)
            self.setCriticalLinks(False)

    def reset(self):
        if self.link_loads is not None:
            self.skims.fill(0)
            self.no_path.fill(-1)
        else:
            print 'Exception: Assignment results object was not yet prepared/initialized'

    def __redim(self):
        self.link_loads = np.zeros((self.links, self.classes['number']), np.float64)
        self.skims = np.zeros((self.zones, self.zones, self.num_skims), np.float64)
        self.no_path = np.zeros((self.zones, self.zones), dtype=np.int32)

        self.reset()

    def set_cores(self, cores):
        if isinstance(cores, int):
            if cores > 0:
                if self.cores != cores:
                    self.cores = cores
                    if self.link_loads is not None:
                        self.__redim()
            else:
                raise ValueError("Number of cores needs to be equal or bigger than one")
        else:
            raise ValueError("Number of cores needs to be an integer")

    def setCriticalLinks(self, save=False, queries={}, crit_res_result=None):
        a = AequilibraeMatrix()
        if save:
            if crit_res_result is None:
                warnings.warn("Critical Link analysis not set properly. Need to specify output file too")
            else:
                if crit_res_result[-3:].lower() != 'aem':
                    crit_res_result += '.aes'

                if self.nodes > 0 and self.zones > 0:
                    if ['elements', 'labels', 'type'] in queries.keys():
                        if len(queries['labels']) == len(queries['elements']) == len(queries['type']):
                            a.create_empty(file_name=crit_res_result, zones=self.zones, matrix_names=queries['labels'])
                        else:
                            raise ValueError("Queries are inconsistent. 'Labels', 'elements' and 'type' need to have same dimensions")
                    else:
                        raise ValueError("Queries are inconsistent. It needs to contain the following elements: 'Labels', 'elements' and 'type'")
        else:
            a.create_empty(file_name=a.random_name(), zones=self.zones, matrix_names=['empty', 'nothing'])
        self.critical_links = {'save': save,
                               'queries': queries,
                               'results': a
                               }

    def setSavePathFile(self, save=False, path_result=None):
        a = np.zeros((max(1,self.zones), 1, 2), dtype=np.int32)
        if save:
            if path_result is None:
                warnings.warn("Path file not set properly. Need to specify output file too")
            else:
                if path_result[-3:].lower() != 'aep':
                    path_result += '.aep'

                if self.nodes > 0 and self.zones > 0:
                    a = open_memmap(path_result, dtype=np.int32, mode='w+', shape=(self.zones,self.nodes, 2))

        self.path_file = {'save': save,
                          'results': a
                          }

    def save_to_disk(self, output='loads', output_file_name ='link_flows', file_type='csv'):
        ''' Function to write to disk all outputs computed during assignment
    Args:
        output: 'loads', for writing the link loads
                'path_file', for writing the path file to a format different than the native binary

        output_file_name: Name of the file, with extension

        file_type: 'csv', for comma-separated files
                   'sqlite' for sqlite databases
    Returns:
        Nothing'''
        headers = ['link']
        if output == 'loads':
            dt = [('Link ID', np.int)]
            for n in self.classes['names']:
                dt.extend([(n + '_ab', np.float), (n + '_ba', np.float), (n + '_tot', np.float)])
                headers.extend(n + '_ab', n + '_ba', n + '_tot')
            res = np.zeros((np.max(self.lids) + 1, self.classes['number']), dtype=dt)

            res['Link ID'][:] = np.arange(np.max(self.lids) + 1)[:]

            # Indices of links BA and AB
            ABs = self.direcs < 0
            BAs = self.direcs > 0
            ab_ids = self.lids[ABs]
            ba_ids = self.lids[BAs]

            # Link flows
            link_flows = self.link_loads[:-1, :]
            for i in enumerate(self.classes['names']):
                n = self.classes['names'][i]
                # AB Flows
                res[n + '_ab'][ab_ids] = link_flows[ABs, :]
                # BA Flows
                res[n + '_ba'][ba_ids] = link_flows[BAs, :]

                # Tot Flow
                res[n + '_tot'] = res[n + '_ab'] + res[n + '_ba']

            # Save to disk
            if file_type == 'csv':
                np.savetxt(output_file_name, res, fmt="%d "+",%1.10f"*3, header=headers)

            if file_type == 'sqlite':
            # Connecting to the database file
                conn = sqlite3.connect(output_file_name)
                c = conn.cursor()
            # Creating the flows table
                c.execute('''DROP TABLE IF EXISTS link_flows''')
                fi = ''
                qm = '?'
                for f in headers[1:]:
                    fi += ', ' + f + ' REAL'
                    qm += ', ?'

                c.execute('''CREATE TABLE link_flows (link_id INTEGER PRIMARY KEY''' + fi + ')''')
                c.execute('BEGIN TRANSACTION')
                c.executemany('INSERT INTO link_flows VALUES (' + qm + ')', res)
                c.execute('END TRANSACTION')
                conn.commit()
                conn.close()

        elif output == 'path_file':
            conn = sqlite3.connect(output_file_name)
            c = conn.cursor()

            # Creating the flows table
            c.execute('''DROP TABLE IF EXISTS path_file''')
            c.execute('''CREATE TABLE path_file (origin_zone INTEGER, node INTEGER, predecessor INTEGER)''')
            c.execute('BEGIN TRANSACTION')

            path_file = path_file = self.path_file['results']
            for i in range(self.zones):
                data = np.zeros((self.nodes, 3), np.int64)
                data[:,0].fill(i)
                data[:,1] = path_file[i,:,0]
                data[:,2] = path_file[i,:,1]
                c.executemany('''INSERT INTO path_file VALUES(?, ?, ?)''', data)
            c.execute('END TRANSACTION')
            conn.commit()
            conn.close()


