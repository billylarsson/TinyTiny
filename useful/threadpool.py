import threading, time
from PyQt6.QtCore import pyqtSignal, QObject

class BackgroundThenMain(QObject):
    trigger = pyqtSignal()
    def background(self, delay: int | float):
        time.sleep(delay)
        self.trigger.emit()


def custom_thread(fn, delay: int | float):
    runner = BackgroundThenMain()
    runner.trigger.connect(fn)
    t = threading.Thread(target=runner.background, args=(delay,))
    t.daemon = True
    t.start()
