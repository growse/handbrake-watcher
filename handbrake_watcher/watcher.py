import logging
import os
import time
from pathlib import Path
from typing import Callable

import inotify
import watchdog
from watchdog.events import LoggingEventHandler
from watchdog.observers import Observer


def call_function_for_each_file(
    path_to_enumerate: Path, function_to_call: Callable[[Path], None]
):
    logger = logging.getLogger(__name__)
    try:
        assert path_to_enumerate.is_dir
    except AssertionError:
        logger.error(f"{path_to_enumerate} is not a directory")

    for file in os.listdir(path_to_enumerate):
        path = path_to_enumerate / file
        if path.is_file():
            function_to_call(path)


def watch_path_and_call_function(
    path_to_watch: Path, function_to_call: Callable[[Path], None]
):
    logger = logging.getLogger(__name__)
    try:
        assert path_to_watch.is_dir
    except AssertionError:
        logger.error(f"{path_to_watch} is not a directory")

    class EventHandler(watchdog.events.FileSystemEventHandler):
        def on_created(self, event):
            if not event.is_directory:
                print(f"Created: {event}")
                function_to_call(Path(event.src_path))

        def on_closed(self, event):
            if not event.is_directory:
                function_to_call(Path(event.src_path))

    observer = Observer()
    observer.schedule(EventHandler(), path_to_watch, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
