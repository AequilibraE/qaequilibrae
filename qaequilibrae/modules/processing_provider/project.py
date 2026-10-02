"""Shared project lifecycle helpers for Processing algorithms."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from qgis.core import QgsProcessingException


@contextmanager
def open_project(project_folder: str | Path) -> Iterator[Any]:
    """Open an AequilibraE project and close it when the context exits."""
    try:
        from aequilibrae import Project
    except ImportError as error:
        raise QgsProcessingException("The AequilibraE Python package is not available") from error

    project = Project()
    try:
        project.open(str(project_folder))
    except Exception as error:
        raise QgsProcessingException(f"Could not open AequilibraE project {project_folder}: {error}") from error
    try:
        yield project
    finally:
        project.close()


@contextmanager
def borrow_project(project_or_folder: Any) -> Iterator[Any]:
    """Reuse an open project or open a folder and restore the previous active project."""
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
