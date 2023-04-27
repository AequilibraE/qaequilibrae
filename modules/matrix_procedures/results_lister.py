import importlib.util as iutil
import os
import sqlite3
from os.path import join

import pandas as pd
from aequilibrae.project.database_connection import database_connection


def list_results(project_base_path) -> pd.DataFrame:
    conn = database_connection(db_type="project_database")
    df = pd.read_sql("select * from results", conn)
    conn.close()

    conn = sqlite3.connect(join(project_base_path, "results_database.sqlite"))
    tables = [x[0] for x in conn.execute("SELECT name FROM sqlite_master WHERE type ='table'").fetchall()]
    conn.close()
    results = df.assign(WARNINGS="")
    for idx, record in results.iterrows():
        if record.table_name not in tables:
            results.loc[idx, "WARNINGS"] = "Table not found in the results database"
    return results
