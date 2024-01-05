#!/usr/bin/env python3

import functools
import json
import logging
import os
from pathlib import Path
from typing import List

import click
import coloredlogs
import sh

from handbrake_watcher import custom_log
from handbrake_watcher.absolute_tqdm import AbosluteTqdm
from handbrake_watcher.watcher import watch_path_and_call_function


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
)
@click.option(
    "--handbrake-preset-file",
    type=click.Path(exists=True),
    help="A handbrake preset file",
)
@click.option(
    "--handbrake-preset",
    default="CLI Default",
    show_default=True,
    help="The handbrake preset to use for conversion",
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
    handbrake_preset_file: str,
    handbrake_preset: str,
    overwrite: bool,
    debug: bool,
):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    coloredlogs.install(level=logging.DEBUG if debug else logging.INFO)
    logger = logging.getLogger(__name__)
    logger.debug("Debug logging enabled")
    preset_option = (
        ["--preset-import-file", handbrake_preset_file] if handbrake_preset_file else []
    )
    logger.debug("Testing handbrake options")
    try:
        sh.HandBrakeCLI(
            "--preset",
            handbrake_preset,
            "-i",
            "null",
            "-o",
            "null",
            *preset_option,
            _log_msg=custom_log,
        )
    except sh.ErrorReturnCode as e:
        if "No title found" not in e.stderr.decode("utf-8"):
            logger.fatal(f"Handbrake Error")
            for line in e.stderr.splitlines():
                logger.fatal(line.decode("utf-8"))
            exit(1)

    logger.info(f"Using HandBrake preset of {handbrake_preset}")

    completed_folder_path = watch_path / "completed"
    os.makedirs(completed_folder_path, exist_ok=True)

    convert_video_baked = functools.partial(
        convert_video,
        output_folder=output,
        handbrake_preset=handbrake_preset,
        preset_option=preset_option,
        overwrite=overwrite,
        completed_folder_path=completed_folder_path,
    )
    watch_path_and_call_function(watch_path, convert_video_baked)


def convert_video(
    input_path: Path,
    output_folder: Path,
    handbrake_preset: str,
    preset_option: List[str],
    overwrite: bool,
    completed_folder_path: Path,
):
    logger = logging.getLogger(__name__)
    try:
        assert input_path.is_file()
        assert output_folder.is_dir()

    except AssertionError:
        logger.exception("Unable to convert {path}")

    output_path = output_folder / f"{input_path.stem}.mkv"

    if output_path.exists() and not overwrite:
        logger.info(f"Output file already exists, not overwriting")

    if not is_valid_media_file(input_path):
        logger.error(f"{input_path} is not an eligable video file. Skipping")

    try:
        with AbosluteTqdm(total=100) as t:
            for line in sh.HandBrakeCLI(
                "--json",
                "--preset",
                handbrake_preset,
                "-i",
                input_path,
                "-o",
                output_path,
                *preset_option,
                _iter=True,
                _log_msg=custom_log,
            ):
                if '"Progress":' in line:
                    percent = 100 * float(line.split(":")[1].strip().rstrip(","))
                    t.update_to(percent)
        completed_video_file = completed_folder_path / input_path.name
        logger.info(f"Moving {input_path} to {completed_video_file}")
        os.rename(input_path, completed_video_file)

        logger.info(f"Completed conversion of {input_path}")

    except sh.ErrorReturnCode as e:  #
        logger.error(f"Error running handbrake on {input_path}")
        for line in e.stderr.splitlines():
            logger.error(line.decode())

    return True


def is_valid_media_file(input_path: Path) -> bool:
    logger = logging.getLogger(__name__)
    try:
        probe_output = sh.HandBrakeCLI("--json", "--scan", "-i", input_path)
        metadata = json.loads(probe_output.partition("JSON Title Set:")[2])
        main_title = metadata["TitleList"][metadata["MainFeature"]]
        framerate = int(main_title["FrameRate"]["Num"]) / int(
            main_title["FrameRate"]["Den"]
        )
        geometry = (
            f'{main_title["Geometry"]["Width"]}x{main_title["Geometry"]["Height"]}'
        )
        duration = f'{main_title["Duration"]["Hours"]}:{main_title["Duration"]["Minutes"]}m:{main_title["Duration"]["Seconds"]}s'
        video_codec = main_title["VideoCodec"]
        if video_codec == "libav1":
            return False
        logger.info(f"main title: {geometry} @{framerate}fps {video_codec} {duration}")

        audio_streams = main_title["AudioList"]
        audio_stream_codecs = ",".join(
            map(
                lambda stream: f"{stream['Language']} ({stream['BitRate']}bps @{stream['SampleRate']}Hz {stream['CodecName']} {stream['ChannelLayoutName']})",
                audio_streams,
            )
        )
        logger.info(
            f"Found {len(audio_streams)} audio streams in source: {audio_stream_codecs}"
        )
        if len(audio_streams) == 0:
            return False
    except sh.ErrorReturnCode as e:
        return False
    return True


if __name__ == "__main__":
    watch()
