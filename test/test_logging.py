from qgis.core import Qgis, QgsMessageLog

from qaequilibrae.logging import LOG_CATEGORY, get_logger


def test_python_log_records_are_written_to_the_qgis_aequilibrae_category(monkeypatch):
    received = []
    monkeypatch.setattr(QgsMessageLog, "logMessage", lambda *args: received.append(args))

    logger = get_logger("test")
    logger.info("Information")
    logger.warning("Warning")
    logger.error("Error")

    assert received == [
        ("Information", LOG_CATEGORY, Qgis.MessageLevel.Info, False),
        ("Warning", LOG_CATEGORY, Qgis.MessageLevel.Warning, False),
        ("Error", LOG_CATEGORY, Qgis.MessageLevel.Critical, False),
    ]
