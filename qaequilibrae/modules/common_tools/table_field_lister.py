from sqlite3 import Connection


def find_table_fields(conn: Connection, table_name: str):
    """Returns the lower-cased column names of *table_name*.

    Uses the table-valued form of the pragma so the table name travels as a bound parameter
    rather than being interpolated into the statement.
    """
    structure = conn.execute("SELECT name FROM pragma_table_info(?);", [table_name]).fetchall()
    return [x[0].lower() for x in structure]
