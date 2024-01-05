import functools
import logging
from pathlib import Path

import click
import coloredlogs
import sh

from . import custom_log
from .watcher import call_function_for_each_file, watch_path_and_call_function


@click.command()
@click.option(
    "--watch-path",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Directory to watch for videos",
)
@click.option(
    "--output",
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
    watch_path: Path,
    output: Path,
    overwrite: bool,
    debug: bool,
):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    coloredlogs.install(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")
    normalize_file = functools.partial(
        normalize_audio, output_path=output, overwrite=overwrite
    )
    # call_function_for_each_file(watch_path, normalize_file)
    watch_path_and_call_function(watch_path, normalize_file)


def normalize_audio(input_path: Path, output_path: Path, overwrite: bool):
    logger = logging.getLogger(__name__)
    try:
        assert output_path.is_dir
        output_file = output_path / input_path.name
        for line in sh.ffmpeg_normalize(
            "-o",
            output_file,
            "-v",
            "-c:a",
            "aac",
            "--keep-loudness-range-target",
            input_path,
            _iter=True,
            _log_msg=custom_log,
            _err_to_out=True,
        ):
            logger.info(line)
    except sh.ErrorReturnCode as e:
        logger.error(f"Error running ffmpeg-normalize on {input_path}")
        for line in e.stderr.splitlines():
            logger.error(line.decode())
    except AssertionError:
        logger.error(f"Supplied output path {output_path} is not a directory")


if __name__ == "__main__":
    watch()
