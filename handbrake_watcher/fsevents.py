import functools
import logging
from pathlib import Path

import click
import coloredlogs

from handbrake_watcher.watcher import watch_path_and_call_function


@click.command()
@click.option(
    "--watch-path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to watch for videos",
)
@click.option("--debug", is_flag=True, default=False)
def watch(watch_path: Path, debug: bool):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    coloredlogs.install(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")
    watch_path_and_call_function(watch_path, noop)


def noop(input_file: Path):
    pass
