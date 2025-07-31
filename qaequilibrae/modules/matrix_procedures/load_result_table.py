import pandas as pd
from aequilibrae.utils.db_utils import read_and_close


def load_result_table(base_path: str, table_name: str):
    with read_and_close(base_path, spatial=False) as conn:
        return pd.read_sql(f"SELECT * FROM {table_name};", con=conn)
