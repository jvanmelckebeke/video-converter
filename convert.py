#!/usr/bin/env python3
import os
import subprocess
import shutil
import time
from pathlib import Path
from tqdm_loggable.auto import tqdm
import logging

# Configuration Constants
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.mpeg', '.mpg', '.m4v'}
SOURCE_ROOT = './to-convert'
OUTPUT_ROOT = 'optimized'
ERRORED_ROOT = 'errored'
IN_PROGRESS_ROOT = 'in-progress'
DONE_ROOT = 'done'
OPTIMIZED_BAD_ROOT = 'optimized-bad'
OPTIMIZED_ORIGINAL_ROOT = 'optimized-original'

FFMPEG_PRESET = os.environ.get('FFMPEG_PRESET', 'veryslow')  # Default to 'veryslow'
FFMPEG_CRF = "26"  # Constant Rate Factor
FFMPEG_AUDIO_BITRATE = "128k"
FFMPEG_VIDEO_CODEC = "libx265"
FFMPEG_AUDIO_CODEC = "aac"
FFMPEG_MOVFLAGS = "+faststart"  # optimize for streaming

CHECK_INTERVAL = 10  # seconds - how often to check for new files. Adjust as needed

# Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def is_video_file(filepath: str) -> bool:
    """Checks if a file has a video extension."""
    return Path(filepath).suffix.lower() in VIDEO_EXTENSIONS


def shorten_filepath(filepath: str) -> str:
    """
    Generates a shorter name for the file path.

    Example:
        "./abra/cadabra/foobarwithalongname.mp4" -> "a/cadabra/foobarwithalongname.mp4" -> "a/cadabra/foob...name.mp4"
    """
    filepath = filepath.replace(SOURCE_ROOT, "").lstrip(os.sep)
    path_obj = Path(filepath)
    parts = [part for part in path_obj.parts if part != '.']

    if not parts:
        return filepath
    if len(parts) == 1:
        return shorten_filename(parts[0])

    directories, filename = parts[:-1], parts[-1]
    short_dirs = [d[0] if d else d for d in directories[:-1]]
    short_dirs.append(directories[-1])

    return "/".join(short_dirs + [shorten_filename(filename)])


def shorten_filename(filename: str) -> str:
    """Shortens a filename if it's longer than 12 characters."""
    if len(filename) > 12:
        return f"{filename[:4]}...{filename[-4:]}"
    return filename


def build_ffmpeg_command(input_path: str, output_path: str) -> list:
    """Constructs the ffmpeg command for video conversion."""
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "warning",
        "-stats",
        "-y",  # Overwrite output file if it exists
        "-i", input_path,
        "-c:v", FFMPEG_VIDEO_CODEC,
        "-preset", FFMPEG_PRESET,
        "-crf", FFMPEG_CRF,
        "-c:a", FFMPEG_AUDIO_CODEC,
        "-b:a", FFMPEG_AUDIO_BITRATE,
        "-movflags", FFMPEG_MOVFLAGS,
        output_path,
    ]
    return command


def move_file_with_structure(source_path: str, dest_root: str, rel_path: str):
    """Moves a file to a destination, preserving the directory structure."""
    dest_path = os.path.join(dest_root, rel_path)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    try:
        shutil.move(source_path, dest_path)
        logging.info(f"Moved {source_path} to {dest_path}")
    except Exception as e:
        logging.error(f"Failed to move {source_path} to {dest_path}: {e}")
        raise


def compare_file_sizes(original_path: str, optimized_path: str) -> bool:
    """Compares the file sizes of the original and optimized files. Returns True if the original is smaller."""
    original_size = os.path.getsize(original_path)
    optimized_size = os.path.getsize(optimized_path)
    return original_size < optimized_size


def process_video(input_path: str) -> str:
    """
    Processes a single video file: converts, handles errors, and moves files.
    """
    try:
        rel_path = os.path.relpath(input_path, SOURCE_ROOT)
    except ValueError as e:
        return f"Error computing relative path for {input_path}: {e}"

    for skip_dir in [OUTPUT_ROOT, ERRORED_ROOT, IN_PROGRESS_ROOT, DONE_ROOT, OPTIMIZED_BAD_ROOT, OPTIMIZED_ORIGINAL_ROOT]:
        if rel_path.startswith(skip_dir + os.sep):
            return f"Skipped: {input_path} (already in a target directory)"

    base, _ = os.path.splitext(rel_path)
    final_output_path = os.path.join(OUTPUT_ROOT, base + '.mp4')
    temp_output_path = os.path.join(IN_PROGRESS_ROOT, base + '.mp4')

    os.makedirs(os.path.dirname(temp_output_path), exist_ok=True)
    os.makedirs(os.path.dirname(final_output_path), exist_ok=True)

    command = build_ffmpeg_command(input_path, temp_output_path)
    shorter_input_path = shorten_filepath(input_path)

    try:
        logging.info(f"Processing {shorter_input_path} -> {temp_output_path}")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Stream ffmpeg output
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                logging.info(f"[{shorter_input_path}]: {line.strip()}")

        retcode = process.poll()

        if retcode != 0:
            handle_ffmpeg_error(input_path, temp_output_path, rel_path, retcode)
            return f"Error processing {input_path}: (ffmpeg returned {retcode}). Moved to {os.path.join(ERRORED_ROOT, rel_path)}"

        # Conversion succeeded

        # move the temp file to optimized location before the size check.
        os.rename(temp_output_path, final_output_path)

        if compare_file_sizes(input_path, final_output_path):
            logging.warning(f"Original file {input_path} is smaller than optimized file {final_output_path}. Moving files.")
            move_file_with_structure(final_output_path, OPTIMIZED_BAD_ROOT, rel_path.replace(".mp4", ".mp4"))  # Ensure .mp4 extension
            move_file_with_structure(input_path, OPTIMIZED_ORIGINAL_ROOT, rel_path)
        else:
            move_file_with_structure(input_path, DONE_ROOT, rel_path)  # Only move the original file if we keep the optimized file.

        return f"Processed {input_path} -> {final_output_path}"

    except Exception as e:
        handle_unexpected_error(input_path, temp_output_path, rel_path, e)
        return f"Exception processing {input_path}: {e}. Moved to {os.path.join(ERRORED_ROOT, rel_path)}"


def handle_ffmpeg_error(input_path, temp_output_path, rel_path, retcode):
    """Handles errors returned by ffmpeg during conversion."""
    logging.error(f"FFmpeg returned non-zero exit code: {retcode} for {input_path}")
    if os.path.exists(temp_output_path):
        os.remove(temp_output_path)
    move_to_errored(input_path, rel_path)


def handle_unexpected_error(input_path, temp_output_path, rel_path, exception):
    """Handles unexpected exceptions during conversion."""
    logging.exception(f"An unexpected error occurred while processing {input_path}")
    if os.path.exists(temp_output_path):
        os.remove(temp_output_path)
    move_to_errored(input_path, rel_path)


def move_to_errored(input_path, rel_path):
    """Moves a file to the errored directory."""
    errored_path = os.path.join(ERRORED_ROOT, rel_path)
    os.makedirs(os.path.dirname(errored_path), exist_ok=True)
    try:
        shutil.move(input_path, errored_path)
        logging.info(f"Moved {input_path} to {errored_path}")
    except Exception as move_err:
        logging.error(f"Failed to move {input_path} to {errored_path}: {move_err}")
        raise  # re-raise the exception if the move fails


def collect_video_files(root: str = SOURCE_ROOT, processed_files: set = None, reverse_order: bool = False) -> list:
    """Collects video files from a directory, skipping specific subdirectories and already processed files.
       Optionally reverses the order of files if reverse_order is True.
    """
    video_files = []
    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {OUTPUT_ROOT, ERRORED_ROOT, IN_PROGRESS_ROOT, DONE_ROOT, OPTIMIZED_BAD_ROOT, OPTIMIZED_ORIGINAL_ROOT}]
        for file in files:
            full_path = os.path.join(current_root, file)
            if is_video_file(full_path) and (processed_files is None or full_path not in processed_files):
                video_files.append(full_path)
    video_files.sort()
    if reverse_order:
        video_files.reverse()
    return video_files


def main():
    """Main function to orchestrate video processing."""
    logging.info("Starting video optimization process.")
    logging.info(f"Using ffmpeg preset: {FFMPEG_PRESET}")

    reverse_order_env = os.environ.get('REVERSE_ORDER', 'false').lower()
    reverse_order = reverse_order_env in ['true', '1', 'yes']
    if reverse_order:
        logging.info("Processing files in reverse order as REVERSE_ORDER is set.")
    else:
        logging.info("Processing files in normal order.")

    processed_files = set()  # Keep track of files that have been processed

    success_count = 0
    error_count = 0
    skipped_count = 0
    size_issue_count = 0  # New counter

    pbar = tqdm(desc="Optimizing Videos", initial=0, total=0)  # Initialize tqdm with total=0
    try:
        while True:  # Keep looping to check for new files
            video_files = collect_video_files(processed_files=processed_files, reverse_order=reverse_order)

            if not video_files:
                logging.info(f"No new video files found. Sleeping for {CHECK_INTERVAL} seconds...")
                time.sleep(CHECK_INTERVAL)  # Wait before checking again
                continue

            logging.info(f"Found {len(video_files)} new video files to process.")
            pbar.total += len(video_files)  # Update total for progress bar
            pbar.refresh() # Force refresh, so the total is updated before anything happens.

            for input_path in video_files:
                result = process_video(input_path)
                processed_files.add(input_path)  # Mark file as processed

                if result.startswith("Processed"):
                    if "Original file is smaller" in result:  # Adjust to match the logging message
                        size_issue_count += 1
                        logging.warning(result)
                    else:
                        success_count += 1
                        logging.info(result)
                elif result.startswith("Error") or result.startswith("Exception"):
                    error_count += 1
                    logging.error(result)
                elif result.startswith("Skipped"):
                    skipped_count += 1
                    logging.info(result)

                pbar.set_postfix(success=success_count, error=error_count, skipped=skipped_count, size_issue=size_issue_count)
                pbar.update(1)  # Increment the progress bar

            if not video_files: # prevents endless loop if interrupted
               break
    finally:
        pbar.close()

    logging.info("Video optimization process completed.")
    logging.info(f"Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}, Size Issues: {size_issue_count}")


if __name__ == "__main__":
    main()
