import sys

# The only XML this module ever reads is docs/source/_static/plugin.xml from this repository,
# so the entity-expansion attacks B405/B314 warn about do not apply here
import xml.etree.ElementTree as ET  # nosec B405
from datetime import datetime
from pathlib import Path

project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))


def set_version(sha):
    current_time = datetime.now()
    current_version = current_time.strftime("%y.%j.%H")

    metadata_path = project_dir / "qaequilibrae" / "metadata.txt"
    _update_metadata(metadata_path, current_version, sha)

    # Update version in XML
    xml_path = project_dir / "docs" / "source" / "_static" / "plugin.xml"
    tree = ET.parse(xml_path)  # nosec B314
    root = tree.getroot()

    for child in root:
        child.attrib["version"] = current_version

    tree.write(xml_path)


def _update_metadata(metadata_path, version, sha):
    """Replace release metadata without duplicating keys on repeated builds."""
    values = {"version": version, "commitSha1": sha}
    updated = []
    replaced = set()

    for line in metadata_path.read_text(encoding="utf-8").splitlines():
        key, separator, _ = line.partition("=")
        if separator and key in values:
            if key not in replaced:
                updated.append(f"{key}={values[key]}")
                replaced.add(key)
        else:
            updated.append(line)

    for key, value in values.items():
        if key not in replaced:
            updated.append(f"{key}={value}")

    metadata_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
