#!/usr/bin/env python3
import signal
import time
import logging
from tqdm_loggable.auto import tqdm

from video_optimizer.config import Configuration
from video_optimizer.utils import Utils
from video_optimizer.file_manager import FileManager
from video_optimizer.video_processor import VideoProcessor
from video_optimizer.file_watcher import FileWatcher

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


def run_with_watcher(config, file_manager, video_processor, pbar, shutdown_event):
    """Run using file system watcher (inotify/FSEvents)."""
    processed_files = set()
    total_success = total_error = total_skipped = total_size_issue = 0

    watcher = FileWatcher(config, processed_files)

    # Initial scan for existing files
    existing_files = file_manager.collect_video_files(processed_files=processed_files)
    if existing_files:
        logging.info(f"Found {len(existing_files)} existing video files to process.")
        pbar.total = len(existing_files)
        pbar.refresh()

        for input_path in existing_files:
            if shutdown_event.is_set():
                break

            success, error, skipped, size_issue = process_file(
                input_path, file_manager, video_processor, config
            )
            processed_files.add(input_path)
            total_success += success
            total_error += error
            total_skipped += skipped
            total_size_issue += size_issue

            pbar.set_postfix(
                success=total_success, error=total_error,
                skipped=total_skipped, size_issue=total_size_issue
            )
            pbar.update(1)

    # Start watching for new files
    if not watcher.start():
        logging.error("File watcher failed to start, falling back to polling mode")
        return run_with_polling(config, file_manager, video_processor, pbar, shutdown_event)

    try:
        while not shutdown_event.is_set():
            # Wait for new files with timeout to check shutdown
            input_path = watcher.get_file(timeout=1.0)

            if input_path is None:
                continue

            if input_path in processed_files:
                continue

            pbar.total += 1
            pbar.refresh()

            success, error, skipped, size_issue = process_file(
                input_path, file_manager, video_processor, config
            )
            processed_files.add(input_path)
            total_success += success
            total_error += error
            total_skipped += skipped
            total_size_issue += size_issue

            pbar.set_postfix(
                success=total_success, error=total_error,
                skipped=total_skipped, size_issue=total_size_issue
            )
            pbar.update(1)
    finally:
        watcher.stop()

    return total_success, total_error, total_skipped, total_size_issue


def run_with_polling(config, file_manager, video_processor, pbar, shutdown_event):
    """Run using polling mode (original behavior)."""
    processed_files = set()
    total_success = total_error = total_skipped = total_size_issue = 0

    while not shutdown_event.is_set():
        video_files = file_manager.collect_video_files(processed_files=processed_files)

        if not video_files:
            logging.info(
                f"No new video files found. Sleeping for {config.CHECK_INTERVAL} seconds...")

            # Check shutdown more frequently than the full interval
            for _ in range(config.CHECK_INTERVAL):
                if shutdown_event.is_set():
                    break
                time.sleep(1)
            continue

        logging.info(f"Found {len(video_files)} new video files to process.")
        pbar.total += len(video_files)
        pbar.refresh()

        for input_path in video_files:
            if shutdown_event.is_set():
                break

            success, error, skipped, size_issue = process_file(
                input_path, file_manager, video_processor, config
            )
            processed_files.add(input_path)
            total_success += success
            total_error += error
            total_skipped += skipped
            total_size_issue += size_issue

            pbar.set_postfix(
                success=total_success, error=total_error,
                skipped=total_skipped, size_issue=total_size_issue
            )
            pbar.update(1)

    return total_success, total_error, total_skipped, total_size_issue


def main():
    """Main function to orchestrate video optimization."""
    logging.info("Starting video optimization process.")

    config = Configuration()
    file_manager = FileManager(config)
    video_processor = VideoProcessor(config, file_manager)

    logging.info(f"Using ffmpeg preset: {config.FFMPEG_PRESET}")
    logging.info(f"Processing files in {'reverse' if config.REVERSE_ORDER else 'normal'} order.")

    # Setup graceful shutdown
    shutdown_event = __import__('threading').Event()

    def signal_handler(_signum, _frame):
        logging.info("Received shutdown signal, finishing current file...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    pbar = tqdm(desc="Optimizing Videos", initial=0, total=0)

    try:
        if config.USE_POLLING:
            logging.info("Using polling mode (USE_POLLING=true)")
            totals = run_with_polling(config, file_manager, video_processor, pbar, shutdown_event)
        else:
            logging.info("Using file system watcher mode")
            totals = run_with_watcher(config, file_manager, video_processor, pbar, shutdown_event)

        total_success, total_error, total_skipped, total_size_issue = totals

    finally:
        pbar.close()

    logging.info("Video optimization process completed.")
    logging.info(
        f"Total - Success: {total_success}, Errors: {total_error}, "
        f"Skipped: {total_skipped}, Size Issues: {total_size_issue}")


if __name__ == "__main__":
    main()
