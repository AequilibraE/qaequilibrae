import sqlite3
from os.path import join, isfile

import pandas as pd
from aequilibrae.utils.db_utils import read_and_close
from aequilibrae.project.database_connection import database_connection


def list_results(project_base_path) -> pd.DataFrame:
    databases = []
    with read_and_close(database_connection("network")) as conn:
        df = pd.read_sql("select * from results", conn)
        databases.append(df)

    if isfile(join(project_base_path, "public_transport.sqlite")):
        with read_and_close(database_connection("transit")) as conn:
            df = pd.read_sql("select * from results", conn)
            databases.append(df)

    df = pd.concat(databases)

    conn = sqlite3.connect(join(project_base_path, "results_database.sqlite"))
    tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    conn.close()

    results = df.assign(WARNINGS="")
    for idx, record in results.iterrows():
        if record.table_name not in tables:
            results.loc[idx, "WARNINGS"] = "Table not found in the results database"
    return results
