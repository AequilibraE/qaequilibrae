from os import listdir

import pandas as pd


def list_matrices(project) -> pd.DataFrame:
    with project.db_connection as conn:
        df = pd.read_sql("select * from matrices", conn)

    existing_files = listdir(project.project_base_path / "matrices")

    matrices = df.assign(WARNINGS="")
    for idx, record in matrices.iterrows():
        if record.file_name not in existing_files:
            matrices.loc[idx, "WARNINGS"] = "File not found on disk"

    return matrices
