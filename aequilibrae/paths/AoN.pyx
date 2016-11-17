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
 Updated:    30/09/2016
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------

Original Algorithm for Shortest path (Dijkstra with a Fibonacci heap) was written by Jake Vanderplas <vanderplas@astro.washington.edu> under license: BSD, (C) 2012

Codes for route ennumeration, DAG construction and Link nesting were written by Pedro Camargo (2013) and have all their rights reserved to the author

 """

cimport numpy as np
cimport cython
from cython.parallel cimport parallel, prange, threadid
import multiprocessing as M
import thread
from multiprocessing.dummy import Pool as ThreadPool

include 'parameters.pxi'
from libc.stdlib cimport abort, malloc, free

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)


def path_computation(origin,destination,graph, results):
    cdef ITYPE_t nodes, O, D, p
    cdef int i, j, skims, a

    if results.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    # Consistency checks
    if origin >= graph.fs.shape[0]:
        return "Node " + str(O) + " is outside the range of nodes in the graph"

    if graph.fs[origin] == graph.fs[origin+1]:
        return "Node " + str(origin) + " does not exist in the graph"

    O = origin
    new_b_nodes = blocking_centroid_flows(O, graph)
    graph_fs = graph.fs
    graph_costs = graph.cost
    graph_skim = graph.skims
    idsgraph = graph.graph['link_id']
    nodes = graph.num_nodes

    #We transform the python variables in Cython variables
    O = origin
    D = destination

    predecessors = results.predecessors
    conn = results.connectors
    temp_skims = results.temporary_skims
    skims = temp_skims.shape[1]

    #In order to release the GIL for this procedure, we create all the
    #memmory views we will need
    #print "creating views"
    cdef double [:] g_view = graph_costs
    cdef long long [:] b_nodes_view = blocking_centroid_flows(O, graph)
    cdef long long [:] graph_fs_view = graph_fs
    cdef double [:, :] graph_skim_view = graph_skim
    cdef long long  [:] idsgraph_view = idsgraph


    cdef long long [:] predecessors_view = predecessors
    cdef long long [:] conn_view = conn
    cdef double [:, :] skim_matrix_view = temp_skims

    #Now we do all procedures with NO GIL
    #print "start computation"
    with nogil:
        # initializes skim_matrix for output
        # initializes predecessors  and link connectors for output
        for i in prange(nodes):
            predecessors_view[i] = -1
            conn_view[i] = -1
            for j in range(skims):
                skim_matrix_view[i, j] = INFINITE

        for j in prange(skims):
            skim_matrix_view[O, j] = 0

    a=_dijkstra_directed_single_pair(O,
                                     D,
                                     g_view,
                                     b_nodes_view,
                                     graph_fs_view,
                                     predecessors_view,
                                     idsgraph_view,
                                     conn_view,
                                     graph_skim_view,
                                     skim_matrix_view)

    if D < results.nodes:
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
    else:
        return 'Destination node out of range. SP tree was not returned'
    return a


@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def one_to_all(origin, demand, graph, result, curr_thread, no_gil=True):
    cdef int nodes, O, i
    ##print "start one to all"
    ##print "Checking bounds"
    #We transform the python variables in Cython variables
    O = origin
    graph_fs = graph.fs

    if result.__graph_id__ != graph.__id__:
        return "Results object not prepared. Use --> results.prepare(graph)"

    if O >= graph_fs.shape[0]:
        return "Node " + str(O) + " is outside the range of nodes in the graph"

    if graph_fs[O] == graph_fs[O+1]:
        return "Node " + str(O) + " does not exist in the graph"

    nodes = graph.num_nodes + 1

    ##print "Blocking through centroids"
    new_b_nodes = blocking_centroid_flows(O, graph)
    #In order to release the GIL for this procedure, we create all the
    #memmory views we will need
    cdef double [:] demand_view = demand

    cdef long long [:] graph_fs_view = graph.fs
    cdef long long [:] b_nodes_view = new_b_nodes
    cdef double [:] g_view = graph.cost
    cdef long long  [:] idsgraph_view = graph.ids
    cdef double [:, :] graph_skim_view = graph.skims

    cdef long long [:] predecessors_view = result.predecessors[:, curr_thread]
    cdef long long [:] conn_view = result.connectors[:, curr_thread]
    cdef double [:] Link_Loads_view = result.link_loads[:, curr_thread]
    cdef long long [:] no_path_view = result.no_path[O, :, curr_thread]

    cdef double [:, :] skim_matrix_view = result.temporary_skims[:, :, curr_thread]
    cdef double [:, :] final_skim_matrices_view = result.skims[O, :, :]

        #Now we do all procedures with NO GIL
    ##print "assigone"
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
    return origin


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



cdef blocking_centroid_flows(O, graph):
    cdef int i, centroids

    centroids = graph.centroids +1
    cdef long long [:] fs = graph.fs

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
                   long long [:] csr_indices,
                   long long [:] csr_indptr,
                   long long [:] ids_graph,
                   double[:,:] graph_skim,
                   long long [:] no_path,
                   double[:,:] skim_matrix,
                   long long [:] predecessors,
                   long long [:] conn,
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
    w = _dijkstra_directed(origin,
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
                     long long [:] no_path) nogil:  #Skim matrix computed for one origin to all other centroids only

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
                   long long [:] csr_indices,
                   long long [:] csr_indptr,
                   long long [:] ids_graph,
                   double[:,:] graph_skim,
                   double[:] Link_Loads,
                   long long [:] no_path,
                   double[:,:] skim_matrix,
                   long long [:] predecessors,
                   long long [:] conn,
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
    w = _dijkstra_directed(origin,
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

    w = _assignsAON(origin,
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
cpdef int _assignsAON(int origin,
                      int nodes,
                      double[:] demand,
                      long long [:] pred,
                      long long [:] conn,
                      double[:] Link_Loads,
                      long long [:] no_path) nogil:

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
cpdef int _dijkstra_directed_single_pair(int origin,
                                         int dest,
                                         double[:] graph_costs,
                                         long long [:] csr_indices,
                                         long long [:] csr_indptr,  # graph forward star
                                         long long [:] pred,
                                         long long [:] ids,
                                         long long [:] connectors,
                                         double[:,:] skim_costs,
                                         double[:,:] skim_matrix):

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
        skim_matrix[j_source,k] = 0

    for k in range(N):
        initialize_node(&nodes[k], k)

    heap.min_node = NULL
    insert_node(&heap, &nodes[j_source])
    while heap.min_node:
        v = remove_min(&heap)
        v.state = 1
        if v.index == dest:
            break
        for j in xrange(csr_indptr[v.index], csr_indptr[v.index + 1]):
            j_current = csr_indices[j]
            current_node = &nodes[j_current]
            #print v.index, j_current, current_node.state, current_node.index
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
                        skim_matrix[j_current, k] = skim_matrix[v.index, k] + skim_costs[j, k]
                elif current_node.val > v.val + weight:
                    decrease_val(&heap, current_node,
                                 v.val + weight)
                    pred[j_current] = v.index
                    #The link that took us to such node
                    connectors[j_current] = ids[j]

                    #The skims
                    for k in range(skims):
                        skim_matrix[j_current, k] = skim_matrix[v.index, k] + skim_costs[j, k]
        #v has now been scanned: add the distance to the results
    free(nodes)
    return 1



@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False) # turn of bounds-checking for entire function
cpdef int _dijkstra_directed(int origin,
                             double[:] graph_costs,
                             long long [:] csr_indices,
                             long long [:] csr_indptr,
                             long long [:] pred,
                             long long [:] ids,
                             long long [:] connectors,
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

# def all_to_all(demand,graph, Link_Loads, no_path,skim_matrix, predecessors, conn, temp_skims, cores):
#     cdef int nodes, a, zones, O, links, ct, i, block_centroid_flow
#
#
#     graph_costs = graph.cost
#     b_nodes = graph.b_node
#     graph_fs = graph.fs
#     graph_skim = graph.skims
#     idsgraph = graph.ids
#     block_centroid_flow = graph.block_centroid_flow
#
#     #We transform the python variables in Cython variables
#     zones=demand.shape[0]
#     links=b_nodes.shape[0]
#     nodes=graph_costs.shape[0]
#
#     #We need to create a new cost array in order to not allow
#     #flows through the centroids
#     #g=graph_costs.copy()
#
#     #And we also have some thread-specific arrays for the shortest path three to be constructed
#     #predecessors = np.empty(nodes, dtype=ITYPE)
#     #conn = np.empty(nodes, dtype=ITYPE)
#     #temp_skims=np.empty((nodes, skims), dtype=DTYPE)
#
#
#     #In order to release the GIL for this procedure, we create all the
#     #memmory views we will need
#     cdef long long [:] graph_fs_view = graph_fs
#     cdef long long [:] b_nodes_view = b_nodes
#     cdef double [:] g_view =graph_costs
#     cdef long long  [:] idsgraph_view = idsgraph
#     cdef double [:,:] graph_skim_view = graph_skim
#
#     cdef long long [:,:] predecessors_view = predecessors
#     cdef long long [:,:] conn_view = conn
#
#     cdef double [:,:] demand_view=demand
#
#     cdef double [:,:] Link_Loads_view=Link_Loads
#     cdef long long [:,:] no_path_view=no_path
#     cdef double [:,:,:] skim_matrix_view = temp_skims
#     cdef double [:,:,:] final_skim_matrices_view=skim_matrix
#
#
#     for O in prange(zones, nogil=True, num_threads=cores):
#         ct=cython.parallel.threadid()
#         a=assigone(O,
#                  nodes,
#                  demand_view[O,:],
#                  g_view,
#                  b_nodes_view,
#                  graph_fs_view,
#                  idsgraph_view,
#                  graph_skim_view,
#                  Link_Loads_view[:,ct],
#                  no_path_view[O,:],
#                  skim_matrix_view[:,:,ct],
#                  predecessors_view[:,ct],
#                  conn_view[:,ct],
#                  final_skim_matrices_view[O,:,:])
#
#     for i in prange(links, nogil=True, num_threads=cores):
#         a=_total_assignment(Link_Loads_view[i,:])
#
#     return 1
#
# @cython.wraparound(False)
# @cython.embedsignature(True)
# @cython.boundscheck(False)
# cpdef int _total_assignment(double[:] Link_Loads) nogil:
#     cdef int i
#     cdef int j = Link_Loads.shape[0]
#     for i in xrange (1,j):
#         Link_Loads[0]=Link_Loads[0]+Link_Loads[i]
#     return 1
#
# def Some_to_all(Oi,Oj,demand,graph, Link_Loads, no_path,skim_matrix, predecessors, conn, temp_skims):
#     cdef int nodes, a, zones, O, links, ct, i, j, block_centroid_flow
#
#     block_centroid_flow = graph.block_centroid_flow
#     graph_costs = graph.cost
#     b_nodes = graph.b_node
#     graph_fs = graph.fs
#     graph_skim = graph.skims
#     idsgraph = graph.ids
#
#     #We transform the python variables in Cython variables
#     i=Oi
#     j=Oj
#     nodes=graph_costs.shape[0]
#     zones=demand.shape[0]
#     links=b_nodes.shape[0]
#     skims=skim_matrix.shape[1]
#
#
#     #And we also have some thread-specific arrays for the shortest path three to be constructed
#     #predecessors = np.empty(nodes, dtype=ITYPE)
#     #conn = np.empty(nodes, dtype=ITYPE)
#     #temp_skims=np.empty((nodes, skims), dtype=DTYPE)
#     #cdef double [:] g_view = g
#
#     #In order to release the GIL for this procedure, we create all the
#     #memmory views we will need
#     cdef long long [:] graph_fs_view = graph_fs
#     cdef long long [:] b_nodes_view = b_nodes
#     cdef double [:] g_view =graph_costs
#     cdef long long  [:] idsgraph_view = idsgraph
#
#
#     cdef long long [:] predecessors_view = predecessors
#     cdef long long [:] conn_view = conn
#     cdef double [:,:] demand_view=demand
#     cdef double [:,:] graph_skim_view = graph_skim
#
#     cdef double [:] Link_Loads_view=Link_Loads
#     cdef long long [:,:] no_path_view=no_path
#
#     cdef double [:,:,:] skim_matrix_view = temp_skims
#     cdef double [:,:] final_skim_matrices_view=skim_matrix
#
#
#     #Now we do all procedures with NO GIL
#     with nogil:
#         #We remove the connectors
#         # a=_removes_connectors(g_view,  #graph_costs
#                               # graph_fs_view,
#                               # O,
#                               # zones)
#             for O in xrange(i,j):
#                 a=assigone(O,
#                          nodes,
#                          demand_view[O,:],
#                          g_view,
#                          b_nodes_view,
#                          graph_fs_view,
#                          idsgraph_view,
#                          graph_skim_view,
#                          Link_Loads_view,
#                          no_path_view[O,:],
#                          skim_matrix_view[O,:,:],
#                          predecessors_view,
#                          conn_view,
#                          final_skim_matrices_view)
#     return O
#
#
# def empty_function(i):
#     cdef int j
#     j = i
#     with nogil:
#         j = _empty_function(j)
#
# cpdef int _empty_function(int i) nogil:
#     cdef int j, k
#
#     for j in range(10):
#         k = j ** j
#     return k