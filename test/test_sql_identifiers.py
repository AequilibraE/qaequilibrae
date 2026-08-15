import sqlite3

import pytest

from qaequilibrae.modules.common_tools import quote_identifier


@pytest.mark.parametrize(
    "name,expected",
    [
        ("link_id", '"link_id"'),
        ("odd name", '"odd name"'),
        ('odd"name', '"odd""name"'),
        ("a); DROP TABLE links; --", '"a); DROP TABLE links; --"'),
    ],
)
def test_quotes_and_doubles_embedded_quotes(name, expected):
    """Identifiers are double-quoted, with any embedded quote doubled."""
    assert quote_identifier(name) == expected


def test_a_hostile_column_name_stays_a_column_name():
    """A column name carrying SQL is used as a name only, and drops no tables."""
    # The names reaching our INSERT/UPDATE builders come from user-supplied layers
    hostile = 'name"; DROP TABLE nodes; --'

    conn = sqlite3.connect(":memory:")
    conn.execute(f"CREATE TABLE nodes (node_id INTEGER, {quote_identifier(hostile)} TEXT);")
    conn.execute("INSERT INTO nodes (node_id) VALUES (1);")
    conn.execute(f"UPDATE nodes SET {quote_identifier(hostile)}=? WHERE node_id=?;", ("safe", 1))

    assert conn.execute("SELECT count(*) FROM sqlite_master WHERE name='nodes';").fetchone()[0] == 1
    assert conn.execute(f"SELECT {quote_identifier(hostile)} FROM nodes;").fetchone()[0] == "safe"
    conn.close()
