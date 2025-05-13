# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Main entry point for the YouTube to Spotify Playlist Migrator.
# Orchestrates the entire process of fetching songs from a YouTube playlist,
# searching for them on Spotify, and adding them to a new Spotify playlist.
# Logs successes, failures, and songs not found to CSV files.
# -----------------------------------------------------------------------------

import logging
import csv
from typing import List, Dict, Tuple, Optional

import config
import utils
import models
import os

os.environ["PYTHONIOENCODING"] = "utf8"

from youtube_client import YouTubeClient
from spotify_client import SpotifyClient

logger = logging.getLogger(__name__)


def write_migration_results_to_csv(
    filepath: str, results: List[models.MigrationResult], headers: List[str]
) -> None:
    """
    Writes a list of MigrationResult objects to a CSV file.

    Args:
        filepath: The path to the CSV file.
        results: A list of MigrationResult objects.
        headers: The header row for the CSV file.
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for result in results:
                yt_song = result.youtube_song
                sp_track = result.spotify_track

                row = [
                    yt_song.original_title,
                    yt_song.parsed_artist or "N/A",
                    yt_song.parsed_song_name or "N/A",
                    yt_song.video_url,
                    yt_song.channel_title,
                ]
                if "spotify_track_name" in headers:  # For success file
                    row.extend(
                        [
                            sp_track.name if sp_track else "N/A",
                            ", ".join(sp_track.artists)
                            if sp_track and sp_track.artists
                            else "N/A",
                            sp_track.uri if sp_track else "N/A",
                            sp_track.external_url
                            if sp_track and sp_track.external_url
                            else "N/A",
                            result.match_score
                            if result.match_score is not None
                            else "N/A",
                        ]
                    )
                elif "reason" in headers:  # For not_found file
                    row.append(result.message or "Unknown reason")

                writer.writerow(row)
        logger.info(f"Successfully wrote {len(results)} results to '{filepath}'.")
    except IOError as e:
        logger.error(
            f"Failed to write results to CSV file '{filepath}': {e}", exc_info=True
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while writing to CSV '{filepath}': {e}",
            exc_info=True,
        )


def write_fetched_youtube_songs_to_csv(
    filepath: str, songs: List[models.YouTubeSong]
) -> None:
    """
    Writes a list of fetched YouTubeSong objects to a CSV file.

    Args:
        filepath: The path to the CSV file.
        songs: A list of YouTubeSong objects.
    """
    headers = [
        "youtube_original_title",
        "youtube_parsed_artist",
        "youtube_parsed_song_name",
        "youtube_video_url",
        "youtube_channel_title",
        "youtube_video_id",
    ]
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for song in songs:
                writer.writerow(
                    [
                        song.original_title,
                        song.parsed_artist or "N/A",
                        song.parsed_song_name or "N/A",
                        str(
                            song.video_url
                        ),  # Ensure HttpUrl is converted to string for CSV
                        song.channel_title,
                        song.video_id,
                    ]
                )
        logger.info(
            f"Successfully wrote {len(songs)} fetched YouTube songs to '{filepath}'."
        )
    except IOError as e:
        logger.error(
            f"Failed to write fetched YouTube songs to CSV '{filepath}': {e}",
            exc_info=True,
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while writing YouTube songs to CSV '{filepath}': {e}",
            exc_info=True,
        )


def run_migration() -> None:
    """
    Orchestrates the entire playlist migration process.
    """
    logger.info("======================================================")
    logger.info("== Starting YouTube to Spotify Playlist Migrator ==")
    logger.info("======================================================")

    if not config.validate_configuration():
        logger.error("Configuration validation failed. Exiting.")
        return
    logger.info("Configuration validated successfully.")
    logger.info(f"Data directory: {config.DATA_DIR}")
    logger.info(f"Fuzzy match threshold set to: {config.FUZZY_MATCH_THRESHOLD}")

    try:
        youtube_playlist_id = input(
            "Enter the YouTube Playlist ID (e.g., PLxxxxxxxxxxxxxxxxx): "
        ).strip()
        if not youtube_playlist_id:
            logger.error("YouTube Playlist ID cannot be empty. Exiting.")
            return
        spotify_playlist_name = input(
            f"Enter the desired name for the new Spotify playlist (default: 'Migrated from {youtube_playlist_id}'): "
        ).strip()
        if not spotify_playlist_name:
            spotify_playlist_name = f"Migrated from {youtube_playlist_id}"
    except KeyboardInterrupt:
        logger.info("\nUser cancelled input. Exiting.")
        return
    logger.info(f"Target YouTube Playlist ID: {youtube_playlist_id}")
    logger.info(f"Target Spotify Playlist Name: {spotify_playlist_name}")

    logger.info("Initializing API clients...")
    yt_client: YouTubeClient
    sp_client: SpotifyClient
    try:
        yt_client = YouTubeClient(api_key=config.YOUTUBE_API_KEY)
        logger.info(
            "Initializing Spotify client (this may open a browser for authentication)..."
        )
        sp_client = SpotifyClient(
            client_id=config.SPOTIPY_CLIENT_ID,
            client_secret=config.SPOTIPY_CLIENT_SECRET,
            redirect_uri=config.SPOTIPY_REDIRECT_URI,
            fuzzy_match_threshold=config.FUZZY_MATCH_THRESHOLD,
        )
        logger.info("API clients initialized successfully.")
    except ValueError as ve:
        logger.error(
            f"Failed to initialize API clients due to configuration: {ve}",
            exc_info=True,
        )
        return
    except ConnectionError as ce:
        logger.error(
            f"Failed to initialize API clients due to connection/auth error: {ce}",
            exc_info=True,
        )
        return
    except Exception as e:
        logger.error(
            f"An unexpected error occurred during API client initialization: {e}",
            exc_info=True,
        )
        return

    logger.info(f"Fetching songs from YouTube playlist: {youtube_playlist_id}...")
    fetched_yt_songs: List[models.YouTubeSong] = yt_client.get_playlist_items(
        youtube_playlist_id
    )
    if not fetched_yt_songs:
        logger.warning(
            "No songs found in the YouTube playlist or an error occurred during fetch. Exiting."
        )
        return
    logger.info(f"Fetched {len(fetched_yt_songs)} songs from YouTube.")
    write_fetched_youtube_songs_to_csv(config.FETCHED_SONGS_FILE, fetched_yt_songs)

    logger.info(f"Creating or accessing Spotify playlist: '{spotify_playlist_name}'...")
    spotify_playlist_id = sp_client.create_or_get_playlist(
        playlist_name=spotify_playlist_name,
        description=f"Playlist migrated from YouTube (Playlist ID: {youtube_playlist_id}).",
    )
    if not spotify_playlist_id:
        logger.error("Failed to create or access Spotify playlist. Exiting.")
        return
    logger.info(
        f"Using Spotify playlist ID: {spotify_playlist_id} for playlist '{spotify_playlist_name}'."
    )

    logger.info(f"Starting song migration process for {len(fetched_yt_songs)} songs...")
    successful_migrations: List[models.MigrationResult] = []
    not_found_or_error_migrations: List[models.MigrationResult] = []
    spotify_track_uris_to_add: List[str] = []

    # Cache to store results of previous searches: key=(lower_artist, lower_song), value=SpotifyTrack or None
    processed_songs_cache: Dict[
        Tuple[Optional[str], Optional[str]], Optional[models.SpotifyTrack]
    ] = {}
    # Store match score separately if needed for cached results
    # cache_scores: Dict[Tuple[Optional[str], Optional[str]], int] = {}

    total_songs = len(fetched_yt_songs)
    for i, yt_song in enumerate(fetched_yt_songs):
        logger.info(
            f"Processing song {i + 1}/{total_songs}: '{yt_song.original_title}'..."
        )

        if not yt_song.parsed_song_name:
            logger.warning(
                f"  SKIPPED: No parsed song name for '{yt_song.original_title}'."
            )
            migration = models.MigrationResult(
                youtube_song=yt_song,
                status="SKIPPED",
                message="Missing parsed song name.",
            )
            not_found_or_error_migrations.append(migration)
            continue

        # Create the cache lookup key (case-insensitive)
        lookup_key = (
            yt_song.parsed_artist.lower().strip() if yt_song.parsed_artist else None,
            yt_song.parsed_song_name.lower().strip(),
        )

        spotify_track_found: Optional[models.SpotifyTrack] = None
        migration_status: str = ""
        match_score: Optional[int] = None
        message: Optional[str] = None

        if lookup_key in processed_songs_cache:
            spotify_track_found = processed_songs_cache[lookup_key]
            # Optionally retrieve score if you stored it for comparison:
            # match_score = cache_scores.get(lookup_key)

            if spotify_track_found:
                migration_status = "SUCCESS (Cached)"
                message = f"Reused cached Spotify track '{spotify_track_found.name}'"
                spotify_track_uris_to_add.append(spotify_track_found.uri)
                logger.info(f"  CACHE HIT: Reusing successful result for {lookup_key}.")
            else:
                migration_status = "NOT_FOUND (Cached)"
                message = f"Reused cached 'not found' status for {lookup_key}"
                logger.info(
                    f"  CACHE HIT: Reusing 'not found' result for {lookup_key}."
                )

        else:  # Not in cache, perform Spotify search
            logger.debug(f"  CACHE MISS: Searching Spotify for {lookup_key}...")
            search_result_tuple = sp_client.search_track(yt_song)

            if search_result_tuple:
                spotify_track_found, match_score = search_result_tuple
                migration_status = "SUCCESS"
                message = f"Found Spotify track '{spotify_track_found.name}' (Score: {match_score})"
                processed_songs_cache[lookup_key] = (
                    spotify_track_found  # Cache the found track
                )
                # Optionally store score: cache_scores[lookup_key] = match_score
                spotify_track_uris_to_add.append(spotify_track_found.uri)
                logger.info(f"  {message}")
            else:
                migration_status = "NOT_FOUND"
                message = "No suitable match found on Spotify or search error occurred."
                processed_songs_cache[lookup_key] = None
                logger.warning(
                    f"  NOT FOUND: Could not find a match for '{yt_song.original_title}'."
                )

        migration = models.MigrationResult(
            youtube_song=yt_song,
            spotify_track=spotify_track_found,
            match_score=match_score,
            status=migration_status,
            message=message,
        )

        if migration_status.startswith("SUCCESS"):
            successful_migrations.append(migration)
        else:
            not_found_or_error_migrations.append(migration)

        # Optional: Small delay between processing each song, regardless of cache hit/miss
        # time.sleep(2) # 2s

    if spotify_track_uris_to_add:
        unique_uris_to_add = list(set(spotify_track_uris_to_add))
        logger.info(
            f"Attempting to add {len(unique_uris_to_add)} unique tracks to Spotify playlist '{spotify_playlist_name}'..."
        )
        add_success = sp_client.add_tracks_to_playlist(
            spotify_playlist_id, unique_uris_to_add
        )
        if add_success:
            logger.info(
                f"Successfully added {len(unique_uris_to_add)} tracks to the Spotify playlist."
            )
        else:
            logger.error(
                "Failed to add some or all tracks to the Spotify playlist. Check logs for batch errors."
            )
    else:
        logger.info(
            "No tracks were found or successfully matched on Spotify to add to the playlist."
        )

    logger.info("Logging migration results to CSV files...")

    success_headers = [
        "youtube_original_title",
        "youtube_parsed_artist",
        "youtube_parsed_song_name",
        "youtube_video_url",
        "youtube_channel_title",
        "spotify_track_name",
        "spotify_artists",
        "spotify_uri",
        "spotify_external_url",
        "match_score",
        "migration_status",
        "details",
    ]

    not_found_headers = [
        "youtube_original_title",
        "youtube_parsed_artist",
        "youtube_parsed_song_name",
        "youtube_video_url",
        "youtube_channel_title",
        "migration_status",
        "details",
    ]

    write_migration_results_to_csv_updated(
        config.SUCCESS_LOG_FILE, successful_migrations, success_headers
    )
    write_migration_results_to_csv_updated(
        config.NOT_FOUND_LOG_FILE, not_found_or_error_migrations, not_found_headers
    )

    logger.info("===================================================")
    logger.info("== Playlist Migration Process Completed.         ==")
    logger.info("== Summary:                                    ==")
    logger.info(f"== Total YouTube songs processed: {total_songs}          ==")
    logger.info(f"== Successfully migrated to Spotify: {len(successful_migrations)} ==")
    logger.info(
        f"== Songs not found or errors: {len(not_found_or_error_migrations)}      =="
    )
    logger.info("==                                                 ==")
    logger.info("== Detailed logs:                                ==")
    logger.info(f"==   Fetched YouTube Songs: {config.FETCHED_SONGS_FILE} ==")
    logger.info(f"==   Successful Migrations: {config.SUCCESS_LOG_FILE} ==")
    logger.info(f"==   Not Found/Errors:      {config.NOT_FOUND_LOG_FILE} ==")
    logger.info(f"==   Application Errors:    {config.APP_ERROR_LOG_FILE} ==")
    logger.info("===================================================")


def write_migration_results_to_csv_updated(
    filepath: str, results: List[models.MigrationResult], headers: List[str]
) -> None:
    """
    Writes a list of MigrationResult objects to a CSV file, including status/message.

    Args:
        filepath: The path to the CSV file.
        results: A list of MigrationResult objects.
        headers: The header row for the CSV file.
    """
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)

            for result in results:
                yt_song = result.youtube_song
                sp_track = result.spotify_track
                row_dict = {
                    "youtube_original_title": yt_song.original_title,
                    "youtube_parsed_artist": yt_song.parsed_artist or "N/A",
                    "youtube_parsed_song_name": yt_song.parsed_song_name or "N/A",
                    "youtube_video_url": str(yt_song.video_url),
                    "youtube_channel_title": yt_song.channel_title,
                    "spotify_track_name": sp_track.name if sp_track else "N/A",
                    "spotify_artists": ", ".join(sp_track.artists)
                    if sp_track and sp_track.artists
                    else "N/A",
                    "spotify_uri": sp_track.uri if sp_track else "N/A",
                    "spotify_external_url": str(sp_track.external_url)
                    if sp_track and sp_track.external_url
                    else "N/A",
                    "match_score": result.match_score
                    if result.match_score is not None
                    else "N/A",
                    "migration_status": result.status,
                    "details": result.message or "",
                }
                row = [row_dict.get(header, "N/A") for header in headers]
                writer.writerow(row)

        logger.info(f"Successfully wrote {len(results)} results to '{filepath}'.")
    except IOError as e:
        logger.error(
            f"Failed to write results to CSV file '{filepath}': {e}", exc_info=True
        )
    except Exception as e:
        logger.error(
            f"An unexpected error occurred while writing to CSV '{filepath}': {e}",
            exc_info=True,
        )


if __name__ == "__main__":
    try:
        utils.ensure_data_directory_exists()
        utils.setup_logging()
        run_migration()
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. Exiting gracefully.")
    except Exception as e:
        logger.critical(
            f"An unhandled critical error occurred in main: {e}", exc_info=True
        )
        print(
            f"A critical error occurred. Check {config.APP_ERROR_LOG_FILE} for details."
        )
