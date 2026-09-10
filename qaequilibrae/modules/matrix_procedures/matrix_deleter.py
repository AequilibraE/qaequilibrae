def delete_matrix(project, matrix_name: str) -> None:
    """Deletes a matrix record from the project, along with its file on disk.

    AequilibraE owns what deleting a matrix means - the record goes and the file it points at
    goes with it - so the work is delegated rather than reimplemented here. Its gateway is built
    once when the project is opened, so it is reloaded first: a matrix imported during this
    session is otherwise absent from it and would look like a record that does not exist.

    Records whose file is missing from disk never make it into that gateway at all, and those are
    exactly the ones flagged in the viewer as not found on disk. Removing the orphan row straight
    from the project database is the only way to let a user clear them one at a time.
    """
    project.matrices.reload()

    if project.matrices.check_exists(matrix_name):
        project.matrices.delete_record(matrix_name)
        return

    with project.db_connection as conn:
        conn.execute("DELETE FROM matrices WHERE name=?", [matrix_name])
