"""Logging helpers that route standard QAequilibraE messages into the QGIS log.

Model-run output retains its dedicated ``Model Run`` category so it can also feed the live run
dialog. All other plugin messages should use :func:`get_logger`. QGIS logs are user-visible and
can be persisted or shared, so messages must not contain credentials or other secrets.
"""

import logging
from typing import cast

from qgis.core import Qgis, QgsMessageLog


LOG_CATEGORY = "AequilibraE"
LOGGER_NAME = "qaequilibrae"
HANDLER_MARKER = "_qaequilibrae_qgis_log_handler"


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
        # A logger survives QGIS plugin reloads, unlike this module's handler class.
        # A stable marker therefore prevents every reload from adding another handler.
        setattr(self, HANDLER_MARKER, True)

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
    """Return a named QAequilibraE logger configured to write to the QGIS message log."""
    logger = logging.getLogger(LOGGER_NAME)
    if not any(getattr(handler, HANDLER_MARKER, False) for handler in logger.handlers):
        handler = QgsMessageLogHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if name is None:
        return logger
    if name == LOGGER_NAME or name.startswith(f"{LOGGER_NAME}."):
        return logging.getLogger(name)
    return logger.getChild(name)
