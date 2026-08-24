from os.path import isfile

from qaequilibrae.modules.common_tools.sql_identifiers import quote_identifier

HAS_RESULTS_TABLE = "SELECT 1 FROM sqlite_master WHERE type='table' AND name='results'"


def delete_result(project, table_name: str) -> None:
    """Deletes a result record from the project, along with its table in the results database.

    AequilibraE owns what deleting a result means, so the work is delegated to it. Its gateway is
    built once when the project is opened, so it is reloaded first: a result produced during this
    session is otherwise absent from it and would look like a record that does not exist.

    That gateway only covers the project database, while the viewer also lists the results
    recorded in the transit database - see ``list_results``. Those are removed here, mirroring
    what AequilibraE does for the ones it owns: the record goes, and the table it points at in the
    results database goes with it.
    """
    project.results.reload()

    if project.results.check_exists(table_name):
        project.results.delete_record(table_name)
        return

    if isfile(project._transit_database_path):
        with project.transit_connection as conn:
            if conn.execute(HAS_RESULTS_TABLE).fetchone() is not None:
                conn.execute("DELETE FROM results WHERE table_name=?", [table_name])

    if isfile(project._results_database_path):
        with project.results_connection as conn:
            conn.execute(f"DROP TABLE IF EXISTS {quote_identifier(table_name)}")
