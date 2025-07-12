#!/usr/bin/env python3
import time
import logging
from tqdm_loggable.auto import tqdm

# Assuming your classes are in a package/directory named 'video_optimizer'
from video_optimizer.config import Configuration
from video_optimizer.utils import Utils
from video_optimizer.file_manager import FileManager
from video_optimizer.video_processor import VideoProcessor

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """Main function to orchestrate video optimization using modular classes."""
    logging.info("Starting video optimization process.")

    config = Configuration()
    file_manager = FileManager(config)
    video_processor = VideoProcessor(config, file_manager)

    logging.info(f"Using ffmpeg preset: {config.FFMPEG_PRESET}")

    if config.REVERSE_ORDER:
        logging.info(
            "Processing files in reverse order as VIDEO_OPTIMIZER_REVERSE_ORDER is set to true.")
    else:
        logging.info("Processing files in normal order.")

    processed_files = set()

    success_count = 0
    error_count = 0
    skipped_count = 0
    size_issue_count = 0

    pbar = tqdm(desc="Optimizing Videos", initial=0, total=0)
    try:
        while True:  # Keep looping to check for new files
            video_files = file_manager.collect_video_files(
                processed_files=processed_files)

            if not video_files:
                logging.info(
                    f"No new video files found. Sleeping for {config.CHECK_INTERVAL} seconds...")
                time.sleep(config.CHECK_INTERVAL)  # Wait before checking again
                continue

            logging.info(
                f"Found {len(video_files)} new video files to process.")
            pbar.total += len(video_files)
            pbar.refresh()

            for input_path in video_files:
                try:
                    rel_path = file_manager.get_relative_path(
                        input_path)  # Get relative path using FileManager
                except ValueError:  # if relative path fails, skip the file. Logged in FileManager already.
                    error_count += 1
                    pbar.set_postfix(success=success_count, error=error_count,
                                     skipped=skipped_count, size_issue=size_issue_count)
                    pbar.update(1)
                    continue

                # Check if file is in skip directories - logic moved to VideoProcessor
                skip_reason = file_manager.check_skip_directory(
                    input_path, rel_path)
                if skip_reason:
                    skipped_count += 1
                    # Use config.SOURCE_ROOT for Utils
                    logging.info(
                        f"Skipped: '{Utils.shorten_filepath(input_path, config.SOURCE_ROOT)}' ({skip_reason})")
                    # Mark as processed even if skipped
                    processed_files.add(input_path)
                    pbar.set_postfix(success=success_count, error=error_count,
                                     skipped=skipped_count, size_issue=size_issue_count)
                    pbar.update(1)
                    continue

                result = video_processor.process_video(input_path)
                processed_files.add(input_path)  # Mark file as processed

                if result.startswith("Processed"):
                    if "Original file is smaller" in result:  # Adjust to match the logging message from VideoProcessor
                        size_issue_count += 1
                        logging.warning(result)
                    else:
                        success_count += 1
                        logging.info(result)
                elif result.startswith("Error") or result.startswith("Exception"):
                    error_count += 1
                    logging.error(result)

                pbar.set_postfix(success=success_count, error=error_count,
                                 skipped=skipped_count, size_issue=size_issue_count)
                pbar.update(1)  # Increment the progress bar

            if not video_files:  # prevents endless loop if interrupted when no files are found initially
                break
    finally:
        pbar.close()

    logging.info("Video optimization process completed.")
    logging.info(
        f"Success: {success_count}, Errors: {error_count}, Skipped: {skipped_count}, Size Issues: {size_issue_count}")


if __name__ == "__main__":
    main()
