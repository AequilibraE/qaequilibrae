import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from qaequilibrae.download_extra_packages_class import download_all


download_all().install(True)