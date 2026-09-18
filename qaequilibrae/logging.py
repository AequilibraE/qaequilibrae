"""Logging helpers that route QAequilibraE messages into the QGIS log."""

import logging
from typing import cast

from qgis.core import Qgis, QgsMessageLog


LOG_CATEGORY = "AequilibraE"
LOGGER_NAME = "qaequilibrae"


def _qgis_level(record: logging.LogRecord) -> Qgis.MessageLevel:
    """Get the QGIS level requested by a record, or map its Python level."""
    if hasattr(record, "qgis_level"):
        return cast(Qgis.MessageLevel, record.qgis_level)
    if record.levelno >= logging.ERROR:
        return Qgis.MessageLevel.Critical
    if record.levelno >= logging.WARNING:
        return Qgis.MessageLevel.Warning
    return Qgis.MessageLevel.Info


class QgsMessageLogHandler(logging.Handler):
    """Forward standard Python log records to the QAequilibraE QGIS category."""

    def __init__(self, category: str = LOG_CATEGORY):
        super().__init__()
        self.category = category

    def emit(self, record: logging.LogRecord) -> None:
        try:
            QgsMessageLog.logMessage(
                self.format(record),
                self.category,
                _qgis_level(record),
                getattr(record, "notify_user", False),
            )
        except Exception:
            self.handleError(record)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a QAequilibraE logger configured to write to the QGIS message log."""
    logger = logging.getLogger(LOGGER_NAME)
    if not any(isinstance(handler, QgsMessageLogHandler) for handler in logger.handlers):
        handler = QgsMessageLogHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    return logger if name is None else logger.getChild(name)
