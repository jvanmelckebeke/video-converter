# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Video optimization system that monitors a source directory, converts videos to H.265 using FFmpeg, and organizes results based on processing outcomes. Videos larger than 1080p are automatically downscaled.

## Commands

```bash
# Run locally (requires FFmpeg installed)
python main.py

# Run with Docker (recommended)
docker-compose up --build

# Install dependencies
pip install -r requirements.txt
```

## Architecture

```
main.py                      # Entry point, orchestrates processing with tqdm progress
video_optimizer/
├── config.py               # Pydantic settings with OPTIMIZER_ env prefix
├── video_processor.py      # FFmpeg subprocess handling, frame progress parsing
├── file_manager.py         # File operations, directory traversal, movement logic
├── file_watcher.py         # Watchdog-based filesystem event monitoring
└── utils.py                # Path shortening, video file detection
```

### Processing Flow

1. `FileManager.collect_video_files()` scans source, excludes processing dirs
2. `VideoProcessor.process_video()` runs FFmpeg to `in-progress/` temp location
3. On success: compare sizes → move to `optimized/` + `done/` or `optimized-bad/` + `optimized-original/`
4. On failure: move original to `errored/`

### Directory Layout (all configurable via env vars)

| Directory | Purpose |
|-----------|---------|
| `to-convert/` | Source directory to monitor |
| `in-progress/` | Temp FFmpeg output (deleted on failure) |
| `optimized/` | Successfully smaller conversions |
| `done/` | Originals of successful conversions |
| `errored/` | Failed conversions (originals) |
| `optimized-bad/` | Conversions that got larger |
| `optimized-original/` | Originals when conversion was larger |

## Configuration

All settings use `OPTIMIZER_` prefix. Key ones:

| Variable | Default | Notes |
|----------|---------|-------|
| `FFMPEG_PRESET` | veryslow | Speed/quality tradeoff |
| `FFMPEG_CRF` | 26 | Lower = better quality, larger files |
| `SOURCE_ROOT` | ./to-convert | Watch directory |
| `CHECK_INTERVAL` | 10 | Seconds between scans (polling mode) |
| `USE_POLLING` | false | Force polling mode instead of filesystem watcher |

Additional FFmpeg settings: `FFMPEG_AUDIO_BITRATE` (128k), `FFMPEG_VIDEO_CODEC` (libx265), `FFMPEG_AUDIO_CODEC` (aac), `FFMPEG_MOVFLAGS` (+faststart).

## Implementation Notes

- **File Watching**: Uses `watchdog` library for instant file detection via inotify/FSEvents; falls back to polling if unavailable
- **Graceful Shutdown**: Handles SIGINT/SIGTERM to finish current file before exiting
- **1080p Downscaling**: `VideoProcessor._get_video_resolution()` checks height; videos >1080p get `-vf scale=-2:1080`
- **Progress Tracking**: FFmpeg stdout parsed with regex `frame=\s*(\d+)` against total from `ffprobe -show_entries stream=nb_frames`
- **File Movement**: All operations through `FileManager._move_file()` which creates directories and logs
- **Skip Logic**: `FileManager.check_skip_directory()` prevents reprocessing files already in output directories