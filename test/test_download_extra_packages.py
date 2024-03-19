import os
from shutil import rmtree
from pathlib import Path

from qaequilibrae.download_extra_packages_class import download_all


@pytest.mark.skip("This test takes like... forever")
def test_file_creation():
    download_all().install()
    folder = Path("qaequilibrae/packages")

    with open("qaequilibrae/requirements.txt", "r") as file:
        reqs = file.read().split("\n")

    reqs = [r.split("=")[0].split("-")[-1] for r in reqs]

    folder_content = [f.path.split("/")[-1].split("-")[0].lower() for f in os.scandir(folder) if f.is_dir()]

    for req in reqs:
        assert req in folder_content

    files = ["cython.py", "six.py", "__version__.py", "requirements.txt"]
    for item in os.listdir(folder):
        if item != "__init__.py":
            continue
        elif item in files:
            os.remove(folder / item)
        else:
            rmtree(folder / item)
