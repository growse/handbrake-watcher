import logging
from pathlib import Path

import click
import coloredlogs
import sh

from handbrake_watcher import custom_log


@click.command()
@click.option(
    "--input",
    required=True,
    type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path),
    help="Where normalized videos get written to",
)
@click.option("--debug", is_flag=True, default=False)
def generate_waveform_image(input: Path, debug: bool):
    assert input.is_file()
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    coloredlogs.install(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")
    waveform_output = input.parent / f"{input.stem}.waveform.png"
    for line in sh.ffmpeg(
        "-i",
        input,
        "-y",
        "-filter_complex",
        "showwavespic=s=2000x1000:split_channels=1",
        "-frames:v",
        "1",
        waveform_output,
        _iter=True,
        _log_msg=custom_log,
        _err_to_out=True,
    ):
        logger.info(line)


if __name__ == "__main__":
    generate_waveform_image()
