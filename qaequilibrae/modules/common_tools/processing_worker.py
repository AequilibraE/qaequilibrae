"""Run Processing operations off the UI thread and forward their feedback."""

from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import QgsProcessingFeedback


class _DialogFeedback(QgsProcessingFeedback):
    message = pyqtSignal(str)

    def __init__(self, cancellation_requested):
        super().__init__()
        self.cancellation_requested = cancellation_requested

    def pushInfo(self, message):
        super().pushInfo(message)
        self.message.emit(message)

    def isCanceled(self):
        return self.cancellation_requested() or super().isCanceled()


class ProcessingWorker(QThread):
    """Call a Processing runner, retaining its result or error for the dialog."""

    message = pyqtSignal(str)
    progress = pyqtSignal(float)

    def __init__(self, runner, parameters, project, parent, **options):
        super().__init__(parent)
        self.runner = runner
        self.parameters = parameters
        self.project = project
        self.options = options
        self.error = None
        self.result = None
        self.cancel_requested = False

    def cancel(self):
        self.cancel_requested = True

    def run(self):
        try:
            feedback = _DialogFeedback(lambda: self.cancel_requested)
            feedback.message.connect(self.message.emit)
            feedback.progressChanged.connect(self.progress.emit)
            self.result = self.runner(self.parameters, project=self.project, feedback=feedback, **self.options)
        except Exception as error:
            self.error = str(error)
