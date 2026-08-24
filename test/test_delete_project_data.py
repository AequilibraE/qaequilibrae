import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pytest

from qaequilibrae.modules.matrix_procedures.matrix_deleter import delete_matrix
from qaequilibrae.modules.matrix_procedures.results_deleter import delete_result


@contextmanager
def connection(path):
    conn = sqlite3.connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


class FakeGateway:
    """Stands in for one of AequilibraE's gateways, recording what the deleter asked of it.

    ``appears_on_reload`` covers the record created after the project was opened: the gateway
    only learns about it once it is reloaded, which is what the deleters do before asking.
    """

    def __init__(self, known=(), appears_on_reload=()):
        self.known = set(known)
        self.appears_on_reload = set(appears_on_reload)
        self.reloads = 0
        self.deleted = []

    def reload(self):
        self.reloads += 1
        self.known |= self.appears_on_reload

    def check_exists(self, name):
        return name in self.known

    def delete_record(self, name):
        self.known.remove(name)
        self.deleted.append(name)


class FakeProject:
    """Just enough of a project for the deleters: the gateways and the databases they reach."""

    def __init__(self, base_path, matrices=None, results=None):
        self.base_path = Path(base_path)
        self.matrices = matrices or FakeGateway()
        self.results = results or FakeGateway()

    @property
    def _transit_database_path(self):
        return self.base_path / "public_transport.sqlite"

    @property
    def _results_database_path(self):
        return self.base_path / "results_database.sqlite"

    @property
    def db_connection(self):
        return connection(self.base_path / "project_database.sqlite")

    @property
    def transit_connection(self):
        return connection(self._transit_database_path)

    @property
    def results_connection(self):
        return connection(self._results_database_path)


def matrix_rows(project):
    with connection(project.base_path / "project_database.sqlite") as conn:
        return [row[0] for row in conn.execute("SELECT name FROM matrices ORDER BY name")]


def transit_result_rows(project):
    with connection(project._transit_database_path) as conn:
        return [row[0] for row in conn.execute("SELECT table_name FROM results ORDER BY table_name")]


def results_database_tables(project):
    with connection(project._results_database_path) as conn:
        return [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]


@pytest.fixture
def project(tmp_path):
    with connection(tmp_path / "project_database.sqlite") as conn:
        conn.execute("CREATE TABLE matrices (name TEXT PRIMARY KEY, file_name TEXT);")
        conn.execute("INSERT INTO matrices VALUES ('demand', 'demand.omx'), ('skims', 'skims.omx');")
    return FakeProject(tmp_path)


@pytest.fixture
def transit_project(project):
    with connection(project._transit_database_path) as conn:
        conn.execute("CREATE TABLE results (table_name TEXT PRIMARY KEY, procedure TEXT);")
        conn.execute("INSERT INTO results VALUES ('pt_assig', 'transit assignment'), ('other', 'x');")
    with connection(project._results_database_path) as conn:
        conn.execute("CREATE TABLE pt_assig (link_id INTEGER);")
        conn.execute("CREATE TABLE other (link_id INTEGER);")
    return project


def test_a_matrix_aequilibrae_knows_about_is_deleted_by_aequilibrae(project):
    project.matrices = FakeGateway(known=["demand"])

    delete_matrix(project, "demand")

    assert project.matrices.deleted == ["demand"]
    # Deleting the record and the file on disk is AequilibraE's job, so the row is still there
    assert matrix_rows(project) == ["demand", "skims"]


def test_a_matrix_imported_after_the_project_was_opened_is_still_found(project):
    project.matrices = FakeGateway(appears_on_reload=["demand"])

    delete_matrix(project, "demand")

    assert project.matrices.reloads == 1
    assert project.matrices.deleted == ["demand"]


def test_a_record_whose_file_is_missing_is_removed_from_the_database(project):
    # AequilibraE never loads a record without a file on disk, so the orphan row is ours to remove
    project.matrices = FakeGateway(known=["skims"])

    delete_matrix(project, "demand")

    assert project.matrices.deleted == []
    assert matrix_rows(project) == ["skims"]


def test_a_result_aequilibrae_knows_about_is_deleted_by_aequilibrae(transit_project):
    transit_project.results = FakeGateway(known=["assignment"])

    delete_result(transit_project, "assignment")

    assert transit_project.results.deleted == ["assignment"]
    assert transit_result_rows(transit_project) == ["other", "pt_assig"]
    assert results_database_tables(transit_project) == ["other", "pt_assig"]


def test_a_result_produced_after_the_project_was_opened_is_still_found(transit_project):
    transit_project.results = FakeGateway(appears_on_reload=["assignment"])

    delete_result(transit_project, "assignment")

    assert transit_project.results.reloads == 1
    assert transit_project.results.deleted == ["assignment"]


def test_a_transit_result_is_removed_from_the_transit_database(transit_project):
    delete_result(transit_project, "pt_assig")

    assert transit_result_rows(transit_project) == ["other"]
    assert results_database_tables(transit_project) == ["other"]


def test_a_transit_result_name_containing_a_quote_is_still_dropped(transit_project):
    with connection(transit_project._results_database_path) as conn:
        conn.execute('CREATE TABLE "odd""name" (link_id INTEGER);')

    delete_result(transit_project, 'odd"name')

    assert results_database_tables(transit_project) == ["other", "pt_assig"]


def test_deleting_a_result_does_not_create_databases_that_are_not_there(project):
    delete_result(project, "assignment")

    assert not project._transit_database_path.exists()
    assert not project._results_database_path.exists()
