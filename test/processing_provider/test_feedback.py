"""Tests for the shared Processing feedback adapter."""

from types import SimpleNamespace

import pytest
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsProcessingFeedback

from qaequilibrae.modules.processing_provider.feedback import connect_progress, push_info


class Worker(QObject):
    signal = pyqtSignal(object)


@pytest.mark.parametrize("total, completed, expected", [(4, 1, 25), (0, 1, 100)])
def test_progress(total, completed, expected):
    worker = Worker()
    feedback = QgsProcessingFeedback()
    connect_progress(worker, feedback)
    worker.signal.emit([])
    worker.signal.emit(["update", 1])
    assert feedback.progress() == 100
    worker.signal.emit(["start", total])
    assert feedback.progress() == 0
    worker.signal.emit(["update", completed])
    assert feedback.progress() == expected
    worker.signal.emit(["finished"])
    assert feedback.progress() == 100


@pytest.mark.parametrize("worker", [None, SimpleNamespace(), SimpleNamespace(signal=object())])
def test_missing_signal(worker):
    feedback = QgsProcessingFeedback()
    connect_progress(worker, feedback)
    assert feedback.progress() == 0


def test_optional_feedback():
    connect_progress(Worker(), None)
    push_info(None, "No feedback")
    messages = []
    push_info(SimpleNamespace(pushInfo=messages.append), "Message")
    assert messages == ["Message"]
