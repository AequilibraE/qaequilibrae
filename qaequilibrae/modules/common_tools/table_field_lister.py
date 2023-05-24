from sqlite3 import Connection


def find_table_fields(conn: Connection, table_name: str):
    structure = conn.execute(f"pragma table_info('{table_name}')").fetchall()
    return [x[1].lower() for x in structure]
