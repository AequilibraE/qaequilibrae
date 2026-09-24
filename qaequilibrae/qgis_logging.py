"""Logging helpers that route standard QAequilibraE messages into the QGIS log.

Model-run output retains its dedicated ``Model Run`` category so it can also feed the live run
dialog. All other plugin messages should use :func:`get_logger`. QGIS logs are user-visible and
can be persisted or shared, so messages must not contain credentials or other secrets.
"""

import logging
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import cast

from qgis.core import Qgis, QgsMessageLog, QgsProcessingFeedback


LOG_CATEGORY = "AequilibraE"
LOGGER_NAME = "qaequilibrae"
HANDLER_MARKER = "_qaequilibrae_qgis_log_handler"
FEEDBACK_HANDLER_MARKER = "_qaequilibrae_processing_feedback_handler"
_active_feedback: ContextVar[QgsProcessingFeedback | None] = ContextVar("processing_feedback", default=None)


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


class ProcessingFeedbackHandler(logging.Handler):
    """Send log records to the active Processing dialog on this execution context."""

    def __init__(self):
        super().__init__()
        setattr(self, FEEDBACK_HANDLER_MARKER, True)

    def emit(self, record: logging.LogRecord) -> None:
        feedback = _active_feedback.get()
        if feedback is None:
            return
        try:
            message = self.format(record)
            if record.levelno >= logging.ERROR:
                feedback.reportError(message)
            elif record.levelno >= logging.WARNING:
                feedback.pushWarning(message)
            elif record.levelno >= logging.INFO:
                feedback.pushInfo(message)
            else:
                feedback.pushDebugInfo(message)
        except Exception:
            self.handleError(record)


@contextmanager
def processing_feedback(feedback: QgsProcessingFeedback):
    """Route plugin logs to feedback for this run, then restore the previous context."""
    token = _active_feedback.set(feedback)
    try:
        yield
    finally:
        _active_feedback.reset(token)


def with_processing_feedback(method):
    """Keep a Processing algorithm's logging context active for its entire run."""

    @wraps(method)
    def wrapper(self, parameters, context, feedback):
        with processing_feedback(feedback):
            return method(self, parameters, context, feedback)

    return wrapper


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a named QAequilibraE logger configured to write to the QGIS message log."""
    logger = logging.getLogger(LOGGER_NAME)
    if not any(getattr(handler, HANDLER_MARKER, False) for handler in logger.handlers):
        handler = QgsMessageLogHandler()
        handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
        logger.addHandler(handler)
    if not any(getattr(handler, FEEDBACK_HANDLER_MARKER, False) for handler in logger.handlers):
        handler = ProcessingFeedbackHandler()
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    if name is None:
        return logger
    if name == LOGGER_NAME or name.startswith(f"{LOGGER_NAME}."):
        return logging.getLogger(name)
    return logger.getChild(name)
