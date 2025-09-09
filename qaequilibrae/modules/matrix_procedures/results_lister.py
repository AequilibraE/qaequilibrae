from os.path import isfile

import pandas as pd


def list_results(project) -> pd.DataFrame:
    databases = []
    with project.db_connection as conn:
        df = pd.read_sql("select * from results", conn)
        databases.append(df)

    if isfile(project._transit_database_path):
        with project.transit_connection as conn:
            # Check if 'transit_database' has a results table before reading it
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='results'").fetchone() is not None:
                df = pd.read_sql("select * from results", conn)
                databases.append(df)

    df = pd.concat(databases)

    if isfile(project._results_database_path):
        with project.results_connection as conn:
            tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    else:
        tables = []

    results = df.assign(WARNINGS="")
    for idx, record in results.iterrows():
        if record.table_name not in tables:
            results.loc[idx, "WARNINGS"] = "Table not found in the results database"
    return results
