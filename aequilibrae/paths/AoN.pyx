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
 Updated:    25/Feb/2017
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------

Original Algorithm for Shortest path (Dijkstra with a Fibonacci heap) was written by Jake Vanderplas <vanderplas@astro.washington.edu> under license: BSD, (C) 2012
 """

cimport numpy as np
cimport cython

include 'parameters.pxi'
from libc.stdlib cimport abort, malloc, free

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def one_to_all(origin, demand, graph, result, aux_result, curr_thread):
    cdef int nodes, O, i, centroids, block_flows_through_centroids
    cdef int critical_queries = 0
    cdef int link_extract_queries, query_type
    #We transform the python variables in Cython variables
    O = origin
    graph_fs = graph.fs

    if result.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    if O >= result.zones:
        return "Centroid " + str(O) + " is outside the range of zones in the graph"

    if O > graph.num_nodes:
        return "Centroid " + str(O) + " does not exist in the graph"

    if graph_fs[O] == graph_fs[O+1]:
        return "Centroid " + str(O) + " does not exist in the graph"

    if VERSION != graph.__version__:
        return 'This graph was created for a different version of AequilibraE. Please re-create it'

    if result.critical_links['save']:
        critical_queries = len(result.critical_links['queries'])
        aux_link_flows = np.zeros(result.links, ITYPE)
    else:
        aux_link_flows = np.zeros(1, ITYPE)

    if result.link_extraction['save']:
        link_extract_queries = len(result.link_extraction['queries'])

    nodes = graph.num_nodes + 1
    centroids = graph.centroids
    block_flows_through_centroids = graph.block_centroid_flows

    # In order to release the GIL for this procedure, we create all the
    # memory views we will need
    cdef double [:] demand_view = demand

    # views from the graph
    cdef int [:] graph_fs_view = graph.fs
    cdef double [:] g_view = graph.cost
    cdef int [:] ids_graph_view = graph.ids
    cdef int [:] original_b_nodes_view = graph.b_node
    cdef double [:, :] graph_skim_view = graph.skims

    # views from the result object
    cdef double [:, :] final_skim_matrices_view = result.skims[O, :, :]
    cdef int [:] no_path_view = result.no_path[O, :]

    # views from the aux-result object
    cdef int [:] predecessors_view = aux_result.predecessors[:, curr_thread]
    cdef double [:, :] skim_matrix_view = aux_result.temporary_skims[:, :, curr_thread]
    cdef int [:] reached_first_view = aux_result.reached_first[:, curr_thread]
    cdef int [:] conn_view = aux_result.connectors[:, curr_thread]
    cdef double [:] link_loads_view = aux_result.temp_link_loads[:, curr_thread]
    cdef double [:] node_load_view = aux_result.temp_node_loads[:, curr_thread]
    cdef int [:] b_nodes_view = aux_result.temp_b_nodes

    # path file variables
    cdef int [:] pred_view = result.path_file['results'][O,:,0]
    cdef int [:] c_view = result.path_file['results'][O,:,1]

    # select link variables
    cdef double [:, :] sel_link_view = result.critical_links['results'][O,:,:]
    cdef int [:] aux_link_flows_view = aux_link_flows

    #Now we do all procedures with NO GIL
    with nogil:
        if block_flows_through_centroids:
            blocking_centroid_flows(O,
                                    centroids,
                                    graph_fs_view,
                                    original_b_nodes_view,
                                    b_nodes_view)
        w = path_finding(O,
                         g_view,
                         b_nodes_view,
                         graph_fs_view,
                         predecessors_view,
                         ids_graph_view,
                         conn_view,
                         reached_first_view)

        network_loading(O,
                        nodes,
                        demand_view,
                        predecessors_view,
                        conn_view,
                        link_loads_view,
                        no_path_view,
                        reached_first_view,
                        node_load_view,
                        w)

        # _copy_skims(skim_matrix_view,
        #             final_skim_matrices_view)

        '''_select_link(links


        '''



    # if result.path_file['save']:
    #     put_path_file_on_disk(pred_view,
    #                           predecessors_view,
    #                           c_view,
    #                           conn_view)
    #
    # for i in range(critical_queries):
    #     critical_links_view = return_an_int_view(result.path_file['queries']['elements'][i])
    #     query_type = 0
    #     if result.path_file['queries'][ type][i] == "or":
    #         query_type = 1
    #     perform_select_link_analysis(O,
    #                                  nodes,
    #                                  demand_view,
    #                                  predecessors_view,
    #                                  conn_view,
    #                                  aux_link_flows_view,
    #                                  sel_link_view,
    #                                  query_type)
    return origin

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef void network_loading(int origin,
                      int nodes,
                      double[:] demand,
                      int [:] pred,
                      int [:] conn,
                      double[:] link_loads,
                      int [:] no_path,
                      int [:] reached_first,
                      double [:] node_load,
                      int found) nogil:

    cdef unsigned int i, node, predecessor, connector
    cdef unsigned int zones = demand.shape[0]
    cdef int N = node_load.shape[0]

    # Clean the node load array
    for i in range(N):
        node_load[i] = 0

    # Loads the demand to the centroids
    for i in range(zones):
        node_load[i] = demand[i]

    #Recursevely cascades to the origin
    for i in xrange(found, 0, -1):
        node = reached_first[i]

        # captures how we got to that node
        predecessor = pred[node]
        connector = conn[node]

        # loads the flow to the link
        link_loads[connector] += node_load[node]

        # Cascades the load from the node to their predecessor
        node_load[predecessor] += node_load[node]

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cdef void _copy_skims(double[:,:] skim_matrix,  #Skim matrix computed from one origin to all nodes
                      double[:,:] final_skim_matrix) nogil:  #Skim matrix computed for one origin to all other centroids only

    cdef int i, j
    cdef int N=final_skim_matrix.shape[0]
    cdef int skims=final_skim_matrix.shape[1]

    for i in range(N):
        for j in range(skims):
            final_skim_matrix[i,j]=skim_matrix[i,j]


cdef return_an_int_view(input):
    cdef int [:] critical_links_view = input
    return critical_links_view


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cpdef void perform_select_link_analysis(int origin,
                                        int nodes,
                                        double[:] demand,
                                        int [:] pred,
                                        int [:] conn,
                                        int [:] aux_link_flows,
                                        double [:, :] critical_array,
                                        int query_type) nogil:
    cdef unsigned int t_origin
    cdef ITYPE_t c, j, i, p,
    cdef unsigned int dests = demand.shape[0]
    cdef unsigned int q = critical_array.shape[0]

    for j in range(dests):
        if demand[j] > 0:
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
cpdef void put_path_file_on_disk(int [:] pred,
                                 int [:] predecessors,
                                 int [:] conn,
                                 int [:] connectors) nogil:
    cdef int i
    cdef int k = pred.shape[0]

    for i in range(k):
        pred[i] = predecessors[i]
        conn[i] = connectors[i]


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cdef void blocking_centroid_flows(int O,
                                  int centroids,
                                  int [:] fs,
                                  int [:] b_node,
                                  int [:] temp_b_nodes) nogil:
    cdef int i

    centroids += 1

    # reset array
    for i in xrange(fs[0], fs[centroids]):
        temp_b_nodes[i] = b_node[i]

    if O < centroids - 1:
        for i in xrange(0, fs[O]):
            temp_b_nodes[i] = O

        for i in xrange(fs[O+1], fs[centroids]):
            temp_b_nodes[i] = O
    else:
        for i in xrange(0, fs[centroids]):
            temp_b_nodes[i] = O


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def path_computation(origin,destination,graph, results):
    cdef ITYPE_t nodes, O, D, p, centroids
    cdef int i, j, skims, a

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
    O = origin
    D = destination
    nodes = graph.num_nodes

     # initializes skim_matrix for output
    # initializes predecessors  and link connectors for output
    results.predecessors.fill(-1)
    results.connectors.fill(-1)
    results.temporary_skims.fill(-1)
    skims = results.temporary_skims.shape[1]

    for j in range(skims):
        results.temporary_skims[O, j] = 0


    #In order to release the GIL for this procedure, we create all the
    #memmory views we will need
    #print "creating views"
    cdef double [:] g_view = graph.cost
    cdef int [:] original_b_nodes_view = graph.b_node
    cdef int [:] graph_fs_view = graph.fs
    cdef double [:, :] graph_skim_view = graph.skims
    cdef int [:] ids_graph_view = graph.graph['link_id']
    centroids = graph.centroids

    cdef int [:] predecessors_view = results.predecessors
    cdef int [:] conn_view = results.connectors
    cdef double [:, :] skim_matrix_view = results.temporary_skims
    cdef int [:] reached_first_view = results.reached_first

    new_b_nodes = graph.b_node.copy()
    cdef int [:] b_nodes_view = new_b_nodes


    #Now we do all procedures with NO GIL
    #print "start computation"
    with nogil:
        blocking_centroid_flows(O,
                                centroids,
                                graph_fs_view,
                                original_b_nodes_view,
                                b_nodes_view)

        w = path_finding(O,
                         g_view,
                         b_nodes_view,
                         graph_fs_view,
                         predecessors_view,
                         ids_graph_view,
                         conn_view,
                         reached_first_view)

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
cdef int _copy_skims_check_path(double[:,:] skim_matrix,  #Skim matrix computed from one origin to all nodes
                     double[:,:] final_skim_matrix,
                     int [:] no_path) nogil:  #Skim matrix computed for one origin to all other centroids only

    cdef int i, j
    cdef int N = final_skim_matrix.shape[0]
    cdef int skims = final_skim_matrix.shape[1]

    for i in range(N):
        if skim_matrix[i,0] == INFINITE:
            no_path[j] = -1
        for j in range(skims):
            final_skim_matrix[i,j] = skim_matrix[i,j]

    return 1



# ###########################################################################################################################
#############################################################################################################################
#Original Dijkstra implementation by Jake Vanderplas', taken from SciPy V0.11
#The old Pyrex syntax for loops was replaced with Python syntax
#Old Numpy Buffers were replaces with latest memory views interface to allow for the release of the GIL
# Path tracking arrays and skim arrays were also added to it
#############################################################################################################################
# ###########################################################################################################################

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef int path_finding(int origin,
                       double[:] graph_costs,
                       int [:] csr_indices,
                       int [:] graph_fs,
                       int [:] pred,
                       int [:] ids,
                       int [:] connectors,
                       int [:] reached_first) nogil:

    cdef unsigned int N = graph_costs.shape[0]
    cdef unsigned int M = pred.shape[0]

    cdef int i, k, j_source, j_current
    cdef ITYPE_t found = 0
    cdef int j
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
