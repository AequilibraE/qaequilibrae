from PyQt5.QtCore import QTimer


class Debouncer:
    """Delays signal emissions"""

    def __init__(self, delay_ms=3000, callback=None):
        self.delay_ms = delay_ms
        self.callback = callback
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._on_timeout)
        self._pending_args = None

    def __call__(self, *args):
        """Allows instance to be used as slot or decorator"""
        self._pending_args = args
        self.timer.start(self.delay_ms)

    def _on_timeout(self):
        if self._pending_args is not None and self.callback is not None:
            self.callback(*self._pending_args)
            self._pending_args = None

    def cancel(self):
        """Cancel pending action"""
        self.timer.stop()
        self._pending_args = None
