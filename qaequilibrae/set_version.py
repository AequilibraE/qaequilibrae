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
    # Add missing info to the metadata
    current_time = datetime.now()
    current_version = current_time.strftime("%y.%j.%H")

    metadata_path = project_dir / "qaequilibrae" / "metadata.txt"
    metadata_lines = metadata_path.read_text().splitlines()
    replacements = {"version": current_version, "commitSha1": sha}
    found = set()

    for index, line in enumerate(metadata_lines):
        key, separator, _ = line.partition("=")
        if separator and key in replacements:
            metadata_lines[index] = f"{key}={replacements[key]}"
            found.add(key)

    for key, value in replacements.items():
        if key not in found:
            metadata_lines.append(f"{key}={value}")

    metadata_path.write_text("\n".join(metadata_lines) + "\n")

    # Update version in XML
    xml_path = project_dir / "docs" / "source" / "_static" / "plugin.xml"
    tree = ET.parse(xml_path)  # nosec B314
    root = tree.getroot()

    for child in root:
        child.attrib["version"] = current_version

    tree.write(xml_path)
