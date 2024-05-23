import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))
from qaequilibrae.download_extra_packages_class import DownloadAll


# on_latest = sys.version_info >= (3, 12)
DownloadAll().install(True)
