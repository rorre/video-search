import struct
from contextlib import contextmanager
from os import PathLike
from typing import BinaryIO

from video_search.hash import VideoFrameHash


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

    def append_hash(self, hash: VideoFrameHash):
        data = hash.to_bytes()
        self._file.write(struct.pack("<I", len(data)))
        self._file.write(data)

    def read_one(self):
        (hash_len,) = struct.unpack("<I", self._file.read(4))
        return VideoFrameHash.from_bytes(self._file.read(hash_len))

    def seek(self, i: int):
        self._file.seek(0)
        for _ in range(i):
            self.read_one()


@contextmanager
def open_storage(path: PathLike):
    with open(path, "ab+") as f:
        yield HashStorage(f)
