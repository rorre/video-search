import struct
from contextlib import contextmanager
from io import BytesIO
from os import PathLike
from pathlib import Path
from typing import Any, BinaryIO, Callable

import numpy as np
from imagehash import ImageHash
from PIL import Image as PILImage
from PIL.Image import Image

from video_search.hash import VideoFrameHash


class LazyVideoFrameHash:
    _frame_data: bytes

    frame: Image | None
    hash: ImageHash
    path: PathLike[str]
    time: float

    @classmethod
    def from_bytes(cls, data: bytes) -> "LazyVideoFrameHash":
        buf = BytesIO(data)

        (frame_len,) = struct.unpack("<I", buf.read(4))
        frame_data = buf.read(frame_len)

        (hash_len,) = struct.unpack("<I", buf.read(4))
        hash_array = np.load(BytesIO(buf.read(hash_len)), allow_pickle=False)

        (path_len,) = struct.unpack("<I", buf.read(4))
        path = buf.read(path_len).decode("utf-8")

        (time,) = struct.unpack("<d", buf.read(8))

        instance = cls.__new__(cls)
        instance.frame = None
        instance._frame_data = frame_data
        instance.hash = ImageHash(hash_array)
        instance.path = Path(path)
        instance.time = time
        return instance

    def load_image(self):
        if self.frame is None:
            self.frame = PILImage.open(BytesIO(self._frame_data))
        return self.frame


class HashStorage:
    def __init__(self, file: BinaryIO):
        self._file = file

    def __iter__(self):
        self._file.seek(0)
        while True:
            try:
                yield self.read_one()
            except:
                return

    def iter_with_progress(
        self, progress_callback: Callable[[float, float], Any] | None = None
    ):
        self._file.seek(0, 2)
        total = float(self._file.tell())
        self._file.seek(0)
        for item in self:
            if progress_callback:
                progress_callback(float(self._file.tell()), total)
            yield item

        if progress_callback:
            progress_callback(total, total)

    def append_hash(self, hash: VideoFrameHash):
        data = hash.to_bytes()
        self._file.write(struct.pack("<I", len(data)))
        self._file.write(data)

    def read_one(self):
        (hash_len,) = struct.unpack("<I", self._file.read(4))
        return LazyVideoFrameHash.from_bytes(self._file.read(hash_len))


@contextmanager
def open_storage(path: PathLike):
    with open(path, "ab+") as f:
        yield HashStorage(f)
