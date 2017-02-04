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
 Updated:    12/25/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------

Original Algorithm for Shortest path (Dijkstra with a Fibonacci heap) was written by Jake Vanderplas <vanderplas@astro.washington.edu> under license: BSD, (C) 2012
 """

cimport numpy as np
cimport cython
from cython.parallel cimport parallel, prange, threadid
import multiprocessing as M
import thread
from multiprocessing.dummy import Pool as ThreadPool

VERSION = '0.3.3'
include 'parameters.pxi'
from libc.stdlib cimport abort, malloc, free

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def one_to_all(origin, demand, graph, result, curr_thread, no_gil=True):
    cdef int nodes, O, i
    cdef int critical_queries, link_extract_queries, query_type
    #We transform the python variables in Cython variables
    O = origin
    graph_fs = graph.fs

    if result.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    if O >= graph_fs.shape[0]:
        return "Node " + str(O) + " is outside the range of nodes in the graph"

    if graph_fs[O] == graph_fs[O+1]:
        return "Node " + str(O) + " does not exist in the graph"

    if VERSION != graph.__version__:
        return 'This graph was created for a different version of AequilibraE. Please re-create it'

    aux_link_flows = np.zeros(1, ITYPE)
    if result.critical_links['save']:
        critical_queries = len(result.critical_links['queries'])
        aux_link_flows = np.zeros(result.links, ITYPE)

    if result.link_extraction['save']:
        link_extract_queries = len(result.link_extraction['queries'])

    nodes = graph.num_nodes + 1

    new_b_nodes = blocking_centroid_flows(O, graph)
    # In order to release the GIL for this procedure, we create all the
    # memory views we will need
    cdef double [:] demand_view = demand

    cdef int [:] graph_fs_view = graph.fs
    cdef int [:] b_nodes_view = new_b_nodes
    cdef double [:] g_view = graph.cost
    cdef int [:] idsgraph_view = graph.ids
    cdef double [:, :] graph_skim_view = graph.skims

    cdef int [:] predecessors_view = result.predecessors[:, curr_thread]
    cdef int [:] conn_view = result.connectors[:, curr_thread]
    cdef double [:] Link_Loads_view = result.link_loads[:, curr_thread]
    cdef int [:] no_path_view = result.no_path[O, :, curr_thread]

    cdef double [:, :] skim_matrix_view = result.temporary_skims[:, :, curr_thread]
    cdef double [:, :] final_skim_matrices_view = result.skims[O, :, :]

    # path file variables
    cdef int [:] pred_view = result.path_file['results'][O,:,0]
    cdef int [:] c_view = result.path_file['results'][O,:,1]

    # select link variables
    cdef double [:, :] sel_link_view = result.critical_links['results'][O,:,:]
    cdef int [:] aux_link_flows_view = aux_link_flows
        #Now we do all procedures with NO GIL
    if no_gil:
        with nogil:
            a=assigone(O,
                       nodes,
                       demand_view,
                       g_view,
                       b_nodes_view,
                       graph_fs_view,
                       idsgraph_view,
                       graph_skim_view,
                       Link_Loads_view,
                       no_path_view,
                       skim_matrix_view,
                       predecessors_view,
                       conn_view,
                       final_skim_matrices_view)
    else:
        a=assigone(O,
                   nodes,
                   demand_view,
                   g_view,
                   b_nodes_view,
                   graph_fs_view,
                   idsgraph_view,
                   graph_skim_view,
                   Link_Loads_view,
                   no_path_view,
                   skim_matrix_view,
                   predecessors_view,
                   conn_view,
                   final_skim_matrices_view)

    if result.path_file['save']:
        put_path_file_on_disk(pred_view,
                              predecessors_view,
                              c_view,
                              conn_view)

    for i in range(critical_queries):
        critical_links_view = return_an_int_view(result.path_file['queries']['elements'][i])
        query_type = 0
        if result.path_file['queries'][ type][i] == "or":
            query_type = 1
        perform_select_link_analysis(O,
                                     nodes,
                                     demand_view,
                                     predecessors_view,
                                     conn_view,
                                     aux_link_flows_view,
                                     sel_link_view,
                                     query_type)
    return origin

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
def reblocks_matrix(matrix, hashtable, new_max):
    cdef int i, j
    cdef int k = matrix.shape[0]
    cdef int l = matrix.shape[1]

    new_mat = np.zeros((int(new_max), int(new_max)), dtype = np.float64)

    for i in range(k):
        for j in range(l):
            new_mat[hashtable[i], hashtable[j]] = matrix[i,j]
    return new_mat



cdef blocking_centroid_flows(int O, graph):
    cdef int i, centroids

    centroids = graph.centroids +1
    cdef int [:] fs = graph.fs

    if graph.block_centroid_flows:
        new_b_nodes = np.array(graph.b_node, copy=True)

        if O < graph.centroids:
            for i in xrange(0, fs[O]):
                new_b_nodes[i] = O

            for i in xrange(fs[O+1], fs[centroids]):
                new_b_nodes[i] = O
        else:
            for i in xrange(0, fs[centroids]):
                new_b_nodes[i] = O
    else:
        new_b_nodes = graph.b_node

    return new_b_nodes

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cpdef int skims_one(int origin,
                   int block_centroid_flow,
                   double[:] graph_costs,
                   int [:] csr_indices,
                   int [:] csr_indptr,
                   int [:] ids_graph,
                   double[:,:] graph_skim,
                   int [:] no_path,
                   double[:,:] skim_matrix,
                   int [:] predecessors,
                   int [:] conn,
                   double[:,:] final_skim_matrix) nogil:

    cdef ITYPE_t links, i, j, w

    cdef int skims = graph_skim.shape[1]
    cdef int zones = final_skim_matrix.shape[0]
    cdef int N = graph_costs.shape[0] #Nodes in our graph (The sparse graph has an overhead of one on the shape)

    #------------------------------
    # initializes skim_matrix for output
    # initializes predecessors  and link connectors for output
    for i in range(N):
        predecessors[i]=-1
        conn[i]=-1
        for j in range(skims):
            skim_matrix[i,j]=INFINITE

    for j in range(skims):
        skim_matrix[origin,j]=0

    #------------------------------
    #Runs the shortest path algorithm to capture the SPath
    w = path_finding(origin,
                           graph_costs,
                           csr_indices,
                           csr_indptr,
                           predecessors,
                           ids_graph,
                           conn,
                           graph_skim,
                           skim_matrix)
    #------------------------------
    #----------------------------------------------------------------------------------------------



    return 1



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


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cpdef int assigone(int origin,
                   int nodes,
                   double[:] demand,
                   double[:] graph_costs,
                   int [:] csr_indices,
                   int [:] csr_indptr,
                   int [:] ids_graph,
                   double[:,:] graph_skim,
                   double[:] Link_Loads,
                   int [:] no_path,
                   double[:,:] skim_matrix,
                   int [:] predecessors,
                   int [:] conn,
                   double[:,:] final_skim_matrix) nogil:

    cdef int links, i, j, w

    cdef int skims = graph_skim.shape[1]
    cdef int zones = demand.shape[0]
    cdef int N = predecessors.shape[0] #Nodes in our graph (The sparse graph has an overhead of one on the shape)

    # If the origin is outside the range of nodes
    if origin >= N:
        return 0

    #------------------------------
    # initializes skim_matrix for output
    # initializes predecessors  and link connectors for output

    for i in range(N):
        predecessors[i] = -1
        conn[i] = -1
        for j in range(skims):
            skim_matrix[i,j] = INFINITE

    for j in range(skims):
        skim_matrix[origin,j] = 0

    #with gil:
    #    #print 'starting dijkstra'
    #------------------------------
    #Runs the shortest path algorithm to capture the SPath
    w = path_finding(origin,
                       graph_costs,
                       csr_indices,
                       csr_indptr,
                       predecessors,
                       ids_graph,
                       conn,
                       graph_skim,
                       skim_matrix)
    #------------------------------
    #----------------------------------------------------------------------------------------------
    #performs the assignment itself
    #with gil:
    #    #print 'starting assign'

    w = network_loading(origin,
                  nodes,
                  demand,
                  predecessors,
                  conn,
                  Link_Loads,
                  no_path)

    w = _copy_skims(skim_matrix,
                  final_skim_matrix)

    '''_select_link(links


    '''
    return 1

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef int network_loading(int origin,
                      int nodes,
                      double[:] demand,
                      int [:] pred,
                      int [:] conn,
                      double[:] Link_Loads,
                      int [:] no_path) nogil:

    cdef unsigned int t_origin
    cdef ITYPE_t c, j, i, p,
    cdef unsigned int dests = demand.shape[0]

    for i in range(dests):
        if demand[i] > 0:
            p = pred[i]
            if pred[i] < 0:
                if i != origin:
                    no_path[i] = -1
            else:
                j = i
                while p >= 0:
                    c = conn[j]
                    Link_Loads[c] = Link_Loads[c] + demand[i]
                    j = p
                    p = pred[j]
    return 1


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
cdef int _copy_skims(double[:,:] skim_matrix,  #Skim matrix computed from one origin to all nodes
                      double[:,:] final_skim_matrix) nogil:  #Skim matrix computed for one origin to all other centroids only

    cdef int i, j
    cdef int N=final_skim_matrix.shape[0]
    cdef int skims=final_skim_matrix.shape[1]

    for i in range(N):
        for j in range(skims):
            final_skim_matrix[i,j]=skim_matrix[i,j]
    return 1

# ###########################################################################################################################
#############################################################################################################################
#Original Dijkstra implementation by Jake Vanderplas', taken from SciPy V0.11
#The old Pyrex syntax for loops was replaced with Python syntax
#Old Numpy Buffers were replaces with latest memmory views interface to allow for the release of the GIL
# Path tracking arrays and skim arrays were also added to it
#############################################################################################################################
# ###########################################################################################################################

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef int path_finding(int origin,
                             double[:] graph_costs,
                             int [:] csr_indices,
                             int [:] csr_indptr,
                             int [:] pred,
                             int [:] ids,
                             int [:] connectors,
                             double[:,:] skim_costs,
                             double[:,:] skim_matrix) nogil:

    cdef unsigned int N = graph_costs.shape[0]

    cdef unsigned int skims = skim_costs.shape[1]

    cdef int i, k, j_source, j_current
    cdef int j
    cdef double weight

    cdef FibonacciHeap heap
    cdef FibonacciNode *v
    cdef FibonacciNode *current_node
    cdef FibonacciNode *nodes = <FibonacciNode*> malloc(N * sizeof(FibonacciNode))


    j_source = origin
    for k in range(skims):
        skim_matrix[j_source,k]=0

    for k in range(N):
        initialize_node(&nodes[k], k)

    heap.min_node = NULL
    insert_node(&heap, &nodes[j_source])

    #with gil:
        #print "start loop"

    while heap.min_node:
        v = remove_min(&heap)
        v.state = 1
        #with gil:
            #print v.index, csr_indptr[v.index], csr_indptr[v.index + 1]
        for j in xrange(csr_indptr[v.index],csr_indptr[v.index + 1]):
            j_current = csr_indices[j]
            current_node = &nodes[j_current]

            if current_node.state != 1:
                weight = graph_costs[j]
                if current_node.state == 2:
                    current_node.state = 3
                    current_node.val = v.val + weight
                    insert_node(&heap, current_node)
                    pred[j_current] = v.index
                    #The link that took us to such node
                    connectors[j_current] = ids[j]

                    #The skims
                    for k in range(skims):
                        skim_matrix[j_current,k]=skim_matrix[v.index,k]+skim_costs[j,k]
                elif current_node.val > v.val + weight:
                    decrease_val(&heap, current_node,
                                 v.val + weight)
                    pred[j_current] = v.index
                    #The link that took us to such node
                    connectors[j_current] = ids[j]

                    #The skims
                    for k in range(skims):
                        skim_matrix[j_current,k]=skim_matrix[v.index,k]+skim_costs[j,k]
        #v has now been scanned: add the distance to the results
    free(nodes)
    return 1

######################################################################
# FibonacciNode structure
#  This structure and the operations on it are the nodes of the
#  Fibonacci heap.

#cdef enum FibonacciState:
#    SCANNED=1
#    NOT_IN_HEAP=2
#    IN_HEAP=3

cdef struct FibonacciNode:
    unsigned int index
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
