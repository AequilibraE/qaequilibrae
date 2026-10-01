import pytest
from qgis.PyQt.QtCore import QThread

from qaequilibrae.modules.common_tools.processing_worker import ProcessingWorker


@pytest.mark.parametrize("fail", [False, True])
def test_processing_worker_forwards_feedback_and_captures_outcome(qtbot, fail):
    parameters, project, zones = {}, object(), object()

    def runner(inputs, *, project, feedback, zones):
        assert QThread.currentThread() is worker
        assert inputs is parameters
        assert project is worker.project
        assert zones is worker.options["zones"]
        feedback.pushInfo("Running")
        feedback.setProgress(50)
        if fail:
            raise ValueError("Failed")
        return {"output": "result"}

    worker = ProcessingWorker(runner, parameters, project, None, zones=zones)
    messages, progress = [], []
    worker.message.connect(messages.append)
    worker.progress.connect(progress.append)
    with qtbot.waitSignal(worker.finished):
        worker.start()
    worker.wait()
    assert messages == ["Running"]
    assert progress == [50]
    assert worker.error == ("Failed" if fail else None)
    assert worker.result == (None if fail else {"output": "result"})


def test_processing_worker_forwards_cancellation(qtbot):
    def runner(inputs, *, project, feedback):
        return feedback.isCanceled()

    worker = ProcessingWorker(runner, {}, None, None)
    worker.cancel()
    with qtbot.waitSignal(worker.finished):
        worker.start()
    worker.wait()
    assert worker.result is True
    assert worker.error is None
