import pandas as pd

from qaequilibrae.modules.common_tools.sql_identifiers import quote_identifier

CATALOG_QUERY = "SELECT name FROM sqlite_master WHERE type='table' AND name=? COLLATE NOCASE;"


def load_result_table(project, table_name: str):
    """Reads a result table from the project's results database.

    SQLite cannot bind a table name, so instead of interpolating whatever the caller passed, the
    name is looked up in the database catalog through a bound parameter and the statement is built
    from the name the catalog gives back, quoted. A caller cannot reach the query with anything
    that is not already a table in that database.
    """
    with project.results_connection as conn:
        known = conn.execute(CATALOG_QUERY, [table_name]).fetchone()
        if known is None:
            raise ValueError(f"There is no result table named '{table_name}' in this project")

        return pd.read_sql(f"SELECT * FROM {quote_identifier(known[0])};", con=conn)
