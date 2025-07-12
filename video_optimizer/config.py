from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuration(BaseSettings):
    """
    Manages configuration settings for the video optimization process, loaded from environment variables.

    Attributes: (Documented as before, but now sourced from env vars)
        VIDEO_EXTENSIONS (set): Set of video file extensions to process.
        SOURCE_ROOT (str): Root directory to search for video files.
        OUTPUT_ROOT (str): Root directory to store optimized videos.
        ERRORED_ROOT (str): Root directory to store videos that failed processing.
        IN_PROGRESS_ROOT (str): Root directory for temporary files during processing.
        DONE_ROOT (str): Root directory to store successfully processed videos.
        OPTIMIZED_BAD_ROOT (str): Root directory for optimized videos that are larger than originals.
        OPTIMIZED_ORIGINAL_ROOT (str): Root directory for original videos when optimized versions are worse.
        FFMPEG_PRESET (str): FFmpeg preset for video encoding.
        FFMPEG_CRF (str): FFmpeg Constant Rate Factor for video quality.
        FFMPEG_AUDIO_BITRATE (str): FFmpeg audio bitrate.
        FFMPEG_VIDEO_CODEC (str): FFmpeg video codec.
        FFMPEG_AUDIO_CODEC (str): FFmpeg audio codec.
        FFMPEG_MOVFLAGS (str): FFmpeg movflags for optimization (e.g., streaming).
        CHECK_INTERVAL (int): Time interval (seconds) to check for new files.
    """

    VIDEO_EXTENSIONS: set[str] = {
        '.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.mpeg', '.mpg', '.m4v'}
    SOURCE_ROOT: str = './to-convert'
    OUTPUT_ROOT: str = 'optimized'
    ERRORED_ROOT: str = 'errored'
    IN_PROGRESS_ROOT: str = 'in-progress'
    DONE_ROOT: str = 'done'
    OPTIMIZED_BAD_ROOT: str = 'optimized-bad'
    OPTIMIZED_ORIGINAL_ROOT: str = 'optimized-original'

    FFMPEG_PRESET: str = 'veryslow'  # Default to 'veryslow'
    FFMPEG_CRF: str = "26"  # Constant Rate Factor
    FFMPEG_AUDIO_BITRATE: str = "128k"
    FFMPEG_VIDEO_CODEC: str = "libx265"
    FFMPEG_AUDIO_CODEC: str = "aac"
    FFMPEG_MOVFLAGS: str = "+faststart"  # optimize for streaming

    CHECK_INTERVAL: int = 10  # seconds - how often to check for new files. Adjust as needed
    REVERSE_ORDER: bool = False  # New setting for reverse order processing

    # New setting to control path shortening in logs, default to True
    SHORTEN_FILE_PATHS: bool = True

    # Prefix for environment variables
    model_config = SettingsConfigDict(env_prefix='OPTIMIZER_')
