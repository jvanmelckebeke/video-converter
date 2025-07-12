# Video Converter

A Python-based video optimization system that continuously monitors a source directory for video files, processes them using FFmpeg with H.265 encoding, and organizes the results into different directories based on processing outcomes.

## Features

- **Continuous Monitoring**: Automatically detects new video files in the source directory
- **H.265 Encoding**: Optimizes videos using FFmpeg with configurable quality settings
- **Progress Tracking**: Real-time progress bars for both overall processing and individual file encoding
- **Smart Organization**: Automatically sorts processed files into appropriate directories
- **Docker Support**: Ready-to-use Docker configuration for easy deployment
- **Configurable**: Environment variable-based configuration system

## Directory Structure

The system organizes files into these directories:

- `to-convert/`: Source directory for new video files
- `optimized/`: Successfully optimized videos
- `done/`: Original files that were successfully optimized
- `errored/`: Files that failed processing
- `in-progress/`: Temporary files during FFmpeg processing
- `optimized-bad/`: Optimized files that are larger than originals
- `optimized-original/`: Original files when optimization resulted in larger files

## Quick Start

### Docker (Recommended)

```bash
docker-compose up --build
```

### Local Development

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Run the application
python main.py
```

## Configuration

Configure the system using environment variables with the `OPTIMIZER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPTIMIZER_FFMPEG_PRESET` | `veryslow` | FFmpeg encoding preset |
| `OPTIMIZER_FFMPEG_CRF` | `26` | Constant rate factor for quality |
| `OPTIMIZER_SOURCE_ROOT` | `./to-convert` | Source directory to monitor |
| `OPTIMIZER_REVERSE_ORDER` | `false` | Process files in reverse order |
| `OPTIMIZER_SHORTEN_FILE_PATHS` | `true` | Enable path shortening in logs |
| `OPTIMIZER_CHECK_INTERVAL` | `10` | Seconds between directory scans |

## How It Works

1. **Monitor**: Continuously scans the source directory for new video files
2. **Process**: Converts videos using FFmpeg with H.265 encoding
3. **Compare**: Checks if the optimized file is smaller than the original
4. **Organize**: Moves files to appropriate directories based on processing results
5. **Repeat**: Continues monitoring for new files

## Requirements

- Python 3.9+
- FFmpeg
- Docker (optional, for containerized deployment)

## License

This project is open source and available under the MIT License.