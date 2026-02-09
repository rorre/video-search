from pathlib import Path

from PIL import Image
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from video_search.search import search_similar
from video_search.storage import open_storage
from video_search.video import hash_video


class IndexWorker(QRunnable):
    class Signals(QObject):
        progress = pyqtSignal(int, int)
        file_progress = pyqtSignal(str, float, float)
        finished = pyqtSignal()
        error = pyqtSignal(str)

    def __init__(self, directory: Path, db_path: Path, recurse: bool):
        super().__init__()
        self.directory = directory
        self.db_path = db_path
        self.recurse = recurse
        self.signals = self.Signals()
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    @pyqtSlot()
    def run(self):
        try:
            rs = "**/" if self.recurse else ""
            files = [
                *self.directory.glob(rs + "*.mp4"),
                *self.directory.glob(rs + "*.webm"),
            ]
            total = len(files)

            with open_storage(self.db_path) as storage:
                for i, path in enumerate(files):
                    if self._cancelled:
                        return
                    self.signals.progress.emit(i, total)

                    def cb(start: float, end: float):
                        self.signals.file_progress.emit(str(path.name), start, end)

                    for h in hash_video(path, progress_callback=cb):
                        if self._cancelled:
                            return
                        storage.append_hash(h)

                self.signals.progress.emit(total, total)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class SearchWorker(QRunnable):
    class Signals(QObject):
        result = pyqtSignal(object)
        finished = pyqtSignal()
        error = pyqtSignal(str)

    def __init__(self, image_path: Path, db_path: Path, threshold: float):
        super().__init__()
        self.image_path = image_path
        self.db_path = db_path
        self.threshold = threshold
        self.signals = self.Signals()

    @pyqtSlot()
    def run(self):
        try:
            with open_storage(self.db_path) as storage:
                results = search_similar(Image.open(self.image_path), storage)
                for r in results:
                    if r.similarity >= self.threshold:
                        self.signals.result.emit(r)
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))
