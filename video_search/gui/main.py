import os
import sys
from io import BytesIO
from pathlib import Path

from PIL.Image import Image
from PyQt6.QtCore import Qt, QThreadPool
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qt_material import apply_stylesheet

from video_search.gui.workers import IndexWorker, SearchWorker


def pil_to_pixmap(image: Image) -> QPixmap:
    buf = BytesIO()
    image.save(buf, format="PNG")
    data = buf.getvalue()
    qimg = QImage()
    qimg.loadFromData(data)
    return QPixmap.fromImage(qimg)


def format_seconds(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:07.4f}"


class ResultCard(QFrame):
    def __init__(self, pixmap: QPixmap, path: str, time: float, similarity: float):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        thumb = QLabel()
        scaled = pixmap.scaled(
            160,
            120,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        thumb.setPixmap(scaled)
        thumb.setFixedSize(160, 120)
        thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(thumb)

        info = QVBoxLayout()
        info.setSpacing(4)

        path_label = QLabel(f"<b>{path}</b>")
        path_label.setWordWrap(True)
        info.addWidget(path_label)

        time_label = QLabel(f"Time: {format_seconds(time)}")
        info.addWidget(time_label)

        pct = similarity * 100
        primary = "#4caf50"
        warn = "#ff9800"
        bad = "#f44336"

        color = primary if pct >= 90 else warn if pct >= 70 else bad
        sim_label = QLabel(f"Similarity: <span style='color:{color}'>{pct:.1f}%</span>")
        info.addWidget(sim_label)

        info.addStretch()
        layout.addLayout(info, 1)


class Settings:
    def __init__(self):
        self.db_path = "data.db"
        self.threshold = 0.80


class SettingsTab(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        form = QFormLayout()

        self._db_edit = QLineEdit(settings.db_path)
        self._db_edit.textChanged.connect(self._on_db_changed)
        db_row = QHBoxLayout()
        db_row.addWidget(self._db_edit, 1)
        db_browse = QPushButton("Browse...")
        db_browse.clicked.connect(self._browse_db)
        db_row.addWidget(db_browse)
        form.addRow("Database path:", db_row)

        self._threshold = QDoubleSpinBox()
        self._threshold.setRange(0.0, 1.0)
        self._threshold.setSingleStep(0.05)
        self._threshold.setValue(settings.threshold)
        self._threshold.setDecimals(2)
        self._threshold.valueChanged.connect(self._on_threshold_changed)
        form.addRow("Search threshold:", self._threshold)

        layout.addLayout(form)
        layout.addStretch()

    def _browse_db(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Select Database File",
            self._db_edit.text(),
            "Database (*.db);;All Files (*)",
        )
        if path:
            self._db_edit.setText(path)

    def _on_db_changed(self, text: str):
        self._settings.db_path = text.strip() or "data.db"

    def _on_threshold_changed(self, value: float):
        self._settings.threshold = value


class IndexTab(QWidget):
    def __init__(self, settings: Settings, status_bar: QStatusBar):
        super().__init__()
        self._settings = settings
        self._status_bar = status_bar
        self._worker: IndexWorker | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Directory:"))
        self._dir_edit = QLineEdit()
        self._dir_edit.setPlaceholderText("Select a directory containing videos...")
        dir_row.addWidget(self._dir_edit, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        layout.addLayout(dir_row)

        opts_row = QHBoxLayout()
        self._recurse_cb = QCheckBox("Scan recursively")
        opts_row.addWidget(self._recurse_cb)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        self._progress_group = QWidget()
        self._progress_group.setVisible(False)
        pg_layout = QVBoxLayout(self._progress_group)
        pg_layout.setContentsMargins(0, 0, 0, 0)
        pg_layout.setSpacing(6)

        self._overall_label = QLabel("Overall:")
        pg_layout.addWidget(self._overall_label)
        self._overall_progress = QProgressBar()
        self._overall_progress.setFormat("%v / %m files")
        pg_layout.addWidget(self._overall_progress)

        self._file_label = QLabel("Current file:")
        pg_layout.addWidget(self._file_label)
        self._file_progress = QProgressBar()
        self._file_progress.setFormat("%p%")
        pg_layout.addWidget(self._file_progress)

        layout.addWidget(self._progress_group)

        btn_row = QHBoxLayout()
        self._index_btn = QPushButton("Start Indexing")
        self._index_btn.setProperty("class", "danger")
        self._index_btn.clicked.connect(self._start_index)
        btn_row.addStretch()
        btn_row.addWidget(self._index_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Select Video Directory")
        if d:
            self._dir_edit.setText(d)

    def _start_index(self):
        directory = self._dir_edit.text().strip()
        if not directory:
            QMessageBox.warning(
                self, "No Directory", "Please select a directory first."
            )
            return

        path = Path(directory)
        if not path.is_dir():
            QMessageBox.warning(
                self, "Invalid Directory", "The selected path is not a valid directory."
            )
            return

        db_path = Path(self._settings.db_path)

        self._index_btn.setEnabled(False)
        self._progress_group.setVisible(True)
        self._overall_progress.setValue(0)
        self._file_progress.setValue(0)
        self._status_bar.showMessage("Indexing...")

        self._worker = IndexWorker(path, db_path, self._recurse_cb.isChecked())
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.file_progress.connect(self._on_file_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_progress(self, current: int, total: int):
        self._overall_progress.setMaximum(total)
        self._overall_progress.setValue(current)
        self._overall_label.setText(f"Overall: {current} / {total} files")

    def _on_file_progress(self, name: str, start: float, end: float):
        self._file_label.setText(f"Current file: {name}")
        if end > 0:
            self._file_progress.setMaximum(1000)
            self._file_progress.setValue(int(start / end * 1000))
        else:
            self._file_progress.setValue(0)

    def _on_finished(self):
        self._index_btn.setEnabled(True)
        self._progress_group.setVisible(False)
        self._status_bar.showMessage("Indexing complete.", 5000)
        self._worker = None

    def _on_error(self, msg: str):
        self._index_btn.setEnabled(True)
        self._progress_group.setVisible(False)
        self._status_bar.showMessage("Indexing failed.", 5000)
        QMessageBox.critical(self, "Error", msg)
        self._worker = None


class SearchTab(QWidget):
    def __init__(self, settings: Settings, status_bar: QStatusBar):
        super().__init__()
        self._settings = settings
        self._status_bar = status_bar
        self._image_path: Path | None = None
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Image:"))
        self._image_edit = QLineEdit()
        self._image_edit.setPlaceholderText("Select or drop an image to search...")
        self._image_edit.setReadOnly(True)
        top_row.addWidget(self._image_edit, 1)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_image)
        top_row.addWidget(browse_btn)
        self._search_btn = QPushButton("Search")
        self._search_btn.clicked.connect(self._start_search)
        top_row.addWidget(self._search_btn)
        layout.addLayout(top_row)

        self._preview = QLabel()
        self._preview.setFixedHeight(150)
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setObjectName("imagePreview")
        self._preview.setText("No image selected")
        layout.addWidget(self._preview)

        self._results_area = QScrollArea()
        self._results_area.setWidgetResizable(True)
        self._results_container = QWidget()
        self._results_layout = QVBoxLayout(self._results_container)
        self._results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._results_area.setWidget(self._results_container)
        layout.addWidget(self._results_area, 1)

    def _browse_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp *.webp)"
        )
        if path:
            self._set_image(Path(path))

    def _set_image(self, path: Path):
        self._image_path = path
        self._image_edit.setText(str(path))
        pixmap = QPixmap(str(path))
        scaled = pixmap.scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._preview.setPixmap(scaled)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp", ".webp"):
                self._set_image(path)

    def _clear_results(self):
        while self._results_layout.count():
            item = self._results_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _start_search(self):
        if not self._image_path:
            QMessageBox.warning(self, "No Image", "Please select an image first.")
            return

        db_path = Path(self._settings.db_path)
        if not db_path.exists():
            QMessageBox.warning(
                self,
                "No Database",
                f"Database file '{db_path}' not found. Index some videos first.",
            )
            return

        self._clear_results()
        self._search_btn.setEnabled(False)
        self._status_bar.showMessage("Searching...")

        worker = SearchWorker(self._image_path, db_path, self._settings.threshold)
        worker.signals.result.connect(self._on_result)
        worker.signals.finished.connect(self._on_finished)
        worker.signals.error.connect(self._on_error)
        QThreadPool.globalInstance().start(worker)

    def _on_result(self, result):
        pixmap = pil_to_pixmap(result.match.frame)
        card = ResultCard(
            pixmap, str(result.match.path), result.match.time, result.similarity
        )
        self._results_layout.addWidget(card)

    def _on_finished(self):
        self._search_btn.setEnabled(True)
        count = self._results_layout.count()
        self._status_bar.showMessage(f"Found {count} result(s).", 5000)
        if count == 0:
            lbl = QLabel("No results found.")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._results_layout.addWidget(lbl)

    def _on_error(self, msg: str):
        self._search_btn.setEnabled(True)
        self._status_bar.showMessage("Search failed.", 5000)
        QMessageBox.critical(self, "Error", msg)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video Search")
        self.setMinimumSize(700, 500)
        self.resize(900, 650)

        self._settings = Settings()

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 4)
        main_layout.setSpacing(8)

        status_bar = QStatusBar()
        self.setStatusBar(status_bar)

        tabs = QTabWidget()
        tabs.addTab(IndexTab(self._settings, status_bar), "Index")
        tabs.addTab(SearchTab(self._settings, status_bar), "Search")
        tabs.addTab(SettingsTab(self._settings), "Settings")
        main_layout.addWidget(tabs, 1)


def main():
    app = QApplication(sys.argv)
    apply_stylesheet(app, theme="dark_blue.xml")

    extra_qss = """
    QLabel#imagePreview {
        border: 1px dashed palette(mid);
        border-radius: 4px;
    }
    """
    app.setStyleSheet(app.styleSheet() + extra_qss)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
