"""
 -----------------------------------------------------------------------------------------------------------
 Package:    AequilibraE

 Name:       Reblocking matrix
 Purpose:    Allowing arbitrary ODs in desire lines

 Original Author:  Pedro Camargo (c@margo.co)
 Contributors:
 Last edited by: Pedro Camrgo

 Website:    www.AequilibraE.com
 Repository:  https://github.com/AequilibraE/AequilibraE

 Created:    05/Feb/2017
 Updated:
 Copyright:   (c) AequilibraE authors
 Licence:     See LICENSE.TXT
 -----------------------------------------------------------------------------------------------------------
 """

cimport numpy as np

@cython.wraparound(False)
@cython.embedsignature(True)
@cython.boundscheck(False)
def reblocks_matrix(matrix, hash_table, new_max):
    cdef int i, j
    cdef int k = matrix.shape[0]
    cdef int l = matrix.shape[1]

    new_mat = np.zeros((int(new_max), int(new_max)), dtype = np.float64)

    for i in range(k):
        for j in range(l):
            new_mat[hash_table[i], hash_table[j]] = matrix[i, j]
    return new_mat
