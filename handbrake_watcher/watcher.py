#!/usr/bin/env python3

import functools
from typing import List
import coloredlogs
from pathlib import Path
import os
import inotify.adapters
import click
import logging
import sh
import json

from handbrake_watcher.absolute_tqdm import AbosluteTqdm


@click.command()
@click.option(
    "--watch",
    required=True,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    help="Folder to watch for videos",
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
    "--normalize-audio",
    is_flag=True,
    default=True,
    help="Should we try and normalize the audio",
)
@click.option(
    "--generate-waveforms",
    is_flag=True,
    default=False,
    help="Generates a multi-channel waveform image for both the input and output files",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Whether or not an existing output file should be overwritten",
)
@click.option("--debug", is_flag=True, default=False)
def watch(
    watch: Path,
    output: Path,
    handbrake_preset_file: str,
    handbrake_preset: str,
    normalize_audio: bool,
    generate_waveforms: bool,
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
    i = inotify.adapters.Inotify()

    i.add_watch(str(watch))
    logger.info(f"Watching {watch}")
    logger.info(f"Will output to {output}")

    trigger_events = {"IN_CLOSE_WRITE", "IN_MOVED_TO"}

    convert_video_baked = functools.partial(
        convert_video,
        output_folder=output,
        normalize_audio=normalize_audio,
        handbrake_preset=handbrake_preset,
        preset_option=preset_option,
        overwrite=overwrite,
        generate_waveforms=generate_waveforms,
    )

    for file in os.listdir(watch):
        path = watch / file
        if path.is_file():
            convert_video_baked(path)

    for event in i.event_gen(yield_nones=False):
        (_, type_names, base_path, filename) = event
        if trigger_events.intersection(type_names) and filename:
            convert_video_baked(Path(base_path) / filename)


def custom_log(ran, call_args, pid=None):
    return ran


def convert_video(
    input_path: Path,
    output_folder: Path,
    normalize_audio: bool,
    handbrake_preset: str,
    preset_option: List[str],
    overwrite: bool,
    generate_waveforms: bool,
) -> bool:
    assert input_path.is_file()
    assert output_folder.is_dir()
    logger = logging.getLogger(__name__)
    output_path = output_folder / f"{input_path.stem}.mkv"

    if output_path.exists() and not overwrite:
        logger.info(f"Output file already exists, not overwriting")
        return False

    pre_normalized_output_path = output_folder / f"{input_path.stem}.pre-normalized.mkv"

    if not is_valid_media_file(input_path):
        logger.error(f"{input_path} is not an eligable video file. Skipping")
        return False

    handbrake_output = pre_normalized_output_path if normalize_audio else output_path

    try:
        with AbosluteTqdm(total=100) as t:
            for line in sh.HandBrakeCLI(
                "--json",
                "--preset",
                handbrake_preset,
                "-i",
                input_path,
                "-o",
                handbrake_output,
                *preset_option,
                _iter=True,
                _log_msg=custom_log,
            ):
                if '"Progress":' in line:
                    percent = 100 * float(line.split(":")[1].strip().rstrip(","))
                    t.update_to(percent)

    except sh.ErrorReturnCode as e:  #
        logger.error(f"Error running handbrake on {input_path}")
        for line in e.stderr.splitlines():
            logger.error(line.decode())

    if normalize_audio:
        try:
            for line in sh.ffmpeg_normalize(
                "-o",
                output_path,
                "-v",
                "-c:a",
                "aac",
                "--progress",
                pre_normalized_output_path,
                _iter=True,
                _log_msg=custom_log,
                _err_to_out=True,
            ):
                logger.info(line)
            os.remove(pre_normalized_output_path)
        except sh.ErrorReturnCode as e:
            logger.error(f"Error running ffmpeg-normalize on {input_path}")
            for line in e.stderr.splitlines():
                logger.error(line.decode())

    if generate_waveforms:
        generate_waveform_image(input_path, output_folder, "before")
        generate_waveform_image(output_path, output_folder, "after")

    logger.info(f"Completed conversion of {input_path}")
    return True


def generate_waveform_image(input_path: Path, output_folder: Path, label: str = ""):
    assert input_path.is_file()
    assert output_folder.is_dir()
    logger = logging.getLogger(__name__)
    waveform_output = output_folder / f"{input_path.name}.{label}.waveform.png"
    for line in sh.ffmpeg(
        "-i",
        input_path,
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
