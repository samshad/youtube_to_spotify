# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Main entry point for the YouTube to Spotify Playlist Migrator.
# -----------------------------------------------------------------------------

import logging
import config
import utils

# Initialize logger for this module
logger = logging.getLogger(__name__)


def run_migration() -> None:
    """
    Orchestrates the entire playlist migration process.
    """
    logger.info("Starting YouTube to Spotify Playlist Migrator.")

    # 1. Validate configuration
    if not config.validate_configuration():
        logger.error("Configuration validation failed. Exiting.", exc_info=True)
        return

    logger.info("Configuration validated successfully.")
    logger.info(f"Data directory: {config.DATA_DIR}")
    logger.info(f"Fuzzy match threshold set to: {config.FUZZY_MATCH_THRESHOLD}")

    # 2. Get user inputs (will be implemented later)
    # youtube_playlist_id = input("Enter the YouTube Playlist ID: ")
    # spotify_playlist_name = input("Enter the desired name for the new Spotify playlist: ")
    youtube_playlist_id = "YOUR_TEST_YOUTUBE_PLAYLIST_ID" # Placeholder for now
    spotify_playlist_name = "Test Migration Playlist" # Placeholder

    logger.info(f"Target YouTube Playlist ID: {youtube_playlist_id}")
    logger.info(f"Target Spotify Playlist Name: {spotify_playlist_name}")

    # --- Placeholder for future steps ---
    # 3. Initialize API clients
    # logger.info("Initializing API clients...")
    # try:
    #     yt_client = YouTubeClient(api_key=config.YOUTUBE_API_KEY)
    #     sp_client = SpotifyClient(
    #         client_id=config.SPOTIPY_CLIENT_ID,
    #         client_secret=config.SPOTIPY_CLIENT_SECRET,
    #         redirect_uri=config.SPOTIPY_REDIRECT_URI
    #     )
    #     logger.info("API clients initialized.")
    # except Exception as e:
    #     logger.error(f"Failed to initialize API clients: {e}", exc_info=True)
    #     return

    # 4. Fetch songs from YouTube
    # logger.info(f"Fetching songs from YouTube playlist: {youtube_playlist_id}...")
    # fetched_yt_songs = yt_client.get_playlist_items(youtube_playlist_id)
    # if not fetched_yt_songs:
    #     logger.warning("No songs found in the YouTube playlist or an error occurred.")
    #     return
    # logger.info(f"Fetched {len(fetched_yt_songs)} songs from YouTube.")
    # # Log fetched songs to CSV (utils.write_to_csv)

    # 5. Create/Get Spotify playlist
    # logger.info(f"Creating/Accessing Spotify playlist: {spotify_playlist_name}...")
    # spotify_playlist_id = sp_client.create_or_get_playlist(spotify_playlist_name)
    # if not spotify_playlist_id:
    #     logger.error("Failed to create or access Spotify playlist. Exiting.")
    #     return
    # logger.info(f"Using Spotify playlist ID: {spotify_playlist_id}")

    # 6. Process and migrate songs
    # logger.info("Starting song migration process...")
    # migration_results = []
    # spotify_track_uris_to_add = []
    # for yt_song in fetched_yt_songs:
    #     # Search, match, log result (append to migration_results and spotify_track_uris_to_add)
    #     pass # Placeholder

    # 7. Add songs to Spotify playlist
    # if spotify_track_uris_to_add:
    #     logger.info(f"Adding {len(spotify_track_uris_to_add)} tracks to Spotify playlist...")
    #     sp_client.add_tracks_to_playlist(spotify_playlist_id, spotify_track_uris_to_add)
    # else:
    #     logger.info("No tracks to add to Spotify.")

    # 8. Log results to CSV files
    # logger.info("Logging migration results...")
    # # utils.write_to_csv for successful, not_found

    logger.info("Playlist migration process completed (skeleton).")


if __name__ == "__main__":
    # This ensures that a data directory is created and logging is set up
    # before any other operations, even if run_migration() itself has an early exit.
    try:
        utils.ensure_data_directory_exists()
        utils.setup_logging() # Setup logging for the entire application
        run_migration()
    except Exception as e:
        # Catch-all for any unhandled exceptions at the top level
        # Logging should already be set up by setup_logging if it succeeded
        # If setup_logging failed, this might print to console if that handler is still active
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"A critical error occurred. Check {config.APP_ERROR_LOG_FILE} for details.")