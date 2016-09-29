# -------------------------------------------------------------------------------
# Name:       TRAFFIC ASSIGNMENT
# Purpose:    Implement procedures to translate a layer and parameters into entry for assignment
#
# Author:      Pedro Camargo
# Website:    www.AequilibraE.com
# Repository:  
#
# Created:     12/01/2014
# Copyright:   (c) Pedro Camargo 2014
# Licence:     GPL
# -------------------------------------------------------------------------------

try:
    import qgis
    from qgis.core import *
    from PyQt4.QtCore import SIGNAL
except:
    pass

import sys, os
import time
import numpy as np
import sys

from multiprocessing.dummy import Pool as ThreadPool
import thread

import math


import platform
plat = platform.system()
if plat == 'Windows':
    import struct
    if (8 * struct.calcsize("P")) == 64:
        from win64 import *
    if (8 * struct.calcsize("P")) == 32:
        from win32 import *

if plat == 'Darwin':
    from mac import *

def main():
    pass


def all_or_nothing(matrix, graph, results):

    # catch errors
    if results.graph_id is None:
        raise ValueError('The results object was not prepared. Use results.prepare(graph)')

    elif results.graph_id != graph.__id__:
        raise ValueError('The results object was prepared for a different graph')

    else:
        pool = ThreadPool(results.cores)
        all_threads = {'count': 0}
        for O in range(results.zones):
            a = matrix[O, :]
            if np.sum(a) > 0:
                #func_assig_thread(O, a, graph, results, all_threads)
                pool.apply_async(func_assig_thread, args=(O, a, graph, results, all_threads))
        pool.close()
        pool.join()


def func_assig_thread(O, a, g, res, all_threads):
    if thread.get_ident() in all_threads:
        th = all_threads[thread.get_ident()]
    else:
        all_threads[thread.get_ident()] = all_threads['count']
        th = all_threads['count']
        all_threads['count'] += 1

    one_to_all(O, a, g, res, th, True)

def ota(O, a, g, res):
    one_to_all(O, a, g, res, 0)

'''
class WorkerThreadAssignment(QThread):
    def __init__(self, parentThread):
        QThread.__init__(self, parentThread)

    def run(self):
        self.running = True
        success = self.doWork()
        self.emit(SIGNAL("jobFinished( PyQt_PyObject )"), success)

    def stop(self):
        self.running = False
        pass

    def doWork(self):
        return True

    def cleanUp(self):
        pass


class Assigns_Frank_Wolfe(WorkerThreadAssignment):
    def __init__(self, parentThread, matrix, GRAPH, GRAPH_PARAMS, vdf, select_analysis, cores, procedure):
        WorkerThreadAssignment.__init__(self, parentThread)
        self.matrix = matrix
        self.GRAPH = GRAPH
        self.GRAPH_PARAMS = GRAPH_PARAMS
        self.vdf = vdf
        self.select_analysis = select_analysis
        self.cores = cores
        self.procedure = procedure
        self.evol_bar = 3
        self.error = None

    def doWork(self):
        evol_bar = self.evol_bar
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'F&W equilibrium assignment'))
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.matrix.shape[0]))

        if self.matrix.dtype != "float64":
            self.matrix = self.matrix.astype(np.float64)
        self.zones = self.matrix.shape[0]
        self.assigned = np.zeros(1, np.int32)

        # Prepare the initial graph
        graph_costs, b_nodes, graph_fs, idsgraph, graph_skim = AoN.building_graph(self.GRAPH)


        # Output matrices
        self.no_path = np.zeros((self.matrix.shape[0], self.matrix.shape[1]), np.int64)
        self.skims = np.zeros((self.matrix.shape[0], self.matrix.shape[1], self.GRAPH.shape[1] - 6), np.float64)
        self.Link_Loads = np.zeros((graph_costs.shape[0], self.cores), np.float64)
        self.thread_dict = {}

        while rel_gap > actual_error:
            pool = ThreadPool(self.cores)
            # print 'entering loop'
            for O in range(self.zones):
                pool.apply_async(func_assig, args=(
                O, self.matrix[O, :], graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, self.Link_Loads,
                self.no_path[O, :], self.skims[O, :, :], self.thread_dict, self.assigned, evol_bar))

            pool.close()
            pool.join()

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, self.matrix.shape[0]))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Assignment Finalized'))

        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)


class Assigns_All_Or_Nothing(WorkerThreadAssignment):
    def __init__(self, parentThread, matrix, GRAPH, select_analysis, cores, procedure):
        WorkerThreadAssignment.__init__(self, parentThread)
        self.matrix = matrix
        self.GRAPH = GRAPH
        self.select_analysis = select_analysis
        self.cores = cores
        self.procedure = procedure
        self.error = None
        self.zones = self.matrix.shape[0]
        self.evol_bar = 3

    def doWork(self):
        evol_bar = self.evol_bar
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'All or nothing assignment'))
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.zones))

        if self.matrix.dtype != "float64":
            self.matrix = self.matrix.astype(np.float64)



        self.All_Loads = None

        self.assigned = np.zeros(1, np.int32)

        self.no_path = np.zeros((self.matrix.shape[0], self.matrix.shape[1]), np.int64)
        self.skims = np.zeros((self.matrix.shape[0], self.matrix.shape[1], self.GRAPH.shape[1] - 6), np.float64)
        self.Link_Loads = np.zeros((graph_costs.shape[0], self.cores), np.float64)
        self.thread_dict = {}

        # NOW WE MAKE THE CONNECTORS ABSURDLY EXPENSIVE SO FLOWS WOULD NOT GO THROUGH THE CENTROIDS
        # The penalty cost is of one order of magnitude bigger than the whole network cost
        self.penalty_cost = 10 ** (int(math.log(np.sum(graph_costs), 2) / math.log(10, 2)) + 1)
        for i in xrange(0, graph_fs[self.zones]):
            graph_costs[i] = graph_costs[i] + self.penalty_cost

        # TEMPORARY ARRAYS NEEDED FOR THE ALGORITHM AND THAT WILL BE SHARED BY ALL THREADS
        nodes = graph_costs.shape[0]
        predecessors = np.empty((nodes, self.cores), dtype=np.int64)
        conn = np.empty((nodes, self.cores), dtype=np.int64)
        temp_skims = np.empty((nodes, self.GRAPH.shape[1] - 6, self.cores), dtype=np.float64)
        temp_skims[:, 0, :].fill(-self.penalty_cost)
        t = time.clock()

        # print self.cores
        pool = ThreadPool(self.cores)
        for O in range(self.zones):
            if np.sum(self.matrix[O, :]) > 0:
                # self.func_assig(O,self.matrix,graph_costs, b_nodes, graph_fs,idsgraph,graph_skim, self.Link_Loads, self.no_path, self.skims, self.thread_dict,predecessors,conn,temp_skims, evol_bar)
                pool.apply_async(self.func_assig, args=(
                O, self.matrix, self.graph, self.Link_Loads, self.no_path, self.skims, self.thread_dict, predecessors, conn, temp_skims, evol_bar))
        pool.close()
        pool.join()

        # print time.clock()-t
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, self.matrix.shape[0]))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Assignment Finalized'))

        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)

    def func_assig(self, O, demand, graph, Link_Loads, no_path, skims,thread_dict, predecessors, conn, temp_skims, evol_bar):
        ct = 0

        ct = thread.get_ident()
        if ct in thread_dict.keys():
            ct = thread_dict[ct]
        else:
            a = len(thread_dict.keys())
            thread_dict[ct] = a
            ct = a

        thread_results = AssignmentResults()
        thread_results.linkloads = Link_Loads[:, ct]
        thread_results.predecessors = predecessors[:, ct]
        thread_results.connectors = conn[:, ct]
        thread_results.cost = None
        thread_results.skims = skims[O, :, :]
        thread_results.no_path = no_path[O, :]
        thread_results.temporary_skims = self.temporary_skims = temp_skims[:, :, ct]


        a = AoN.One_to_all(O, demand[O, :], graph, thread_results)
        self.assigned[0] = self.assigned[0] + 1
        # QThread.emit(SIGNAL( "ProgressValue( PyQt_PyObject )" ), (evol_bar,assigned[0]))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, assigned[0]))



class Compute_Dist_Matrix(WorkerThreadAssignment):
    def __init__(self, parentThread, GRAPH, all_zones, cores, evol_bar, procedure):
        WorkerThreadAssignment.__init__(self, parentThread)
        self.GRAPH = GRAPH
        self.cores = cores
        self.procedure = procedure
        self.error = None
        self.all_zones = all_zones
        self.zones = np.max(all_zones) + 1
        self.evol_bar = evol_bar

    def doWork(self):
        evol_bar = self.evol_bar
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Computing Impedance matrix'))
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, self.all_zones.shape[0]))
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 0))

        graph_costs, b_nodes, graph_fs, idsgraph, graph_skim = AoN.building_graph(self.GRAPH)

        self.assigned = np.zeros(1, np.int32)

        self.no_path = np.zeros((self.zones, self.zones), np.int64)
        self.skims = np.zeros((self.zones, self.zones, self.GRAPH.shape[1] - 6), np.float64)
        self.thread_dict = {}

        # NOW WE MAKE THE CONNECTORS ABSURDLY EXPENSIVE SO FLOWS WOULD NOT GO THROUGH THE CENTROIDS
        # The penalty cost is of one order of magnitude bigger than the whole network cost
        self.penalty_cost = 10 ** (int(math.log(np.sum(graph_costs), 2) / math.log(10, 2)) + 1)
        for i in xrange(0, graph_fs[self.zones]):
            graph_costs[i] = graph_costs[i] + self.penalty_cost

        # TEMPORARY ARRAYS NEEDED FOR THE ALGORITHM AND THAT WILL BE SHARED BY ALL THREADS
        nodes = graph_costs.shape[0]
        predecessors = np.empty((nodes, self.cores), dtype=np.int64)
        conn = np.empty((nodes, self.cores), dtype=np.int64)
        temp_skims = np.empty((nodes, self.GRAPH.shape[1] - 6, self.cores), dtype=np.float64)
        temp_skims[:, 0, :].fill(-self.penalty_cost)
        t = time.clock()

        # self.cores
        pool = ThreadPool(self.cores)
        for O in self.all_zones:
            self.func_assig(O, graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, self.no_path, self.skims,
                            self.thread_dict, predecessors, conn, temp_skims, evol_bar)
            # pool.apply_async(self.func_assig,args=(O,graph_costs, b_nodes, graph_fs,idsgraph,graph_skim, self.no_path, self.skims, self.thread_dict,predecessors,conn,temp_skims, evol_bar))
        pool.close()
        pool.join()

        # print time.clock()-t
        # self.emit(SIGNAL( "ProgressValue( PyQt_PyObject )" ), (evol_bar,self.matrix.shape[0]))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Assignment Finalized'))

        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)

    def func_assig(self, O, graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, no_path, skims, thread_dict,
                   predecessors, conn, temp_skims, evol_bar):
        ct = 0

        ct = thread.get_ident()
        if ct in thread_dict.keys():
            ct = thread_dict[ct]
        else:
            a = len(thread_dict.keys())
            thread_dict[ct] = a
            ct = a

        a = AoN.SKIMS_One_to_all(O, graph_costs, b_nodes, graph_fs, idsgraph, graph_skim, no_path[O, :], skims[O, :, :],
                                 predecessors[:, ct], conn[:, ct], temp_skims[:, :, ct])
        self.assigned[0] = self.assigned[0] + 1

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, str(self.assigned[0])))


class traffic_maps(WorkerThreadAssignment):  # retrieving results and plotting map
    def __init__(self, parentThread, layer, theme, SizeScale, LINK_FLOWS_ABFlow, LINK_FLOWS_BAFlow, max_abflow,
                 max_baflow, max_totflow, procedure):
        WorkerThreadAssignment.__init__(self, parentThread)
        self.layer = layer
        self.theme = theme
        self.SizeScale = SizeScale
        self.LINK_FLOWS_ABFlow = LINK_FLOWS_ABFlow
        self.LINK_FLOWS_BAFlow = LINK_FLOWS_BAFlow
        self.max_abflow = max_abflow
        self.max_baflow = max_baflow
        self.max_totflow = max_totflow
        self.procedure = procedure
        self.error = None
        self.evol_bar = 4

        # Let's make maps!!!

    def doWork(self):
        # We check if we need new symbol layers to make maps for both directions
        renderer = self.layer.rendererV2()
        symbol = renderer.symbol()
        evol_bar = self.evol_bar
        self.emit(SIGNAL("ProgressMaxValue( PyQt_PyObject )"), (evol_bar, 3))
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 0))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Preparing Maps'))

        # We add the appropriate symbol layers
        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 1))
        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Adding symbol layers'))
        symbol.insertSymbolLayer(0, QgsSimpleLineSymbolLayerV2())
        symbol.insertSymbolLayer(0, QgsSimpleLineSymbolLayerV2())
        # Delete those we won't use
        if symbol.symbolLayerCount() > 2:
            for i in xrange(symbol.symbolLayerCount(), 2, -1):
                symbol.deleteSymbolLayer(symbol.symbolLayerCount() - 1)

        renderer = self.layer.rendererV2()
        symbol = renderer.symbol()

        if self.theme == "tot_vol":
            self.emit(SIGNAL("ProgressText4 ( PyQt_PyObject )"), 'Preparing color themes')
            symbol.symbolLayer(0).setDataDefinedProperty(u'color',
                                                         u'color_hsva(180 - scale_linear(abs(' + self.LINK_FLOWS_ABFlow + '), 0, ' + str(
                                                             self.max_abflow) + ', 0, 180), 90, 90, 255)')
            symbol.symbolLayer(1).setDataDefinedProperty(u'color',
                                                         u'color_hsva(180 - scale_linear(abs(' + self.LINK_FLOWS_BAFlow + '), 0, ' + str(
                                                             self.max_baflow) + ', 0, 180), 90, 90, 255)')
        self.emit(SIGNAL("ProgressValue4( PyQt_PyObject )"), 2)


        # We make the thickness map
        if self.SizeScale == "tot_vol":
            self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Preparing Scale sized lines'))
            symbol.symbolLayer(0).setDataDefinedProperty(u'offset',
                                                         u'scale_linear(abs(' + self.LINK_FLOWS_ABFlow + '), 0,' + str(
                                                             self.max_totflow) + ', 0, 4) / 2 + 0.25')
            symbol.symbolLayer(0).setDataDefinedProperty(u'width',
                                                         u'scale_linear(abs(' + self.LINK_FLOWS_ABFlow + '), 0, ' + str(
                                                             self.max_totflow) + ', 0, 4)')

            symbol.symbolLayer(1).setDataDefinedProperty(u'offset',
                                                         u'0 - abs(scale_linear(abs(' + self.LINK_FLOWS_BAFlow + '), 0,' + str(
                                                             self.max_totflow) + ', 0, 4) / 2 + 0.25)')
            symbol.symbolLayer(1).setDataDefinedProperty(u'width',
                                                         u'scale_linear(abs(' + self.LINK_FLOWS_BAFlow + '),0,' + str(
                                                             self.max_totflow) + ', 0, 4)')

            if self.theme == None:
                symbol.symbolLayer(0).setDataDefinedProperty(u'color', u'0,170,0,255')
                symbol.symbolLayer(1).setDataDefinedProperty(u'color', u'0,170,0,255')

        self.emit(SIGNAL("ProgressValue( PyQt_PyObject )"), (evol_bar, 3))

        self.emit(SIGNAL("ProgressText ( PyQt_PyObject )"), (evol_bar, 'Maps finalized. Refreshing'))
        self.emit(SIGNAL("FinishedThreadedProcedure( PyQt_PyObject )"), self.procedure)

            """symbol.appendSymbolLayer(symbol.symbolLayer(0))
            properties2 = {'size': '1.0', 'color': '255,255,255,255'}
            symbol_layer2 = QgsMarkerLineSymbolLayerV2.create(properties2)
            symbol.changeSymbolLayer(2, symbol_layer2)
            symbol_layer = QgsSimpleMarkerSymbolLayerV2()
            symbol.symbolLayer(2).subSymbol().appendSymbolLayer(symbol_layer)
            symbol.symbolLayer(2).subSymbol().symbolLayer(0).setName('arrowhead')
            symbol.symbolLayer(2).subSymbol().symbolLayer(0).setColor(QtGui.QColor(255,255,255,255))
            symbol.symbolLayer(2).subSymbol().symbolLayer(0).setBorderColor(QtGui.QColor(255,255,255,255))
            symbol.symbolLayer(2).subSymbol().symbolLayer(0).setDataDefinedProperty(u'offset',u'scale_linear(abs(LINK_FLOWS_BAFlow), 0, -10, 0, -2) / 2 - 1.5')
            symbol.symbolLayer(2).subSymbol().symbolLayer(0).setDataDefinedProperty(u'size', u'scale_linear(abs(LINK_FLOWS_BAFlow), 0, 10, 0, 2)')
            symbol.symbolLayer(2).subSymbol().symbolLayer(1).setName('arrowhead')
            symbol.symbolLayer(2).subSymbol().symbolLayer(1).setColor(QtGui.QColor(255,255,255,255))
            symbol.symbolLayer(2).subSymbol().symbolLayer(1).setBorderColor(QtGui.QColor(255,255,255,255))
            symbol.symbolLayer(2).subSymbol().symbolLayer(1).setDataDefinedProperty(u'offset',u'scale_linear(abs(LINK_FLOWS_ABFlow), 0, 10, 0, 2) / 2 + 1.5')
            symbol.symbolLayer(2).subSymbol().symbolLayer(1).setDataDefinedProperty(u'size', u'scale_linear(abs(LINK_FLOWS_ABFlow), 0, 10, 0, 2)')renderer.setSizeScaleField('LINK_FLOWS_TotFlow')
            try:
                w=4.5/self.max_flow
            except:
                w=1
            symbol.setWidth(w)"""


class select_analysis_sets():
    def __init__(self):
        self.links = np.zeros(0, dtype='int64')
        self.origins = np.zeros(0, dtype='int64')
        self.destinations = np.zeros(0, dtype='int64')

'''


if __name__ == '__main__':
    main()
