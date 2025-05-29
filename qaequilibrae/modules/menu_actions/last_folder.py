# Copyright (c) 2025, UChicago Argonne, LLC
# BSD OPEN SOURCE LICENSE. Full license can be found in LICENSE
import logging
import os
from tempfile import gettempdir


def last_folder():
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
