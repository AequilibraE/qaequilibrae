from pathlib import Path
from pprint import pformat


def create_strings(dct: dict):
    """Export the same Processing parameters used by the assignment dialog."""
    source = f"""from aequilibrae.context import get_active_project

from qaequilibrae.modules.processing_provider.paths_procedures.traffic_assignment import run_traffic_assignment


def run_assignment():
    return run_traffic_assignment({pformat(dct["parameters"], sort_dicts=False)}, project=get_active_project())
"""

    out_name = Path(dct["out_name"])
    out_name.write_text(source, encoding="utf-8")

    init_path = Path(dct["project_path"]) / "run" / "__init__.py"
    lines = init_path.read_text(encoding="utf-8").splitlines(keepends=True)
    import_line = f"from .{out_name.stem} import run_assignment\n"
    if import_line not in lines:
        lines.insert(0, import_line)
    init_path.write_text("".join(lines), encoding="utf-8")
