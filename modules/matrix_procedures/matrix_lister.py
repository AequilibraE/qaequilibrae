import importlib.util as iutil
import os

import pandas as pd
from aequilibrae.project.database_connection import database_connection

spec = iutil.find_spec("openmatrix")
has_omx = spec is not None


def list_matrices(fldr) -> pd.DataFrame:
    conn = database_connection(db_type="project_database")
    df = pd.read_sql("select * from matrices", conn)
    conn.close()

    existing_files = os.listdir(fldr)

    matrices = df.assign(WARNINGS="")
    for idx, record in matrices.iterrows():
        if record.file_name not in existing_files:
            matrices.loc[idx, "WARNINGS"] = "File not found on disk"

        elif record.file_name[-4:] == ".omx" and not has_omx:
            matrices.loc[idx, "WARNINGS"] = "OMX not available for display"
    return matrices
