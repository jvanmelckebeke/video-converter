import os
import shutil
import logging
from typing import Set, List

from video_optimizer.config import Configuration
from video_optimizer.utils import Utils


class FileManager:
    """
    Manages file operations for the video optimization process.
    Corrected to reflect proper 'in-progress' directory usage.
    """

    def __init__(self, config: Configuration):
        """
        Initializes the FileManager with a Configuration object.
        """
        self.config = config

    def _move_file(self, source_path: str, dest_path: str) -> None:
        """
        Moves a file from source to destination, creating destination directories if necessary.
        Handles potential exceptions during file moving.

        Args:
            source_path (str): Path to the source file.
            dest_path (str): Path to the destination.
        """
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        try:
            shutil.move(source_path, dest_path)
            logging.info(f"Moved '{Utils.shorten_filepath(source_path, self.config.SOURCE_ROOT)}' to '{Utils.shorten_filepath(dest_path, self.config.SOURCE_ROOT)}'")
        except Exception as e:
            logging.error(f"Failed to move '{source_path}' to '{dest_path}': {e}")
            raise

    def move_file_with_structure(self, source_path: str, dest_root: str, rel_path: str) -> None:
        """
        Moves a file to a destination root, preserving the relative directory structure.

        Args:
            source_path (str): Path to the source file.
            dest_root (str): Root directory for the destination.
            rel_path (str): Relative path of the file within the source root.
        """
        dest_path = os.path.join(dest_root, rel_path)
        self._move_file(source_path, dest_path)

    def get_in_progress_path(self, rel_path: str) -> str:
        """Returns the path for the in-progress file (without moving the original)."""
        return os.path.join(self.config.IN_PROGRESS_ROOT, rel_path)

    def get_output_path(self, rel_path: str) -> str:
        """Returns the path for the optimized output file (without moving)."""
        return os.path.join(self.config.OUTPUT_ROOT, rel_path)

    def move_to_errored(self, source_path: str, rel_path: str) -> str:
        """Moves the *original* file to the errored directory."""
        dest_path = os.path.join(self.config.ERRORED_ROOT, rel_path)
        self._move_file(source_path, dest_path)
        return dest_path

    def move_to_done(self, source_path: str, rel_path: str) -> str:
        """Moves the *original* file to the done directory."""
        dest_path = os.path.join(self.config.DONE_ROOT, rel_path)
        self._move_file(source_path, dest_path)
        return dest_path

    def move_to_optimized_bad(self, optimized_path: str, rel_path: str) -> str: # Now takes optimized_path as argument
        """Moves the *optimized* file to the optimized-bad directory."""
        dest_path = os.path.join(self.config.OPTIMIZED_BAD_ROOT, rel_path)
        self._move_file(optimized_path, dest_path) # Moving optimized file
        return dest_path

    def move_to_optimized_original(self, original_path: str, rel_path: str) -> str: # Now takes original_path
        """Moves the *original* file to the optimized-original directory."""
        dest_path = os.path.join(self.config.OPTIMIZED_ORIGINAL_ROOT, rel_path)
        self._move_file(original_path, dest_path) # Moving original file
        return dest_path


    def compare_file_sizes(self, original_path: str, optimized_path: str) -> bool:
        """ ... (rest of compare_file_sizes method is the same) ... """
        original_size = os.path.getsize(original_path)
        optimized_size = os.path.getsize(optimized_path)
        return original_size < optimized_size

    def collect_video_files(self, processed_files: Set[str] = None) -> List[str]:
        """ ... (rest of collect_video_files method is the same) ... """
        video_files = []
        skip_dirs = {
            self.config.OUTPUT_ROOT,
            self.config.ERRORED_ROOT,
            self.config.IN_PROGRESS_ROOT,
            self.config.DONE_ROOT,
            self.config.OPTIMIZED_BAD_ROOT,
            self.config.OPTIMIZED_ORIGINAL_ROOT,
        }

        for current_root, dirs, files in os.walk(self.config.SOURCE_ROOT):
            dirs[:] = [d for d in dirs if d not in skip_dirs]  # Modify dirs in-place to prune traversal
            for file in files:
                full_path = os.path.join(current_root, file)
                if Utils.is_video_file(full_path, self.config) and (processed_files is None or full_path not in processed_files):
                    video_files.append(full_path)

        video_files.sort()
        if self.config.REVERSE_ORDER:  # Use config's REVERSE_ORDER directly
            video_files.reverse()
        return video_files

    def get_relative_path(self, input_path: str) -> str:
        """ ... (rest of get_relative_path method is the same) ... """
        try:
            rel_path = os.path.relpath(input_path, self.config.SOURCE_ROOT)
            return rel_path
        except ValueError as e:
            logging.error(f"Error computing relative path for {input_path}: {e}")
            raise

    def check_skip_directory(self, input_path: str, rel_path: str) -> str or None:
        """ ... (rest of check_skip_directory method is the same) ... """
        skip_dirs = [self.config.OUTPUT_ROOT, self.config.ERRORED_ROOT, self.config.IN_PROGRESS_ROOT, self.config.DONE_ROOT, self.config.OPTIMIZED_BAD_ROOT, self.config.OPTIMIZED_ORIGINAL_ROOT]
        for skip_dir in skip_dirs:
            if rel_path.startswith(skip_dir + os.sep):
                return f"already in '{skip_dir}' directory" # Return skip reason
        return None # No skip reason