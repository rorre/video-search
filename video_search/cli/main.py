from pathlib import Path
from typing import Annotated

import typer
from PIL import Image
from rich import print
from rich.panel import Panel
from rich.progress import Progress, track
from rich_pixels import Pixels

from video_search.search import search_similar
from video_search.storage import open_storage
from video_search.video import hash_video

app = typer.Typer()
global_config = {"db": Path("data.db")}


def format_seconds(total_seconds: float) -> str:
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:07.4f}"


@app.command()
def index(
    directory: Annotated[
        Path, typer.Argument(help="Directory to scan for video files and index")
    ],
    recurse: Annotated[bool, typer.Option(help="Run scan recursively")] = False,
):
    rs = ""
    if recurse:
        rs = "**/"

    with open_storage(global_config["db"]) as storage:
        for path in track(
            [*directory.glob(rs + "*.mp4"), *directory.glob(rs + "*.webm")],
            description="Processing videos...",
        ):
            with Progress() as progress:
                task = progress.add_task(f"Processing video {path}...")

                def cb(start: float, end: float):
                    progress.update(task, total=end, completed=start)

                for hash in hash_video(path, progress_callback=cb):
                    storage.append_hash(hash)


@app.command()
def search(
    image: Annotated[Path, typer.Argument(help="Image file to find for the source")],
    threshold: Annotated[float, typer.Option(help="Threshold for similarity")] = 0.8,
):
    with open_storage(global_config["db"]) as storage:
        res = search_similar(Image.open(image), storage)
        for x in res:
            if x.similarity < threshold:
                continue

            print(
                Panel(
                    Pixels.from_image(x.match.frame),
                    title=str(x.match.path),
                    subtitle=f"Time: {format_seconds(x.match.time)}s | Similarity {x.similarity}",
                )
            )


@app.callback()
def main(
    db_path: Annotated[Path, typer.Option(help="Path to database")] = Path("data.db"),
):
    global_config["db"] = db_path
