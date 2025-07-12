# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based video optimization system that continuously monitors a source directory for video files, processes them using FFmpeg with H.265 encoding, and organizes the results into different directories based on processing outcomes.

## Architecture

The codebase has been refactored from a monolithic `convert.py` into a modular design:

- **main.py**: Entry point that orchestrates the optimization process with progress tracking
- **video_optimizer/**: Main package containing modular components
  - **config.py**: Pydantic-based configuration management with environment variable support
  - **video_processor.py**: FFmpeg processing logic with progress tracking via tqdm
  - **file_manager.py**: File operations, directory management, and file movement logic
  - **utils.py**: Utility functions for file path manipulation and video file detection

### Directory Structure

The system organizes files into these directories:
- `to-convert/`: Source directory (configurable via `OPTIMIZER_SOURCE_ROOT`)
- `optimized/`: Successfully optimized videos
- `done/`: Original files that were successfully optimized
- `errored/`: Files that failed processing
- `in-progress/`: Temporary files during FFmpeg processing
- `optimized-bad/`: Optimized files that are larger than originals
- `optimized-original/`: Original files when optimization resulted in larger files

## Commands

### Running the Application

**Local development:**
```bash
python main.py
```

**Docker (recommended):**
```bash
docker-compose up --build
```

### Testing Dependencies
```bash
python -m pip install -r requirements.txt
```

### Configuration

All settings are managed through environment variables with the `OPTIMIZER_` prefix:

- `OPTIMIZER_FFMPEG_PRESET`: FFmpeg encoding preset (default: veryslow)
- `OPTIMIZER_FFMPEG_CRF`: Constant rate factor for quality (default: 26)
- `OPTIMIZER_SOURCE_ROOT`: Source directory to monitor (default: ./to-convert)
- `OPTIMIZER_REVERSE_ORDER`: Process files in reverse order (default: false)
- `OPTIMIZER_SHORTEN_FILE_PATHS`: Enable path shortening in logs (default: true)
- `OPTIMIZER_CHECK_INTERVAL`: Seconds between directory scans (default: 10)

## Key Implementation Details

### Progress Tracking
The system uses nested tqdm progress bars:
- Outer bar: Overall file processing progress
- Inner bar: Per-file FFmpeg encoding progress with frame counts from ffprobe

### Error Handling
Three-tier error management:
1. FFmpeg errors move original files to `errored/`
2. Size comparison failures move optimized to `optimized-bad/` and original to `optimized-original/`
3. Unexpected exceptions are logged and files moved to `errored/`

### File Processing Logic
1. Scan source directory excluding processing directories
2. Get relative paths and check for skip conditions
3. Process with FFmpeg to temporary location (`in-progress/`)
4. Compare file sizes after processing
5. Move files to appropriate final directories based on results

### Docker Configuration
The Dockerfile uses Python 3.9-slim with FFmpeg installed. The docker-compose setup includes:
- Volume mounting for file access
- Resource limits for memory/CPU
- User permissions (1000:1000)
- Logging configuration with size limits

## Development Notes

- The legacy `convert.py` file remains for reference but should not be modified
- Configuration uses Pydantic with environment variable validation
- All file operations go through the FileManager class for consistency
- FFmpeg progress is parsed using regex on stdout for real-time updates
- The system continuously monitors for new files until manually stopped