import pandas as pd


def load_result_table(project, table_name: str):
    # SQLite cannot bind a table name, and table_name always comes from the project's own results catalog
    with project.results_connection as conn:
        return pd.read_sql(f"SELECT * FROM {table_name};", con=conn)  # nosec B608
