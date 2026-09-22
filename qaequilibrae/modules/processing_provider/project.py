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
