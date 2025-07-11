import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))


def set_version(sha):
    # Add missing info to the metadata
    current_time = datetime.now()
    current_version = current_time.strftime("%y.%j.%f")

    with open("qaequilibrae/metadata.txt", mode="a") as file:
        file.write(f"version={current_version}\n")
        file.write(f"commitSha1={sha}")

    # Update version in XML
    tree = ET.parse("docs/source/_static/plugins.xml")
    root = tree.getroot()

    for child in root:
        child.attrib["version"] = current_version

    tree.write("docs/source/_static/plugins.xml")
