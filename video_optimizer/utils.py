import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_optimizer.config import Configuration


class Utils:
    """Utility functions for file path manipulation and checks."""

    @staticmethod
    def is_video_file(filepath: str, config: "Configuration") -> bool:
        """Checks if a file has a video extension from the configured list."""
        return Path(filepath).suffix.lower() in config.VIDEO_EXTENSIONS

    @staticmethod
    def shorten_filepath(filepath: str, source_root: str, shorten: bool = True) -> str:
        """
        Generates a shorter name for the file path, relative to the source root.

        Args:
            filepath: The full file path to shorten.
            source_root: The root directory to make the path relative to.
            shorten: Whether to apply shortening. Defaults to True.

        Example:
            "./to-convert/abra/cadabra/foobarwithalongname.mp4" -> "a/cadabra/foob...name.mp4"
        """
        if not shorten:
            return filepath

        filepath = filepath.replace(source_root, "").lstrip(os.sep)
        path_obj = Path(filepath)
        parts = [part for part in path_obj.parts if part != '.']

        if not parts:
            return filepath
        if len(parts) == 1:
            return Utils.shorten_filename(parts[0])

        directories, filename = parts[:-1], parts[-1]
        short_dirs = [d[0] if d else d for d in directories[:-1]]
        short_dirs.append(directories[-1])

        return "/".join(short_dirs + [Utils.shorten_filename(filename)])

    @staticmethod
    def shorten_filename(filename: str) -> str:
        """Shortens a filename if it's longer than 12 characters."""
        if len(filename) > 12:
            return f"{filename[:4]}...{filename[-4:]}"
        return filename
