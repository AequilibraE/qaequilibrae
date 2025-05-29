import logging
import os
from tempfile import gettempdir


def last_folder():
    """Reads the last-used folder path and its return value.
    If the folder does not exist or cannot be find, function returns a temporary directory."""
    pth = os.path.join(gettempdir(), "aequilibrae_last_folder.txt")
    if not os.path.isfile(pth):
        with open(pth, "w") as file:
            file.write(gettempdir())
        return gettempdir()
    try:
        with open(pth, "r") as file:
            return file.readline()
    except Exception as e:
        logger = logging.getLogger("qaequilibrae")
        logger.debug(f"Could not find previously used folder: {e.args}")
        return gettempdir()
