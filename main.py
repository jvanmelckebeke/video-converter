#!/usr/bin/env python3
import time
import logging
from collections import deque
from tqdm_loggable.auto import tqdm

# Assuming your classes are in a package/directory named 'video_optimizer'
from video_optimizer.config import Configuration
from video_optimizer.utils import Utils
from video_optimizer.file_manager import FileManager
from video_optimizer.video_processor import VideoProcessor

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


def discover_new_files(file_manager, processed_files):
    """Discover new video files that haven't been processed yet."""
    return file_manager.collect_video_files(processed_files=processed_files)


def process_file_from_queue(input_path, file_manager, video_processor, processed_files, config):
    """Process a single file from the queue and return updated counters."""
    success_count = error_count = skipped_count = size_issue_count = 0
    
    try:
        rel_path = file_manager.get_relative_path(input_path)
    except ValueError:
        error_count += 1
        processed_files.add(input_path)
        return success_count, error_count, skipped_count, size_issue_count

    # Check if file is in skip directories
    skip_reason = file_manager.check_skip_directory(input_path, rel_path)
    if skip_reason:
        skipped_count += 1
        logging.info(
            f"Skipped: '{Utils.shorten_filepath(input_path, config.SOURCE_ROOT)}' ({skip_reason})")
        processed_files.add(input_path)
        return success_count, error_count, skipped_count, size_issue_count

    # Process the video file
    result = video_processor.process_video(input_path)
    processed_files.add(input_path)

    if result.startswith("Processed"):
        if "Original file is smaller" in result:
            size_issue_count += 1
            logging.warning(result)
        else:
            success_count += 1
            logging.info(result)
    elif result.startswith("Error") or result.startswith("Exception"):
        error_count += 1
        logging.error(result)

    return success_count, error_count, skipped_count, size_issue_count


def main():
    """Main function to orchestrate video optimization using queue-based processing."""
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
    file_queue = deque()
    queued_files = set()  # Track files currently in queue

    # Global counters
    total_success = 0
    total_error = 0
    total_skipped = 0
    total_size_issue = 0

    pbar = tqdm(desc="Optimizing Videos", initial=0, total=0)
    
    try:
        while True:
            # If queue is empty, discover new files and start a new batch
            if not file_queue:
                new_files = discover_new_files(file_manager, processed_files)
                
                if not new_files:
                    logging.info(
                        f"No new video files found. Sleeping for {config.CHECK_INTERVAL} seconds...")
                    time.sleep(config.CHECK_INTERVAL)
                    continue
                
                # Start new batch: reset progress bar and populate queue
                logging.info(f"Found {len(new_files)} new video files to process.")
                file_queue.extend(new_files)
                queued_files.update(new_files)  # Track queued files
                pbar.n = 0  # Reset position only
                pbar.total = len(file_queue)
                pbar.refresh()
            
            # Process files from queue
            while file_queue:
                current_file = file_queue.popleft()
                queued_files.discard(current_file)  # Remove from queued tracking
                
                # Process current file
                success, error, skipped, size_issue = process_file_from_queue(
                    current_file, file_manager, video_processor, processed_files, config
                )
                
                # Update global counters
                total_success += success
                total_error += error
                total_skipped += skipped
                total_size_issue += size_issue
                
                # Update progress bar
                pbar.set_postfix(
                    success=total_success, 
                    error=total_error,
                    skipped=total_skipped, 
                    size_issue=total_size_issue
                )
                pbar.update(1)
                
                # Check for new files after processing each file
                all_discovered = discover_new_files(file_manager, processed_files)
                # Filter out files already in queue or processed
                new_files = [f for f in all_discovered if f not in queued_files and f not in processed_files]
                if new_files:
                    logging.info(f"Found {len(new_files)} additional files during processing.")
                    file_queue.extend(new_files)
                    queued_files.update(new_files)  # Track new queued files
                    pbar.total += len(new_files)
                    pbar.refresh()
                    
    finally:
        pbar.close()

    logging.info("Video optimization process completed.")
    logging.info(
        f"Total - Success: {total_success}, Errors: {total_error}, Skipped: {total_skipped}, Size Issues: {total_size_issue}")


if __name__ == "__main__":
    main()
