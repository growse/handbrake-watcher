import logging
import os
import time
from pathlib import Path
from typing import Callable

import watchdog
from watchdog.events import FileClosedEvent, FileMovedEvent, FileSystemEvent
from watchdog.observers.polling import PollingObserver


def watch_path_and_call_function(
    path_to_watch: Path,
    function_to_call: Callable[[Path], None],
    process_existing: bool = True,
):
    logger = logging.getLogger(__name__)
    try:
        assert path_to_watch.is_dir
    except AssertionError:
        logger.error(f"{path_to_watch} is not a directory")

    class EventHandler(watchdog.events.FileSystemEventHandler):
        def on_any_event(self, event: FileSystemEvent) -> None:
            if event.event_type in ["closed", "moved"] and not event.is_directory:
                if event.event_type == "moved":
                    logger.info(
                        f"File moved from {event.src_path} to {event.dest_path}"
                    )
                    path = Path(event.dest_path)
                else:
                    logger.info(f"File closed at {event.src_path}")
                    path = Path(event.src_path)
                try:
                    function_to_call(path)
                except Exception as e:
                    logger.error(f"Error processing {path}: {e}")
            else:
                if not event.is_directory and event.event_type != "modified":
                    logger.info(f"Ignoring event: {event}")

    # NFS doesn't support inotify
    observer = PollingObserver()
    event_handler = EventHandler()
    observer.schedule(event_handler, str(path_to_watch), recursive=True)

    if process_existing:
        existing_files = os.walk(path_to_watch)
        for existing_dir in existing_files:
            for existing_file in existing_dir[2]:
                existing_path = Path(existing_dir[0]) / existing_file
                if existing_path.is_file():
                    logger.info(f"Found existing file: {existing_path}")
                    event = FileMovedEvent(existing_path, existing_path)
                    event_handler.on_any_event(event)

    observer.start()

    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
