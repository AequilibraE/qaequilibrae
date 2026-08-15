import os
from pathlib import Path

from qaequilibrae.i18n.create_pro_file import create_file


def test_file_creation():
    """The translation .pro file is written, and is not empty."""
    create_file()
    output_path = Path("qaequilibrae/i18n/qaequilibrae.pro")

    assert output_path.exists()
    assert os.stat(output_path).st_size > 0

    os.remove(output_path)
