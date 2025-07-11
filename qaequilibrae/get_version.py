import sys
from pathlib import Path

project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))

with open("qaequilibrae/metadata.txt", mode="r") as file:
    for line in file:
        if "version" in line:
            print(line.split("=")[1])
