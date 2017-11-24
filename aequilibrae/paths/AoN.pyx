"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Core path computation algorithms
 Purpose:    Implement shortest path and network loading routines

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camrgo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    15/09/2013
 Updated:    30/Nov/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------

Original Algorithm for Shortest path (Dijkstra with a Fibonacci heap) was written by Jake Vanderplas <vanderplas@astro.washington.edu> under license: BSD, (C) 2012
 """

"""
TODO:
LIST OF ALL THE THINGS WE NEED TO DO TO NOT HAVE TO HAVE nodes 1..n as CENTROIDS. ARBITRARY NUMBERING

- Checks of weather the centroid we are computing path from is a centroid and/or exists in the graph
- Re-write function **network_loading** on the part of loading flows to centroids

"""


cimport numpy as np
cimport cython

include 'parameters.pxi'
from libc.stdlib cimport abort, malloc, free
from ..__version__ import version as VERSION


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def one_to_all(origin, matrix, graph, result, aux_result, curr_thread):
    cdef long nodes, orig, i, block_flows_through_centroids, classes, b, origin_index, zones, posit, posit1
    cdef int critical_queries = 0
    cdef int link_extract_queries, query_type

    # Origin index is the index of the matrix we are assigning
    # this is used as index for the skim matrices
    # orig is the ID of the actual centroid
    # Is is used to actual path computation and to refer to outputs of path computation

    orig = origin
    origin_index = graph.nodes_to_indices[orig]

    if VERSION != graph.__version__:
        raise ValueError('This graph was created for a different version of AequilibraE. Please re-create it')

    if result.critical_links['save']:
        critical_queries = len(result.critical_links['queries'])
        aux_link_flows = np.zeros(result.links, ITYPE)
    else:
        aux_link_flows = np.zeros(1, ITYPE)

    if result.link_extraction['save']:
        link_extract_queries = len(result.link_extraction['queries'])

    nodes = graph.num_nodes
    zones = graph.num_zones
    block_flows_through_centroids = graph.block_centroid_flows

    # In order to release the GIL for this procedure, we create all the
    # memory views we will need
    cdef double [:, :] demand_view = matrix.matrix_view[origin_index, :, :]
    classes = matrix.matrix_view.shape[2]

    # views from the graph
    cdef unsigned long [:] graph_fs_view = graph.fs
    cdef double [:] g_view = graph.cost
    cdef unsigned long [:] ids_graph_view = graph.ids
    cdef unsigned long [:] all_nodes_view = graph.all_nodes
    cdef unsigned long [:] original_b_nodes_view = graph.graph['b_node']
    cdef double [:, :] graph_skim_view = graph.skims

    # views from the result object
    cdef double [:, :] final_skim_matrices_view = result.skims.matrix_view[origin_index, :, :]
    cdef unsigned long [:] no_path_view = result.no_path[origin_index, :]

    # views from the aux-result object
    cdef unsigned long [:] predecessors_view = aux_result.predecessors[:, curr_thread]
    cdef double [:, :] skim_matrix_view = aux_result.temporary_skims[:, :, curr_thread]
    cdef unsigned long [:] reached_first_view = aux_result.reached_first[:, curr_thread]
    cdef unsigned long [:] conn_view = aux_result.connectors[:, curr_thread]
    cdef double [:, :] link_loads_view = aux_result.temp_link_loads[:, :, curr_thread]
    cdef double [:, :] node_load_view = aux_result.temp_node_loads[:, :, curr_thread]
    cdef unsigned long [:] b_nodes_view = aux_result.temp_b_nodes[:, curr_thread]

    # path file variables
    # 'origin', 'node', 'predecessor', 'connector'
    posit = origin_index * graph.num_nodes * result.path_file['save']
    posit1 = posit + graph.num_nodes

    cdef unsigned int [:] pred_view = result.path_file['results'].predecessor[posit:posit1]
    cdef unsigned int [:] c_view = result.path_file['results'].connector[posit:posit1]
    cdef unsigned int [:] o_view = result.path_file['results'].origin[posit:posit1]
    cdef unsigned int [:] n_view = result.path_file['results'].node[posit:posit1]

    # select link variables
    cdef double [:, :] sel_link_view = result.critical_links['results'].matrix_view[origin_index,:,:]
    cdef unsigned long [:] aux_link_flows_view = aux_link_flows

    #Now we do all procedures with NO GIL
    with nogil:
        if block_flows_through_centroids: # Unblocks the centroid if that is the case
            b = 0
            blocking_centroid_flows(b,
                                    origin_index,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)
        w = path_finding(origin_index,
                         g_view,
                         b_nodes_view,
                         graph_fs_view,
                         predecessors_view,
                         ids_graph_view,
                         conn_view,
                         reached_first_view)

        network_loading(classes,
                        demand_view,
                        predecessors_view,
                        conn_view,
                        link_loads_view,
                        no_path_view,
                        reached_first_view,
                        node_load_view,
                        w)

        if block_flows_through_centroids: # Re-blocks the centroid if that is the case
            b = 1
            blocking_centroid_flows(b,
                                    origin_index,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)

        _copy_skims(skim_matrix_view,
                    final_skim_matrices_view)

    if result.path_file['save']:
        with nogil:
            put_path_file_on_disk(orig,
                                  pred_view,
                                  predecessors_view,
                                  c_view,
                                  conn_view,
                                  all_nodes_view,
                                  o_view,
                                  n_view)

    for i in range(critical_queries):
        critical_links_view = return_an_int_view(result.path_file['queries']['elements'][i])
        query_type = 0
        if result.path_file['queries'][ type][i] == "or":
            query_type = 1
        with nogil:
            perform_select_link_analysis(orig,
                                         classes,
                                         demand_view,
                                         predecessors_view,
                                         conn_view,
                                         aux_link_flows_view,
                                         sel_link_view,
                                         query_type)

    return origin

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef void network_loading(long classes,
                           double[:, :] demand,
                           unsigned long [:] pred,
                           unsigned long [:] conn,
                           double[:, :] link_loads,
                           unsigned long [:] no_path,
                           unsigned long [:] reached_first,
                           double [:, :] node_load,
                           long found) nogil:

    cdef unsigned long i, j, predecessor, connector, node
    cdef unsigned long zones = demand.shape[0]
    cdef unsigned long N = node_load.shape[0]

    # Clean the node load array
    for i in range(N):
        node_load[i] = 0

    # Loads the demand to the centroids
    for j in range(classes):
        for i in range(zones):
            node_load[i, j] = demand[i, j]

    #Recursevely cascades to the origin
    for i in xrange(found, 0, -1):
        node = reached_first[i]

        # captures how we got to that node
        predecessor = pred[node]
        connector = conn[node]

        # loads the flow to the links for each class
        for j in range(classes):
            link_loads[connector, j] += node_load[node, j]

            # Cascades the load from the node to their predecessor
            node_load[predecessor, j] += node_load[node, j]

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cdef void _copy_skims(double[:,:] skim_matrix,  #Skim matrix_procedures computed from one origin to all nodes
                      double[:,:] final_skim_matrix) nogil:  #Skim matrix_procedures computed for one origin to all other centroids only

    cdef long i, j
    cdef long N = final_skim_matrix.shape[0]
    cdef long skims = final_skim_matrix.shape[1]

    for i in range(N):
        for j in range(skims):
            final_skim_matrix[i,j]=skim_matrix[i,j]


cdef return_an_int_view(input):
    cdef int [:] critical_links_view = input
    return critical_links_view


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cpdef void perform_select_link_analysis(long origin,
                                        int classes,
                                        double[:, :] demand,
                                        unsigned long [:] pred,
                                        unsigned long [:] conn,
                                        unsigned long [:] aux_link_flows,
                                        double [:, :] critical_array,
                                        int query_type) nogil:
    cdef unsigned int t_origin
    cdef ITYPE_t c, j, i, p, l
    cdef unsigned int dests = demand.shape[0]
    cdef unsigned int q = critical_array.shape[0]

    """ TODO:
    FIX THE SELECT LINK ANALYSIS FOR MULTIPLE CLASSES"""
    l = 0
    for j in range(dests):
        if demand[j, l] > 0:
            p = pred[j]
            j = i
            while p >= 0:
                c = conn[j]
                aux_link_flows[c] = 1
                j = p
                p = pred[j]
        if query_type == 1: # Either one of the links in the query
            for i in range(q):
                if aux_link_flows[i] == 1:
                    critical_array


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cpdef void put_path_file_on_disk(unsigned int orig,
                                 unsigned int [:] pred,
                                 unsigned long [:] predecessors,
                                 unsigned int [:] conn,
                                 unsigned long [:] connectors,
                                 unsigned long [:] all_nodes,
                                 unsigned int [:] origins_to_write,
                                 unsigned int [:] nodes_to_write) nogil:
    cdef unsigned long i
    cdef unsigned long k = pred.shape[0]

    for i in range(k):
        origins_to_write[i] = orig
        nodes_to_write[i] = all_nodes[i]
        pred[i] = all_nodes[predecessors[i]]
        conn[i] = connectors[i]


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cdef void blocking_centroid_flows(unsigned long action,
                                  unsigned long orig,
                                  unsigned long [:] fs,
                                  unsigned long [:] temp_b_nodes,
                                  unsigned long [:] real_b_nodes) nogil:
    cdef unsigned long i

    if action == 0: # We are unblocking
        for i in xrange(fs[orig], fs[orig + 1]):
            temp_b_nodes[i] = real_b_nodes[i]
    else: # We are blocking:
        for i in xrange(fs[orig], fs[orig + 1]):
            temp_b_nodes[i] = orig

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def path_computation(origin, destination, graph, results):
    cdef ITYPE_t nodes, orig, D, p, b
    cdef long i, j, skims, a, block_flows_through_centroids

    if results.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    # Consistency checks
    if origin >= graph.fs.shape[0]:
        return "Node " + str(origin) + " is outside the range of nodes in the graph"

    if graph.fs[origin] == graph.fs[origin+1]:
        return "Node " + str(origin) + " does not exist in the graph"

    if VERSION != graph.__version__:
        return 'This graph was created for a different version of AequilibraE. Please re-create it'
    #We transform the python variables in Cython variables
    orig = origin
    D = destination
    nodes = graph.num_nodes

     # initializes skim_matrix for output
    # initializes predecessors  and link connectors for output
    results.predecessors.fill(-1)
    results.connectors.fill(-1)
    results.temporary_skims.fill(-1)
    skims = results.num_skims

    #In order to release the GIL for this procedure, we create all the
    #memmory views we will need
    cdef double [:] g_view = graph.cost
    cdef unsigned long [:] original_b_nodes_view = graph.graph['b_node']
    cdef unsigned long [:] graph_fs_view = graph.fs
    cdef double [:, :] graph_skim_view = graph.skims
    cdef unsigned long [:] ids_graph_view = graph.graph['link_id']
    block_flows_through_centroids = graph.block_centroid_flows

    cdef unsigned long [:] predecessors_view = results.predecessors
    cdef unsigned long [:] conn_view = results.connectors
    cdef double [:, :] skim_matrix_view = results.temporary_skims
    cdef unsigned long [:] reached_first_view = results.reached_first

    new_b_nodes = graph.b_node.copy()
    cdef unsigned long [:] b_nodes_view = new_b_nodes

    #Now we do all procedures with NO GIL
    with nogil:
        if block_flows_through_centroids: # Unblocks the centroid if that is the case
            b = 0
            blocking_centroid_flows(b,
                                    orig,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)
        w = path_finding(orig,
                         g_view,
                         b_nodes_view,
                         graph_fs_view,
                         predecessors_view,
                         ids_graph_view,
                         conn_view,
                         reached_first_view)

        if block_flows_through_centroids: # Unblocks the centroid if that is the case
            b = 1
            blocking_centroid_flows(b,
                                    orig,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)
    if 0<= D < results.nodes:
        p = predecessors_view[D]
        all_connectors = []
        all_nodes = [D]
        milepost = [skim_matrix_view[D]]
        if p >= 0:
            while p > 0:
                all_connectors.append(conn_view[D])
                all_nodes.append(p)
                milepost.append(skim_matrix_view[p])
                D = p
                p = predecessors_view[p]
            results.path = np.asarray(all_connectors, np.int64)[::-1]
            results.path_nodes = np.asarray(all_nodes, np.int64)[::-1]
            results.milepost =  np.asarray(milepost, np.float64)[::-1]

            del all_nodes
            del all_connectors
            del milepost

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def skimming_single_origin(origin, graph, result, aux_result, curr_thread):
    """
    :param origin:
    :param graph:
    :param results:
    :return:
    """
    cdef unsigned long nodes, orig, origin_index, i, block_flows_through_centroids, skims, zones, b
    #We transform the python variables in Cython variables
    orig = origin
    origin_index = graph.nodes_to_indices[orig]

    graph_fs = graph.fs

    if result.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    if orig not in graph.centroids:
        return "Centroid " + str(orig) + " is outside the range of zones in the graph"

    if orig > graph.num_nodes:
        return "Centroid " + str(orig) + " does not exist in the graph"

    if graph_fs[orig] == graph_fs[orig + 1]:
        return "Centroid " + str(orig) + " does not exist in the graph"

    if VERSION != graph.__version__:
        return 'This graph was created for a different version of AequilibraE. Please re-create it'

    nodes = graph.num_nodes + 1
    zones = graph.num_zones
    block_flows_through_centroids = graph.block_centroid_flows
    skims = result.num_skims

    # In order to release the GIL for this procedure, we create all the
    # memory views we will need

    # views from the graph
    cdef unsigned long [:] graph_fs_view = graph.fs
    cdef double [:] g_view = graph.cost
    cdef unsigned long [:] ids_graph_view = graph.ids
    cdef unsigned long [:] original_b_nodes_view = graph.b_node
    cdef double [:, :] graph_skim_view = graph.skims[:, :]

    cdef double [:, :] final_skim_matrices_view = result.skims.matrix_view[origin_index, :, :]

    # views from the aux-result object
    cdef unsigned long [:] predecessors_view = aux_result.predecessors[:, curr_thread]
    cdef unsigned long [:] reached_first_view = aux_result.reached_first[:, curr_thread]
    cdef unsigned long [:] conn_view = aux_result.connectors[:, curr_thread]
    cdef unsigned long [:] b_nodes_view = aux_result.temp_b_nodes[:, curr_thread]
    cdef double [:, :] skim_matrix_view = aux_result.temporary_skims[:, :, curr_thread]

    #Now we do all procedures with NO GIL
    with nogil:
        if block_flows_through_centroids: # Unblocks the centroid if that is the case
            b = 0
            blocking_centroid_flows(b,
                                    origin_index,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)
        w = path_finding(origin_index,
                         g_view,
                         b_nodes_view,
                         graph_fs_view,
                         predecessors_view,
                         ids_graph_view,
                         conn_view,
                         reached_first_view)

        skim_multiple_fields(origin_index,
                             nodes,
                             zones, # ???????????????
                             skims,
                             skim_matrix_view,
                             predecessors_view,
                             conn_view,
                             graph_skim_view,
                             reached_first_view,
                             w,
                             final_skim_matrices_view)
        if block_flows_through_centroids: # Unblocks the centroid if that is the case
            b = 1
            blocking_centroid_flows(b,
                                    origin_index,
                                    graph_fs_view,
                                    b_nodes_view,
                                    original_b_nodes_view)
    return orig

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef void skim_multiple_fields(long origin,
                                long nodes,
                                long zones,
                                long skims,
                                double[:, :] node_skims,
                                unsigned long [:] pred,
                                unsigned long [:] conn,
                                double[:, :] graph_costs,
                                unsigned long [:] reached_first,
                                long found,
                                double [:,:] final_skims) nogil:
    cdef unsigned long i, node, predecessor, connector, j

    # sets all skims to infinity
    for i in range(nodes):
        for j in range(skims):
            node_skims[i, j] = INFINITE

    # Zeroes the intrazonal cost
    for j in range(skims):
            node_skims[origin, j] = 0

    # Cascade skimming
    for i in xrange(1, found + 1):
        node = reached_first[i]

        # captures how we got to that node
        predecessor = pred[node]
        connector = conn[node]

        for j in range(skims):
            node_skims[node, j] = node_skims[predecessor, j] + graph_costs[connector, j]

    for i in range(zones):
        for j in range(skims):
            final_skims[i, j] = node_skims[i, j]


# ###########################################################################################################################
#############################################################################################################################
#Original Dijkstra implementation by Jake Vanderplas, taken from SciPy V0.11
#The old Pyrex syntax for loops was replaced with Python syntax
#Old Numpy Buffers were replaces with latest memory views interface to allow for the release of the GIL
# Path tracking arrays and skim arrays were also added to it
#############################################################################################################################
# ###########################################################################################################################

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef int path_finding(long origin,
                       double[:] graph_costs,
                       unsigned long [:] csr_indices,
                       unsigned long [:] graph_fs,
                       unsigned long [:] pred,
                       unsigned long [:] ids,
                       unsigned long [:] connectors,
                       unsigned long [:] reached_first) nogil:

    cdef unsigned int N = graph_costs.shape[0]
    cdef unsigned int M = pred.shape[0]

    cdef long i, k, j_source, j_current
    cdef ITYPE_t found = 0
    cdef long j
    cdef DTYPE_t weight

    cdef FibonacciHeap heap
    cdef FibonacciNode *v
    cdef FibonacciNode *current_node
    cdef FibonacciNode *nodes = <FibonacciNode*> malloc(N * sizeof(FibonacciNode))

    for i in range(M):
        pred[i] = -1
        connectors[i] = -1

    j_source = origin
    for k in range(N):
        initialize_node(&nodes[k], k)

    heap.min_node = NULL
    insert_node(&heap, &nodes[j_source])

    while heap.min_node:
        v = remove_min(&heap)
        reached_first[found] = v.index
        found += 1
        v.state = 1

        for j in xrange(graph_fs[v.index],graph_fs[v.index + 1]):
            j_current = csr_indices[j]
            current_node = &nodes[j_current]

            if current_node.state != 1:
                weight = graph_costs[j]
                if current_node.state == 2:
                    current_node.state = 3
                    current_node.val = v.val + weight
                    insert_node(&heap, current_node)
                    pred[j_current] = v.index
                    connectors[j_current] = ids[j]

                elif current_node.val > v.val + weight:
                    decrease_val(&heap, current_node,
                                 v.val + weight)
                    pred[j_current] = v.index
                    #The link that took us to such node
                    connectors[j_current] = ids[j]

    free(nodes)
    return found -1

######################################################################
# FibonacciNode structure
#  This structure and the operations on it are the nodes of the
#  Fibonacci heap.

#cdef enum FibonacciState:
#    SCANNED=1
#    NOT_IN_HEAP=2
#    IN_HEAP=3

cdef struct FibonacciNode:
    ITYPE_t index
    unsigned int rank
    #FibonacciState state
    unsigned int state
    DTYPE_t val
    FibonacciNode* parent
    FibonacciNode* left_sibling
    FibonacciNode* right_sibling
    FibonacciNode* children

cdef void initialize_node(FibonacciNode* node,
                          unsigned int index,
                          double val=0) nogil:
    # Assumptions: - node is a valid pointer
    #              - node is not currently part of a heap
    node.index = index
    node.val = val
    node.rank = 0
    node.state = 2
    node.parent = NULL
    node.left_sibling = NULL
    node.right_sibling = NULL
    node.children = NULL

cdef FibonacciNode* rightmost_sibling(FibonacciNode* node) nogil:
    # Assumptions: - node is a valid pointer
    cdef FibonacciNode* temp = node
    while(temp.right_sibling):
        temp = temp.right_sibling
    return temp

cdef FibonacciNode* leftmost_sibling(FibonacciNode* node) nogil:
    # Assumptions: - node is a valid pointer
    cdef FibonacciNode* temp = node
    while(temp.left_sibling):
        temp = temp.left_sibling
    return temp

cdef void add_child(FibonacciNode* node, FibonacciNode* new_child) nogil:
    # Assumptions: - node is a valid pointer
    #              - new_child is a valid pointer
    #              - new_child is not the sibling or child of another node
    new_child.parent = node

    if node.children:
        add_sibling(node.children, new_child)
    else:
        node.children = new_child
        new_child.right_sibling = NULL
        new_child.left_sibling = NULL
        node.rank = 1

cdef void add_sibling(FibonacciNode* node, FibonacciNode* new_sibling) nogil:
    # Assumptions: - node is a valid pointer
    #              - new_sibling is a valid pointer
    #              - new_sibling is not the child or sibling of another node
    cdef FibonacciNode* temp = rightmost_sibling(node)
    temp.right_sibling = new_sibling
    new_sibling.left_sibling = temp
    new_sibling.right_sibling = NULL
    new_sibling.parent = node.parent
    if new_sibling.parent:
        new_sibling.parent.rank += 1

cdef void remove(FibonacciNode* node) nogil:
    # Assumptions: - node is a valid pointer
    if node.parent:
        node.parent.rank -= 1
        if node.left_sibling:
            node.parent.children = node.left_sibling
        elif node.right_sibling:
            node.parent.children = node.right_sibling
        else:
            node.parent.children = NULL

    if node.left_sibling:
        node.left_sibling.right_sibling = node.right_sibling
    if node.right_sibling:
        node.right_sibling.left_sibling = node.left_sibling

    node.left_sibling = NULL
    node.right_sibling = NULL
    node.parent = NULL


######################################################################
# FibonacciHeap structure
#  This structure and operations on it use the FibonacciNode
#  routines to implement a Fibonacci heap

ctypedef FibonacciNode* pFibonacciNode

cdef struct FibonacciHeap:
    FibonacciNode* min_node
    pFibonacciNode[100] roots_by_rank  # maximum number of nodes is ~2^100.

cdef void insert_node(FibonacciHeap* heap,
                      FibonacciNode* node) nogil:
    # Assumptions: - heap is a valid pointer
    #              - node is a valid pointer
    #              - node is not the child or sibling of another node
    if heap.min_node:
        add_sibling(heap.min_node, node)
        if node.val < heap.min_node.val:
            heap.min_node = node
    else:
        heap.min_node = node

cdef void decrease_val(FibonacciHeap* heap,
                       FibonacciNode* node,
                       DTYPE_t newval) nogil:
    # Assumptions: - heap is a valid pointer
    #              - newval <= node.val
    #              - node is a valid pointer
    #              - node is not the child or sibling of another node
    #              - node is in the heap
    node.val = newval
    if node.parent and (node.parent.val >= newval):
        remove(node)
        insert_node(heap, node)
    elif heap.min_node.val > node.val:
        heap.min_node = node

cdef void link(FibonacciHeap* heap, FibonacciNode* node) nogil:
    # Assumptions: - heap is a valid pointer
    #              - node is a valid pointer
    #              - node is already within heap

    cdef FibonacciNode *linknode
    cdef FibonacciNode *parent
    cdef FibonacciNode *child

    if heap.roots_by_rank[node.rank] == NULL:
        heap.roots_by_rank[node.rank] = node
    else:
        linknode = heap.roots_by_rank[node.rank]
        heap.roots_by_rank[node.rank] = NULL

        if node.val < linknode.val or node == heap.min_node:
            remove(linknode)
            add_child(node, linknode)
            link(heap, node)
        else:
            remove(node)
            add_child(linknode, node)
            link(heap, linknode)

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cdef FibonacciNode* remove_min(FibonacciHeap* heap) nogil:
    # Assumptions: - heap is a valid pointer
    #              - heap.min_node is a valid pointer
    cdef FibonacciNode *temp
    cdef FibonacciNode *temp_right
    cdef FibonacciNode *out
    cdef unsigned int i

    # make all min_node children into root nodes
    if heap.min_node.children:
        temp = leftmost_sibling(heap.min_node.children)
        temp_right = NULL

        while temp:
            temp_right = temp.right_sibling
            remove(temp)
            add_sibling(heap.min_node, temp)
            temp = temp_right

        heap.min_node.children = NULL

    # choose a root node other than min_node
    temp = leftmost_sibling(heap.min_node)
    if temp == heap.min_node:
        if heap.min_node.right_sibling:
            temp = heap.min_node.right_sibling
        else:
            out = heap.min_node
            heap.min_node = NULL
            return out

    # remove min_node, and point heap to the new min
    out = heap.min_node
    remove(heap.min_node)
    heap.min_node = temp

    # re-link the heap
    for i in range(100):
        heap.roots_by_rank[i] = NULL

    while temp:
        if temp.val < heap.min_node.val:
            heap.min_node = temp
        temp_right = temp.right_sibling
        link(heap, temp)
        temp = temp_right

    return out
