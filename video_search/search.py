import heapq
from dataclasses import dataclass
from typing import Any, Callable

from imagehash import ImageHash, phash
from PIL.Image import Image

from video_search.storage import HashStorage, LazyVideoFrameHash


@dataclass
class Result:
    base: ImageHash
    match: LazyVideoFrameHash

    def __lt__(self, other: "Result"):
        # !!! Value is negated for purpose of max heap
        return -self._value() < -other._value()

    def _value(self):
        return self.match.hash - self.base

    @property
    def similarity(self):
        return 1.0 - (self._value() / 64)


def search_similar(
    image: Image,
    storage: HashStorage,
    hash_algorithm: Callable[[Image], ImageHash] = phash,
    top_n: int = 50,
    progress_callback: Callable[[float, float], Any] | None = None,
):
    current_hash = hash_algorithm(image)

    # The heap must be a max-heap, because heappushpop() will pop the lowest value
    # Therefore when all of this are done, it will be the least differ from base.
    h: list[Result] = []
    for hash in storage.iter_with_progress(progress_callback):
        c = Result(current_hash, hash)
        if len(h) < top_n:
            heapq.heappush(h, c)
        else:
            heapq.heappushpop(h, c)

    # Result is reversed because of max heap
    return reversed([heapq.heappop(h) for i in range(len(h))])
