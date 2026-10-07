"""Open or reuse matrices for Processing algorithms."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


@contextmanager
def open_matrix(path: str, cores: str, matrix: Any | None = None) -> Iterator[Any]:
    """Reuse a matrix or load selected cores from a file."""
    if matrix is not None:
        yield matrix
        return

    from aequilibrae.matrix import AequilibraeMatrix

    matrix = AequilibraeMatrix()
    try:
        matrix.load(Path(path))
        selected = [core.strip() for core in cores.split(",") if core.strip()] if cores else list(matrix.names)
        if not selected:
            raise ValueError("The matrix contains no cores")
        matrix.computational_view(selected)
        yield matrix
    finally:
        matrix.close()
