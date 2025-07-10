import sys
from datetime import datetime
from pathlib import Path

project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))


current_time = datetime.now()
current_version = current_time.strftime("%y.%j.%f")

with open("qaequilibrae/metadata.txt", mode="a") as file:
    file.write(f"version={current_version}")
    print(current_version)
