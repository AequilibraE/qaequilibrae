import sqlite3
from contextlib import nullcontext

import pytest

from qaequilibrae.modules.matrix_procedures.load_result_table import load_result_table


class FakeProject:
    """Just enough of a project for the helper: something that hands out a results connection."""

    def __init__(self, connection):
        self.connection = connection

    @property
    def results_connection(self):
        return nullcontext(self.connection)


@pytest.fixture
def project():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE assignment_result (link_id INTEGER, matrix_tot REAL);")
    connection.execute("INSERT INTO assignment_result VALUES (1, 12.5), (2, 7.0);")
    connection.commit()
    yield FakeProject(connection)
    connection.close()


def test_reads_an_existing_result_table(project):
    """A result table is read back with its columns and values intact."""
    result = load_result_table(project, "assignment_result")

    assert result.columns.tolist() == ["link_id", "matrix_tot"]
    assert result["matrix_tot"].tolist() == [12.5, 7.0]


def test_matches_the_table_name_case_insensitively(project):
    """The table name is matched the way SQLite does, ignoring case."""
    # SQLite resolves table names case-insensitively, so the helper must not be stricter
    assert load_result_table(project, "Assignment_Result").shape == (2, 2)


def test_unknown_table_is_rejected(project):
    """A name that matches no result table is refused rather than queried."""
    with pytest.raises(ValueError, match="no result table named"):
        load_result_table(project, "not_a_table")


@pytest.mark.parametrize(
    "payload",
    [
        "assignment_result; DROP TABLE assignment_result",
        "assignment_result WHERE 1=0 --",
        'assignment_result"; DROP TABLE assignment_result; --',
        "sqlite_master UNION SELECT 1, 2",
    ],
)
def test_injection_payloads_are_rejected_and_leave_the_database_alone(project, payload):
    """SQL smuggled in through the table name is refused and the database is left untouched."""
    with pytest.raises(ValueError, match="no result table named"):
        load_result_table(project, payload)

    remaining = project.connection.execute("SELECT count(*) FROM assignment_result;").fetchone()[0]
    assert remaining == 2


def test_a_table_whose_name_contains_a_quote_is_still_readable(project):
    """A table name carrying a double quote is quoted properly rather than rejected."""
    project.connection.execute('CREATE TABLE "odd""name" (link_id INTEGER);')
    project.connection.execute('INSERT INTO "odd""name" VALUES (3);')
    project.connection.commit()

    assert load_result_table(project, 'odd"name')["link_id"].tolist() == [3]
