import numpy as np 

DTYPE = np.float64
ctypedef np.float64_t DTYPE_t

ITYPE = np.int32
ctypedef np.int32_t ITYPE_t

# EPS is the precision of DTYPE
cdef DTYPE_t DTYPE_EPS = 1E-15

# NULL_IDX is the index used in predecessor matrices to store a non-path
cdef ITYPE_t NULL_IDX = -9999

cdef double INFINITE = 1.79769313e+308

VERSION = "0.3.5"
SUB_VERSION = '0'
