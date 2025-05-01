import sqlite3
from os.path import join

import pandas as pd


def load_result_table(project_base_path: str, table_name: str):
    pth = join(project_base_path, "results_database.sqlite")
    conn = sqlite3.connect(pth)

    return pd.read_sql(f"SELECT * FROM {table_name};", con=conn)
