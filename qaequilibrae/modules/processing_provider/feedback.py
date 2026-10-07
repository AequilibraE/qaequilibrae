"""Report worker progress through QGIS Processing."""

from typing import Any

from qgis.core import QgsProcessingFeedback


def connect_progress(worker: Any, feedback: QgsProcessingFeedback | None) -> None:
    """Forward start, update, and finished signals as percentage progress."""
    if feedback is None:
        return
    signal = getattr(worker, "signal", None)
    if signal is None or not hasattr(signal, "connect"):
        return

    total = 1

    def report(message: list[Any]) -> None:
        nonlocal total
        kind = message[0] if message else None
        if kind == "start":
            total = max(int(message[1]), 1)
            feedback.setProgress(0)
        elif kind == "update":
            feedback.setProgress(int(100 * int(message[1]) / total))
        elif kind == "finished":
            feedback.setProgress(100)

    signal.connect(report)


def push_info(feedback: QgsProcessingFeedback | None, message: str) -> None:
    """Log a message if feedback is available."""
    if feedback is not None:
        feedback.pushInfo(message)
