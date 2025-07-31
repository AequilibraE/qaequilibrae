from os.path import isfile

import pandas as pd
from aequilibrae.utils.db_utils import read_and_close


def list_results(project) -> pd.DataFrame:
    databases = []
    with read_and_close(project._project_database_path) as conn:
        df = pd.read_sql("select * from results", conn)
        databases.append(df)

    if isfile(project._transit_database_path):
        with read_and_close(project._transit_database_path) as conn:
            df = pd.read_sql("select * from results", conn)
            databases.append(df)

    df = pd.concat(databases)

    if isfile(project._results_database_path):
        with read_and_close(project._results_database_path) as conn:
            tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    else:
        tables = []

    results = df.assign(WARNINGS="")
    for idx, record in results.iterrows():
        if record.table_name not in tables:
            results.loc[idx, "WARNINGS"] = "Table not found in the results database"
    return results
