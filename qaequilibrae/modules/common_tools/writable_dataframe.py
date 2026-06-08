import pandas as pd
import numpy as np


def make_writable_network_dataframe(df: pd.DataFrame) -> pd.DataFrame:

    # Force required graph columns to exact writable NumPy dtypes
    dtype_map = {
        "link_id": np.int64,
        "a_node": np.int64,
        "b_node": np.int64,
        "direction": np.int8,
    }

    data = {}

    for col in df.columns:
        series = df[col]

        if col in dtype_map:
            dtype = dtype_map[col]
        elif pd.api.types.is_integer_dtype(series):
            dtype = np.int64
        elif pd.api.types.is_float_dtype(series):
            dtype = np.float64
        elif pd.api.types.is_numeric_dtype(series):
            dtype = np.float64
        else:
            dtype = object

        # The .tolist() step intentionally breaks any read-only / extension-array backing.
        arr = np.asarray(series.tolist(), dtype=dtype)

        # Require:
        # C = C-contiguous
        # W = writable
        # O = owns its own memory
        arr = np.require(arr, dtype=dtype, requirements=["C", "W", "O"])

        data[col] = arr

    return pd.DataFrame(data, copy=False)