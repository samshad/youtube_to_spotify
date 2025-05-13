# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Utility functions for the YouTube to Spotify Migrator.
# Includes logging setup, file operations, and string cleaning.
# -----------------------------------------------------------------------------

import logging
import re
from typing import Tuple, Optional
from youtube_title_parse import get_artist_title

# Assuming config.py is in the same directory or accessible via PYTHONPATH
import config
import sys


def setup_logging() -> None:
    """
    Configures basic logging for the application.
    Logs to both console and a file specified in config.APP_ERROR_LOG_FILE.
    """
    # Ensure a data directory exists for the log file
    ensure_data_directory_exists()

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # File Handler (always UTF-8)
    file_handler = logging.FileHandler(config.APP_ERROR_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)  # Or your desired level for file
    file_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)

    # Console Stream Handler
    # Attempt to use UTF-8 and replace characters that cannot be displayed
    # to prevent the UnicodeEncodeError on the console.
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)

    # For the Windows console, set encoding to UTF-8
    if hasattr(console_handler.stream, "reconfigure"):
        console_handler.stream.reconfigure(encoding="utf-8")

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Suppress overly verbose logs from underlying libraries
    logging.getLogger("googleapiclient.discovery_cache").setLevel(logging.ERROR)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("spotipy").setLevel(logging.INFO)


def ensure_data_directory_exists() -> None:
    """
    Ensures that the data directory specified in the config exists.
    Creates it if it does not.
    """
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        # Get a logger instance for this module
        logger = logging.getLogger(
            __name__
        )  # Or just use print if logger is not yet set up
        logger.error(
            f"Could not create data directory: {config.DATA_DIR}. Error: {e}",
            exc_info=True,
        )
        raise


def clean_youtube_title(title: str) -> str:
    """
    Cleans a YouTube video title by removing common patterns like
    (Official Music Video), [Lyrics], HD, etc.

    Args:
        title: The raw YouTube video title.

    Returns:
        A cleaned version of the title.
    """
    if not title:
        return ""

    # Patterns to remove (case-insensitive)
    # Order matters: remove more specific patterns (like those with content) first.
    patterns_to_remove = [
        r"\(.*\bsoundtrack\b.*\)",  # (Official Soundtrack)
        r"\[.*\bsoundtrack\b.*\]",  # [Official Soundtrack]
        r"\(.*\bofficial music video\b.*\)",  # (anything Official Music Video anything)
        r"\[.*\bofficial music video\b.*\]",  # [anything Official Music Video anything]
        r"\(.*\bofficial video\b.*\)",  # (anything Official Video anything)
        r"\[.*\bofficial video\b.*\]",  # [anything Official Video anything]
        r"\(.*\bofficial lyric video\b.*\)",  # (anything Official Lyric Video anything)
        r"\[.*\bofficial lyric video\b.*\]",  # [anything Official Lyric Video anything]
        r"\(.*\blyric video\b.*\)",  # (anything Lyric Video anything)
        r"\[.*\blyric video\b.*\]",  # [anything Lyric Video anything]
        r"\(.*\blyrics\b.*\)",  # (anything Lyrics anything)
        r"\[.*\blyrics\b.*\]",  # [anything Lyrics anything]
        r"\(.*\bofficial audio\b.*\)",  # (anything Official Audio anything)
        r"\[.*\bofficial audio\b.*\]",  # [anything Official Audio anything]
        r"\(.*\baudio\b.*\)",  # (anything Audio anything)
        r"\[.*\baudio\b.*\]",  # [anything Audio anything]
        r"\(.*\bvisualizer\b.*\)",  # (anything Visualizer anything)
        r"\[.*\bvisualizer\b.*\]",  # [anything Visualizer anything]
        r"\(.*\bfull album\b.*\)",  # (Full Album)
        r"\[.*\bfull album\b.*\]",  # [Full Album]
        r"\(.*\blive\b.*\)",  # (Live at...)
        r"\[.*\blive\b.*\]",  # [Live at...]
        r"\(\s*HD\s*\)",
        r"\[\s*HD\s*\]",
        r"\(\s*HQ\s*\)",
        r"\[\s*HQ\s*\]",
        r"\(\s*4K\s*\)",
        r"\[\s*4K\s*\]",
        r"\(feat\.[^)]+\)",
        r"\[feat\.[^)]+\]",  # (feat. Artist)
        r"\(ft\.[^)]+\)",
        r"\[ft\.[^)]+\]",  # (ft. Artist)
        r"\(prod\.[^)]+\)",
        r"\[prod\.[^)]+\]",  # (prod. Producer)
        r"\s*#\w+",  # Remove hashtags
    ]

    cleaned_title = title
    for pattern in patterns_to_remove:
        cleaned_title = re.sub(pattern, "", cleaned_title, flags=re.IGNORECASE)

    # Remove content within parentheses/brackets if they are now empty or just contain whitespace
    cleaned_title = re.sub(r"\(\s*\)", "", cleaned_title)
    cleaned_title = re.sub(r"\[\s*\]", "", cleaned_title)

    # Remove leading/trailing special characters that might be left over, like '-' or '|'
    cleaned_title = cleaned_title.strip(" \t\n\r-_|")
    return cleaned_title.strip()


def parse_artist_song_from_title(
    cleaned_title: str, channel_title: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Attempts to parse artist and song name from a cleaned YouTube title.

    This is a heuristic-based approach and might need refinement.

    Args:
        cleaned_title: The YouTube title, already processed by clean_youtube_title().
        channel_title: The YouTube channel title, used as a fallback for artist.

    Returns:
        A tuple (artist, song_name). Either can be None if parsing fails.
    """
    artist: Optional[str] = None
    song: Optional[str] = None

    if not cleaned_title:
        return None, None

    result = get_artist_title(cleaned_title)

    if result:
        potential_artist = result[0]
        potential_song = result[1]

        # Basic sanity check: avoid overly short artist/song names if possible
        # and if the channel title seems more like the artist
        if len(potential_artist) > 1 and len(potential_song) > 1:
            artist = potential_artist
            song = potential_song
        else:  # One part is too short, or parsing is ambiguous
            song = cleaned_title  # Fallback: assume whole title is the song
            if channel_title:  # And use channel as artist
                # Clean channel title from common suffixes like "VEVO", "Music", "Official"
                cleaned_channel = re.sub(
                    r"\s*(VEVO|Music|Official|Records|Label)$",
                    "",
                    channel_title,
                    flags=re.IGNORECASE,
                ).strip()
                artist = cleaned_channel if cleaned_channel else channel_title

    else:  # No result from get_artist_title
        song = cleaned_title  # Assume the whole title is the song name
        if channel_title:
            cleaned_channel = re.sub(
                r"\s*(VEVO|Music|Official|Records|Label)$",
                "",
                channel_title,
                flags=re.IGNORECASE,
            ).strip()
            artist = cleaned_channel if cleaned_channel else channel_title

    # Final cleanup for artist and song names
    if artist:
        artist = artist.strip(
            " \t\n\r-_|[]()"
        )  # Remove leading/trailing special characters
    if song:
        song = song.strip(
            " \t\n\r-_|[]()"
        )  # Remove leading/trailing special characters

    # If artist is still None and channel_title exists, use channel_title
    if not artist and channel_title:
        cleaned_channel = re.sub(
            r"\s*(VEVO|Music|Official|Records|Label)$",
            "",
            channel_title,
            flags=re.IGNORECASE,
        ).strip()
        artist = cleaned_channel if cleaned_channel else channel_title

    return artist, song


if __name__ == "__main__":
    # Test logging setup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Utils.py: Logging test message.")
    logger.warning("Utils.py: This is a warning.")
    logger.error("Utils.py: This is an error.", exc_info=True)

    # Test title cleaning and parsing
    test_titles = [
        (
            "Complex Artist - Feat. Other - Song Name (prod. by Producer) (Visualizer)",
            "Complex Artist",
        ),
        ("[Special Clip] IU(아이유)_Dear Name(이름에게)", "1theK (원더케이)"),
        (
            "Main Rahoon Ya Na Rahoon Full', 'Emraan Hashmi, Esha Gupta | Amaal Mallik, Armaan Malik",
            "T-Series",
        ),
        ("Jashn-E-Bahara - Jodhaa Akbar | Anumita Nadesan", "Anumita Nadesan"),
        ("[IU] 'Love poem' Live Clip", "이지금 [IU Official]"),
        ("[MV] IU(아이유) _ eight(에잇) (Prod.&Feat. SUGA of BTS)", "1theK (원더케이)"),
    ]

    for title, channel in test_titles:
        print(f"\nOriginal: '{title}' (Channel: '{channel}')")
        cleaned = clean_youtube_title(title)
        print(f"Cleaned:  '{cleaned}'")
        parsed_artist, parsed_song = parse_artist_song_from_title(cleaned, channel)
        print(f"Parsed:   Artist='{parsed_artist}', Song='{parsed_song}'")
