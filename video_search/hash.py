import struct
from dataclasses import dataclass
from io import BytesIO
from os import PathLike
from pathlib import Path

import numpy as np
from imagehash import ImageHash
from PIL import Image as PILImage
from PIL.Image import Image


@dataclass
class VideoFrameHash:
    frame: Image
    hash: ImageHash
    path: PathLike[str]
    time: float

    def to_bytes(self) -> bytes:
        with BytesIO() as im:
            self.frame.save(im, format="PNG")
            frame_data = im.getvalue()

        with BytesIO() as hashf:
            np.save(hashf, self.hash.hash, False)
            hash_data = hashf.getvalue()

        path_data = str(self.path).encode("utf-8")

        buf = BytesIO()
        buf.write(struct.pack("<I", len(frame_data)))
        buf.write(frame_data)
        buf.write(struct.pack("<I", len(hash_data)))
        buf.write(hash_data)
        buf.write(struct.pack("<I", len(path_data)))
        buf.write(path_data)
        buf.write(struct.pack("<d", self.time))
        return buf.getvalue()

    @classmethod
    def from_bytes(cls, data: bytes) -> "VideoFrameHash":
        buf = BytesIO(data)

        (frame_len,) = struct.unpack("<I", buf.read(4))
        frame = PILImage.open(BytesIO(buf.read(frame_len)))

        (hash_len,) = struct.unpack("<I", buf.read(4))
        hash_array = np.load(BytesIO(buf.read(hash_len)), allow_pickle=False)

        (path_len,) = struct.unpack("<I", buf.read(4))
        path = buf.read(path_len).decode("utf-8")

        (time,) = struct.unpack("<d", buf.read(8))

        instance = cls.__new__(cls)
        instance.frame = frame
        instance.hash = ImageHash(hash_array)
        instance.path = Path(path)
        instance.time = time
        return instance
