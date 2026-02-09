from os import PathLike
from typing import Any, Callable

import av
from imagehash import ImageHash, dhash, phash
from PIL.Image import Image

from video_search.hash import VideoFrameHash

THRESHOLD = 0.2


def hash_video(
    video: PathLike,
    hash_algorithm: Callable[[Image], ImageHash] = phash,
    progress_callback: Callable[[float, float], Any] | None = None,
):
    vid = av.open(video)

    previous_hash = None
    real_duration: float = vid.duration / 1_000_000  # type: ignore
    for frame in vid.decode(video=0):
        im: Image = frame.to_image()
        current = hash_algorithm(im)

        im.thumbnail((128, 128))
        frame_hash = VideoFrameHash(im, current, video, frame.time)

        if not previous_hash:
            if progress_callback:
                progress_callback(frame.time, real_duration)
            yield frame_hash
            previous_hash = current
            continue

        pct = (current - previous_hash) / 64
        if pct > THRESHOLD:
            yield frame_hash
            progress_callback(frame.time, real_duration)
            previous_hash = current

    if progress_callback:
        progress_callback(real_duration, real_duration)
    vid.close()
