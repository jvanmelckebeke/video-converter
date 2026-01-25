#!/usr/bin/env python3
import time
import logging
from tqdm_loggable.auto import tqdm

from video_optimizer.config import Configuration
from video_optimizer.utils import Utils
from video_optimizer.file_manager import FileManager
from video_optimizer.video_processor import VideoProcessor

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def process_file(input_path, file_manager, video_processor, config):
    """Process a single file and return result counts."""
    success = error = skipped = size_issue = 0

    try:
        rel_path = file_manager.get_relative_path(input_path)
    except ValueError:
        return 0, 1, 0, 0  # error

    skip_reason = file_manager.check_skip_directory(input_path, rel_path)
    if skip_reason:
        logging.info(
            f"Skipped: '{Utils.shorten_filepath(input_path, config.SOURCE_ROOT)}' ({skip_reason})")
        return 0, 0, 1, 0  # skipped

    result = video_processor.process_video(input_path)

    if result.startswith("Processed"):
        if "Original file is smaller" in result:
            logging.warning(result)
            return 0, 0, 0, 1  # size_issue
        else:
            logging.info(result)
            return 1, 0, 0, 0  # success
    elif result.startswith("Error") or result.startswith("Exception"):
        logging.error(result)
        return 0, 1, 0, 0  # error

    return 0, 0, 0, 0


def main():
    """Main function to orchestrate video optimization."""
    logging.info("Starting video optimization process.")

    config = Configuration()
    file_manager = FileManager(config)
    video_processor = VideoProcessor(config, file_manager)

    logging.info(f"Using ffmpeg preset: {config.FFMPEG_PRESET}")
    logging.info(f"Processing files in {'reverse' if config.REVERSE_ORDER else 'normal'} order.")

    processed_files = set()
    total_success = total_error = total_skipped = total_size_issue = 0

    pbar = tqdm(desc="Optimizing Videos", initial=0, total=0)

    try:
        while True:
            video_files = file_manager.collect_video_files(processed_files=processed_files)

            if not video_files:
                logging.info(
                    f"No new video files found. Sleeping for {config.CHECK_INTERVAL} seconds...")
                time.sleep(config.CHECK_INTERVAL)
                continue

            logging.info(f"Found {len(video_files)} new video files to process.")
            pbar.total += len(video_files)
            pbar.refresh()

            for input_path in video_files:
                success, error, skipped, size_issue = process_file(
                    input_path, file_manager, video_processor, config
                )

                processed_files.add(input_path)
                total_success += success
                total_error += error
                total_skipped += skipped
                total_size_issue += size_issue

                pbar.set_postfix(
                    success=total_success,
                    error=total_error,
                    skipped=total_skipped,
                    size_issue=total_size_issue
                )
                pbar.update(1)

    finally:
        pbar.close()

    logging.info("Video optimization process completed.")
    logging.info(
        f"Total - Success: {total_success}, Errors: {total_error}, "
        f"Skipped: {total_skipped}, Size Issues: {total_size_issue}")


if __name__ == "__main__":
    main()
