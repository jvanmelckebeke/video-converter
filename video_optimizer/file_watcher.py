"""File system watcher for detecting new video files."""
import logging
import os
import queue
from typing import Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from video_optimizer.config import Configuration
from video_optimizer.utils import Utils


class VideoFileHandler(FileSystemEventHandler):
    """Handles file system events for video files."""

    def __init__(self, config: Configuration, file_queue: queue.Queue, processed_files: Set[str]):
        self.config = config
        self.file_queue = file_queue
        self.processed_files = processed_files
        self._skip_dirs = {
            config.OUTPUT_ROOT,
            config.ERRORED_ROOT,
            config.IN_PROGRESS_ROOT,
            config.DONE_ROOT,
            config.OPTIMIZED_BAD_ROOT,
            config.OPTIMIZED_ORIGINAL_ROOT,
        }

    def _should_process(self, path: str) -> bool:
        """Check if the file should be processed."""
        # Skip if already processed
        if path in self.processed_files:
            return False

        # Skip if not a video file
        if not Utils.is_video_file(path, self.config):
            return False

        # Skip if in an output directory (check path components, not substring)
        path_parts = os.path.normpath(path).split(os.sep)
        for skip_dir in self._skip_dirs:
            if skip_dir in path_parts:
                return False

        return True

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation events."""
        if event.is_directory:
            return

        if self._should_process(event.src_path):
            logging.debug(f"Detected new video file: {event.src_path}")
            self.file_queue.put(event.src_path)

    def on_moved(self, event: FileMovedEvent) -> None:
        """Handle file move events (files moved into watched directory)."""
        if event.is_directory:
            return

        if self._should_process(event.dest_path):
            logging.debug(f"Detected moved video file: {event.dest_path}")
            self.file_queue.put(event.dest_path)


class FileWatcher:
    """Watches a directory for new video files using inotify/FSEvents."""

    def __init__(self, config: Configuration, processed_files: Set[str]):
        self.config = config
        self.processed_files = processed_files
        self.file_queue: queue.Queue = queue.Queue()
        self._observer: Optional[Observer] = None
        self._running = False

    def start(self) -> bool:
        """Start the file system watcher. Returns True if successful."""
        try:
            self._observer = Observer()
            handler = VideoFileHandler(self.config, self.file_queue, self.processed_files)
            self._observer.schedule(handler, self.config.SOURCE_ROOT, recursive=True)
            self._observer.start()
            self._running = True
            logging.info(f"File system watcher started for: {self.config.SOURCE_ROOT}")
            return True
        except Exception as e:
            logging.warning(f"Failed to start file system watcher: {e}")
            logging.warning("Falling back to polling mode")
            return False

    def stop(self) -> None:
        """Stop the file system watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._running = False
            logging.info("File system watcher stopped")

    def get_file(self, timeout: Optional[float] = None) -> Optional[str]:
        """Get the next file from the queue, blocking up to timeout seconds."""
        try:
            return self.file_queue.get(timeout=timeout)
        except queue.Empty:
            return None
