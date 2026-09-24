"""Shared project lifecycle helpers for Processing algorithms."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from qgis.core import QgsProcessingException


@contextmanager
def open_project(project_folder: str | Path) -> Iterator[Any]:
    """Open an AequilibraE project and close it on every exit path.

    AequilibraE's ``Project`` class deliberately exposes ``open`` and ``close``
    methods instead of implementing ``__enter__`` and ``__exit__``. Processing
    algorithms still need the same lifetime guarantee, especially when an
    algorithm is cancelled or raises while writing a record.
    """
    try:
        from aequilibrae import Project
    except ImportError as error:
        raise QgsProcessingException("The AequilibraE Python package is not available") from error

    project = Project()
    opened = False
    try:
        try:
            project.open(str(project_folder))
        except Exception as error:
            raise QgsProcessingException(f"Could not open AequilibraE project {project_folder}: {error}") from error
        opened = True
        yield project
    finally:
        if opened:
            project.close()


@contextmanager
def borrow_project(project_or_folder: Any) -> Iterator[Any]:
    """Yield an open project, opening it from a folder only when necessary.

    A caller that already holds a project passes it straight through, so a dialog and
    a standalone Processing run share one code path. When a folder has to be opened,
    whoever was active beforehand is restored afterwards, so the project a dialog is
    using keeps its active status.
    """
    from aequilibrae.context import activate_project, get_active_project

    if hasattr(project_or_folder, "network"):
        yield project_or_folder
        return

    active = get_active_project(must_exist=False)
    if active is not None and Path(active.project_base_path).resolve() == Path(project_or_folder).resolve():
        yield active
        return

    try:
        with open_project(project_or_folder) as project:
            yield project
    finally:
        activate_project(active)
