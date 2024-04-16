#!/usr/bin/env python3

import functools
import logging
import os
import time
from pathlib import Path

import click
import coloredlogs
import sh

from handbrake_watcher import custom_log
from handbrake_watcher.watcher import watch_path_and_call_function


@click.command()
@click.option(
    "--watch-path",
    "watch_dir_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to watch for videos",
)
@click.option(
    "--output",
    "output_dir_path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Where normalized videos get written to",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Whether or not an existing output file should be overwritten",
)
@click.option("--debug", is_flag=True, default=False)
def watch(
    watch_dir_path: Path,
    output_dir_path: Path,
    overwrite: bool,
    debug: bool,
):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    coloredlogs.install(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")
    normalize_file = functools.partial(
        normalize_audio,
        output_dir_path=output_dir_path,
        overwrite=overwrite,
        watched_dir_path=watch_dir_path,
    )
    watch_path_and_call_function(watch_dir_path, normalize_file)


def normalize_audio(
    input_file_path: Path,
    output_dir_path: Path,
    overwrite: bool,
    watched_dir_path: Path,
):
    logger = logging.getLogger(__name__)
    if input_file_path.suffix not in [".mkv", ".mp4"]:
        raise Exception("Extension not supported")
    try:
        assert output_dir_path.is_dir
        output_file = output_dir_path / input_file_path.relative_to(watched_dir_path)
        logger.info(f"Normalizing {input_file_path} to {output_file}")
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Brief pause, because bears
        time.sleep(1)

        args = ["-o", output_file, "-v", "-c:a", "aac", "--keep-loudness-range-target"]
        if overwrite:
            args.append("-f")
        for line in sh.ffmpeg_normalize(
            *args,
            input_file_path,
            _iter=True,
            _log_msg=custom_log,
            _err_to_out=True,
        ):
            logger.info(line)
    except sh.ErrorReturnCode as e:
        logger.error(f"Error running ffmpeg-normalize on {input_file_path}")
        for line in e.stderr.splitlines():
            logger.error(line.decode())
    except AssertionError:
        logger.error(f"Supplied output path {output_dir_path} is not a directory")
    os.remove(input_file_path)


if __name__ == "__main__":
    watch()
