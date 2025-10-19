import pandas as pd


def load_result_table(project, table_name: str):
    with project.results_connection as conn:
        return pd.read_sql(f"SELECT * FROM {table_name};", con=conn)
