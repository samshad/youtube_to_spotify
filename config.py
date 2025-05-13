# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: This script loads configuration settings for the YouTube to Spotify from an .env file.
# -----------------------------------------------------------------------------

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# Assumes .env file is in the project root, which is the parent of this config.py file's directory
# Or, if running scripts from the project root, Path() / ".env" works directly.
ENV_PATH = Path(__file__).resolve().parent / ".env"
if not ENV_PATH.exists():
    # Fallback for cases where the script is run from the project root.
    ENV_PATH = Path(".") / ".env"
load_dotenv(dotenv_path=ENV_PATH)

YOUTUBE_API_KEY: str | None = os.getenv("YOUTUBE_API_KEY")
SPOTIPY_CLIENT_ID: str | None = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET: str | None = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI: str | None = os.getenv("SPOTIPY_REDIRECT_URI")

PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
FETCHED_SONGS_FILE = DATA_DIR / "youtube_songs_fetched.csv"
SUCCESS_LOG_FILE = DATA_DIR / "successfully_migrated.csv"
NOT_FOUND_LOG_FILE = DATA_DIR / "not_found_on_spotify.csv"
APP_ERROR_LOG_FILE = DATA_DIR / "app_errors.log"

# Matching Configuration
FUZZY_MATCH_THRESHOLD: int = 85  # Score out of 100 for fuzzywuzzy match

# Spotify Configuration
SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST: int = 100  # Spotify API limit

# YouTube Configuration
YOUTUBE_MAX_RESULTS_PER_PAGE: int = 50  # YouTube API limit for playlist items


def validate_configuration() -> bool:
    """
    Validates that essential configuration variables are set.

    Returns:
        bool: True if the configuration is valid, False otherwise.
    """
    required_vars = {
        "YOUTUBE_API_KEY": YOUTUBE_API_KEY,
        "SPOTIPY_CLIENT_ID": SPOTIPY_CLIENT_ID,
        "SPOTIPY_CLIENT_SECRET": SPOTIPY_CLIENT_SECRET,
        "SPOTIPY_REDIRECT_URI": SPOTIPY_REDIRECT_URI,
    }
    missing_vars = [key for key, value in required_vars.items() if not value]
    if missing_vars:
        print(
            f"Error: Missing required configuration variables: {', '.join(missing_vars)}"
        )
        print(f"Please ensure they are set in your .env file located at: {ENV_PATH}")
        return False
    return True


if __name__ == "__main__":
    if validate_configuration():
        print("Configuration loaded successfully.")
        print(
            f"YOUTUBE_API_KEY: {'*' * 5 if YOUTUBE_API_KEY else None}"
        )  # Avoid printing actual key
        print(f"SPOTIPY_CLIENT_ID: {'*' * 5 if SPOTIPY_CLIENT_ID else None}")
        print(f"Data Directory: {DATA_DIR}")
    else:
        print("Configuration validation failed.")
