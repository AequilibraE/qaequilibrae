import os
import mmap
import sys
from pathlib import Path

project_dir = Path(__file__).parent.parent
if str(project_dir) not in sys.path:
    sys.path.append(str(project_dir))


def create_file():
    forms = []
    sources = []

    for path, subdirs, files in os.walk("qaequilibrae/modules"):
        for name in files:
            if name in ["__init__.py", "metadata.txt"]:
                pass
            elif name[-2:] == "ui":
                forms.append(os.path.join(path, name))
            else:
                with open(os.path.join(path, name), "rb", 0) as file, mmap.mmap(
                    file.fileno(), 0, access=mmap.ACCESS_READ
                ) as s:
                    if s.find(b"self.tr") != -1:
                        sources.append(os.path.join(path, name))

    forms = [f.replace("""\\""", "/").replace("qaequilibrae", "..") for f in forms]
    sources = [s.replace("""\\""", "/").replace("qaequilibrae", "..") for s in sources]

    with open("qaequilibrae/i18n/qaequilibrae.pro", mode="w") as pro_file:
        pro_file.write(f"FORMS = {forms[0]} \\")
        for f in forms[1:-1]:
            pro_file.write(f"\n {f} \\")
        pro_file.write(f"\n {forms[-1]}")

        pro_file.write("\n")

        pro_file.write(f"\nSOURCES = ../qaequilibrae.py \\")
        for s in sources[:-1]:
            pro_file.write(f"\n {s} \\")
        pro_file.write(f"\n {sources[-1]}")

        pro_file.write("\n")

        pro_file.write(f"\nTRANSLATIONS = qaequilibrae.ts")


if __name__ == "__main__":
    create_file()
