from os import PathLike
from typing import Any, Callable

import av
from imagehash import ImageHash, phash
from PIL.Image import Image
from video_search.hash import VideoFrameHash
from av.video.reformatter import Interpolation

THRESHOLD = 0.2


def calculate_thumbnail_size(
    original_size: tuple[int, int],
    target_size: tuple[int, int],
) -> tuple[int, int]:
    orig_w, orig_h = original_size
    targ_w, targ_h = target_size

    ratio_w = targ_w / orig_w
    ratio_h = targ_h / orig_h

    scaling_factor = min(ratio_w, ratio_h, 1.0)
    new_w = round(orig_w * scaling_factor)
    new_h = round(orig_h * scaling_factor)

    return (new_w, new_h)


def hash_video(
    video: PathLike,
    hash_algorithm: Callable[[Image], ImageHash] = phash,
    progress_callback: Callable[[float, float], Any] | None = None,
):
    vid = av.open(video, mode="r")

    previous_hash = None
    duration_micro = vid.duration or 0
    real_duration: float = duration_micro / 1_000_000  # type: ignore
    for frame in vid.decode(video=0):
        thumbnail_size = calculate_thumbnail_size(
            (frame.width, frame.height),
            (128, 128),
        )

        im: Image = frame.to_image(
            width=thumbnail_size[0],
            height=thumbnail_size[1],
            interpolation=Interpolation.LANCZOS,
        )
        current = hash_algorithm(im)
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
            if progress_callback:
                progress_callback(frame.time, real_duration)
            previous_hash = current

    if progress_callback:
        progress_callback(real_duration, real_duration)
    vid.close()
