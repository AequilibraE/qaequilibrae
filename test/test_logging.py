import importlib

from qgis.core import Qgis, QgsMessageLog, QgsProcessingFeedback

import qaequilibrae.qgis_logging as qgis_logging
from qaequilibrae.download_extra_packages_class import log_message
from qaequilibrae.qgis_logging import LOG_CATEGORY, get_logger


def test_python_log_records_are_written_to_the_qgis_aequilibrae_category(monkeypatch):
    received = []
    monkeypatch.setattr(QgsMessageLog, "logMessage", lambda *args: received.append(args))

    logger = get_logger("test")
    logger.info("Information")
    logger.warning("Warning")
    logger.error("Error")

    assert received == [
        ("[qaequilibrae.test] Information", LOG_CATEGORY, Qgis.MessageLevel.Info, False),
        ("[qaequilibrae.test] Warning", LOG_CATEGORY, Qgis.MessageLevel.Warning, False),
        ("[qaequilibrae.test] Error", LOG_CATEGORY, Qgis.MessageLevel.Critical, False),
    ]


def test_plugin_reload_does_not_duplicate_qgis_log_messages(monkeypatch):
    received = []
    monkeypatch.setattr(QgsMessageLog, "logMessage", lambda *args: received.append(args))

    reloaded_logging = importlib.reload(qgis_logging)
    reloaded_logging.get_logger("reload").info("Only once")

    assert received == [("[qaequilibrae.reload] Only once", LOG_CATEGORY, Qgis.MessageLevel.Info, False)]


def test_processing_feedback_is_scoped_to_the_active_run():
    logger = qgis_logging.get_logger("processing")
    first = QgsProcessingFeedback()
    second = QgsProcessingFeedback()

    with qgis_logging.processing_feedback(first):
        logger.info("Started first run")
        with qgis_logging.processing_feedback(second):
            logger.warning("Second run warning")
        logger.info("Finished first run")
    logger.info("Outside processing")

    assert "Started first run" in first.textLog()
    assert "Finished first run" in first.textLog()
    assert "Second run warning" not in first.textLog()
    assert "Outside processing" not in first.textLog()
    assert "Second run warning" in second.textLog()
    assert "Started first run" not in second.textLog()


def test_exceptions_include_a_traceback(monkeypatch):
    received = []
    monkeypatch.setattr(QgsMessageLog, "logMessage", lambda *args: received.append(args))

    try:
        raise RuntimeError("broken")
    except RuntimeError:
        get_logger("test").exception("Could not complete the operation")

    assert "[qaequilibrae.test] Could not complete the operation" in received[0][0]
    assert "RuntimeError: broken" in received[0][0]


def test_dependency_installation_messages_request_a_qgis_notification(monkeypatch):
    received = []
    monkeypatch.setattr(QgsMessageLog, "logMessage", lambda *args: received.append(args))

    log_message("Dependency installation failed", Qgis.MessageLevel.Critical)

    assert received == [
        (
            "[qaequilibrae.download_extra_packages_class] Dependency installation failed",
            LOG_CATEGORY,
            Qgis.MessageLevel.Critical,
            True,
        )
    ]
