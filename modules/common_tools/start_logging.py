import logging
import os
from tempfile import gettempdir


def starts_logging():
    logger = logging.getLogger("AequilibraEGUI")

    log_file = os.path.join(gettempdir(), "QAequilibraE.log")
    if not os.path.isfile(log_file):
        a = open(log_file, "w")
        a.close()

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s; %(message)s")

    if not len(logger.handlers):
        ch = logging.FileHandler(log_file)
        ch.setFormatter(formatter)
        ch.name = "AequilibraEGUI"
        ch.setLevel(logging.DEBUG)
        logger.addHandler(ch)
