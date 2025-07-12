import os
import subprocess
import logging
import re  # For regular expressions to parse FFmpeg output
from tqdm_loggable.auto import tqdm

from video_optimizer.config import Configuration
from video_optimizer.file_manager import FileManager
from video_optimizer.utils import Utils


class VideoProcessor:
    """
    Processes video files using FFmpeg, handles errors, and manages file movement.
    Now with tqdm integration for FFmpeg progress, using ffprobe for total frames.
    """

    def __init__(self, config: Configuration, file_manager: FileManager):
        """ ... (rest of __init__ method is the same) ... """
        self.config = config
        self.file_manager = file_manager

    def _build_ffmpeg_command(self, input_path: str, output_path: str) -> list:
        """Build FFmpeg command with conditional 1080p downscaling."""
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "warning",
            "-stats",  # Keep -stats for progress output
            "-y",  # Overwrite output file if it exists
            "-i", input_path,
            "-c:v", self.config.FFMPEG_VIDEO_CODEC,
            "-preset", self.config.FFMPEG_PRESET,
            "-crf", self.config.FFMPEG_CRF,
        ]
        
        # Check if video needs downscaling to 1080p
        resolution = self._get_video_resolution(input_path)
        if resolution:
            width, height = resolution
            logging.info(f"Video resolution: {width}x{height} for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
            
            if height > 1080:
                logging.info(f"Downscaling from {height}p to 1080p for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
                command.extend(["-vf", "scale=-2:1080"])
            else:
                logging.info(f"Keeping original resolution ({height}p) for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
        else:
            logging.warning(f"Could not determine resolution for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}', proceeding without scaling")
        
        # Add audio and output settings
        command.extend([
            "-c:a", self.config.FFMPEG_AUDIO_CODEC,
            "-b:a", self.config.FFMPEG_AUDIO_BITRATE,
            "-movflags", self.config.FFMPEG_MOVFLAGS,
            output_path,
        ])
        
        return command

    def _handle_ffmpeg_error(self, input_path: str, temp_output_path: str, rel_path: str, retcode: int) -> None:
        """ ... (rest of _handle_ffmpeg_error method is the same) ... """
        logging.error(f"FFmpeg returned non-zero exit code: {retcode} for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        self.file_manager.move_to_errored(input_path, rel_path)  # Move ORIGINAL to errored

    def _handle_unexpected_error(self, input_path: str, temp_output_path: str, rel_path: str, exception: Exception) -> None:
        """ ... (rest of _handle_unexpected_error method is the same) ... """
        logging.exception(f"An unexpected error occurred while processing '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)
        self.file_manager.move_to_errored(input_path, rel_path)  # Move ORIGINAL to errored

    def _get_video_resolution(self, input_path: str) -> tuple[int, int] or None:
        """
        Uses ffprobe to get the width and height of a video file.

        Args:
            input_path (str): Path to the input video file.

        Returns:
            tuple[int, int] or None: (width, height) or None if ffprobe fails.
        """
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                input_path
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            dimensions = result.stdout.strip().split(',')
            if len(dimensions) == 2 and dimensions[0].isdigit() and dimensions[1].isdigit():
                width, height = int(dimensions[0]), int(dimensions[1])
                return (width, height)
            else:
                logging.warning(f"ffprobe output for dimensions was unexpected: '{result.stdout.strip()}' for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'")
                return None

        except subprocess.CalledProcessError as e:
            logging.error(f"ffprobe command failed for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}': {e}")
            return None
        except FileNotFoundError:
            logging.error("ffprobe not found. Make sure it's installed and in your PATH.")
            return None

    def _get_total_frames(self, input_path: str) -> int or None:
        """
        Uses ffprobe to get the total number of frames in a video file.

        Args:
            input_path (str): Path to the input video file.

        Returns:
            int or None: Total number of frames, or None if ffprobe fails or cannot determine frames.
        """
        try:
            command = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=nb_frames",
                "-of", "default=nokey=1:noprint_wrappers=1",
                input_path
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            frames_str = result.stdout.strip()
            if frames_str.isdigit():
                return int(frames_str)
            else:
                logging.warning(f"ffprobe output for frame count was not a digit: '{frames_str}' for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}'. Using dynamic progress.")
                return None # Indicate frames couldn't be reliably determined.

        except subprocess.CalledProcessError as e:
            logging.error(f"ffprobe command failed for '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}': {e}")
            return None
        except FileNotFoundError:
            logging.error("ffprobe not found. Make sure it's installed and in your PATH.")
            return None


    def process_video(self, input_path: str) -> str:
        """
        Processes a single video file: converts, handles errors, and moves files using FileManager.
        Now integrates FFmpeg progress with tqdm, using ffprobe for total frames for percentage.
        """
        try:
            rel_path = self.file_manager.get_relative_path(input_path)
        except ValueError as e:
            return f"Error computing relative path for '{input_path}': {e}"

        base, _ = os.path.splitext(rel_path)
        temp_output_path = self.file_manager.get_in_progress_path(base + '.mp4')  # Get path in in-progress
        final_output_path = self.file_manager.get_output_path(base + '.mp4')  # Get path in output
        os.makedirs(os.path.dirname(temp_output_path), exist_ok=True)  # Ensure in-progress dir exists for ffmpeg output
        os.makedirs(os.path.dirname(final_output_path), exist_ok=True)  # Ensure output dir exists for final optimized file

        command = self._build_ffmpeg_command(input_path, temp_output_path)
        shorter_input_path = Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)

        # Regex to parse frame= from ffmpeg output
        frame_regex = re.compile(r"frame=\s*(\d+)")

        total_frames = self._get_total_frames(input_path) # Get total frames using ffprobe

        logging.info(f"'{shorter_input_path} has {total_frames or 'unknown'} frames")  # Log total frames or unknown

        file_pbar = tqdm(
            total=total_frames,  # Set total frames from ffprobe, can be None
            desc=f"Processing: {Utils.shorten_filename(os.path.basename(input_path))}",  # File-specific description
            unit="frame",
            unit_scale=True,
            leave=False,  # Don't leave the inner pbar on completion
            dynamic_ncols=True # Better tqdm display in different terminals
        )

        try:
            logging.info(f"Processing '{shorter_input_path}' -> '{Utils.shorten_filepath(final_output_path, self.config.SOURCE_ROOT)}'")  # Log output path, not temp path
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            # Stream ffmpeg output and update tqdm
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    logging.debug(f"[{shorter_input_path}]: {line.strip()}")  # Log in debug level, as it's verbose progress info

                    frame_match = frame_regex.search(line)
                    if frame_match:
                        current_frame = int(frame_match.group(1))
                        file_pbar.update(current_frame - file_pbar.n)  # Update by the increment since last update

            retcode = process.poll()

            file_pbar.close()  # Close file-specific progress bar

            if retcode != 0:
                self._handle_ffmpeg_error(input_path, temp_output_path, rel_path, retcode)
                return f"Error processing '{input_path}' (ffmpeg returned {retcode}). Moved original to '{os.path.join(self.config.ERRORED_ROOT, rel_path)}'"  # Clarify 'original moved'

            # Conversion succeeded

            # Move the TEMP optimized file to the FINAL optimized output path
            os.rename(temp_output_path, final_output_path)  # Optimized file moved to final output

            if self.file_manager.compare_file_sizes(input_path, final_output_path):
                logging.warning(f"Original file '{Utils.shorten_filepath(input_path, self.config.SOURCE_ROOT)}' is smaller than optimized file '{Utils.shorten_filepath(final_output_path, self.config.SOURCE_ROOT)}'. Moving files.")
                bad_optimized_path = self.file_manager.move_to_optimized_bad(final_output_path, rel_path.replace(".mp4", ".mp4"))  # Move OPTIMIZED to bad
                original_to_optimized_original_path = self.file_manager.move_to_optimized_original(input_path, rel_path)  # Move ORIGINAL to optimized-original
                os.remove(final_output_path)  # Remove the larger optimized file in the output directory after moving to bad.
            else:
                done_path = self.file_manager.move_to_done(input_path, rel_path)  # Move ORIGINAL to done (if optimized is kept)

            return f"Processed '{input_path}' -> '{final_output_path}'"  # final_output_path is the final optimized location

        except Exception as e:
            file_pbar.close()  # Ensure file pbar is closed in case of exception
            self._handle_unexpected_error(input_path, temp_output_path, rel_path, e)
            return f"Exception processing '{input_path}': {e}. Moved original to '{os.path.join(self.config.ERRORED_ROOT, rel_path)}'"  # Clarify 'original moved'