from AoN cimport FibonacciNode, initialize_node, add_child, add_sibling, insert_node
from AoN cimport *

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
        return "Node " + str(origin) + " is outside the range of nodes in the graph"

    if graph.fs[origin] == graph.fs[origin+1]:
        return "Node " + str(origin) + " does not exist in the graph"

    if VERSION != graph.__version__:
        return 'This graph was created for a different version of AequilibraE. Please re-create it'
    #We transform the python variables in Cython variables
    O = origin
    D = destination
    new_b_nodes = blocking_centroid_flows(O, graph)
    graph_fs = graph.fs
    graph_costs = graph.cost
    graph_skim = graph.skims
    idsgraph = graph.graph['link_id']
    nodes = graph.num_nodes


    predecessors = results.predecessors
    conn = results.connectors
    temp_skims = results.temporary_skims
    skims = temp_skims.shape[1]

    #In order to release the GIL for this procedure, we create all the
    #memmory views we will need
    #print "creating views"
    cdef double [:] g_view = graph_costs
    cdef int [:] b_nodes_view = blocking_centroid_flows(O, graph)
    cdef int [:] graph_fs_view = graph_fs
    cdef double [:, :] graph_skim_view = graph_skim
    cdef int [:] idsgraph_view = idsgraph


    cdef int [:] predecessors_view = predecessors
    cdef int [:] conn_view = conn
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
                                         int [:] csr_indices,
                                         int [:] csr_indptr,  # graph forward star
                                         int [:] pred,
                                         int [:] ids,
                                         int [:] connectors,
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
