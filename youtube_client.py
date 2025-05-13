# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Client for interacting with the YouTube Data API v3.
# Handles fetching playlist items and parsing basic song information.
# -----------------------------------------------------------------------------

import logging
from typing import List, Optional, Dict, Any

from googleapiclient.discovery import build, Resource
from googleapiclient.errors import HttpError

import config
import models
import utils

logger = logging.getLogger(__name__)


class YouTubeClient:
    """
    A client to interact with the YouTube Data API v3.
    """

    YOUTUBE_API_SERVICE_NAME = "youtube"
    YOUTUBE_API_VERSION = "v3"

    def __init__(self, api_key: Optional[str]):
        """
        Initializes the YouTube API client.

        Args:
            api_key: The YouTube Data API key.

        Raises:
            ValueError: If the API key is not provided.
        """
        if not api_key:
            logger.error("YouTube API key is not provided.")
            raise ValueError("YouTube API key is required to initialize YouTubeClient.")
        try:
            self.youtube_service: Resource = build(
                self.YOUTUBE_API_SERVICE_NAME,
                self.YOUTUBE_API_VERSION,
                developerKey=api_key,
            )
            logger.info("YouTube API client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube API client: {e}", exc_info=True)
            raise ConnectionError(f"Could not build YouTube API service: {e}") from e

    def get_playlist_items(self, playlist_id: str) -> List[models.YouTubeSong]:
        """
        Fetches all video items from a given YouTube playlist ID.

        Handles API pagination to retrieve all items. Parses video titles
        to attempt to extract artist and song names.

        Args:
            playlist_id: The ID of the YouTube playlist.

        Returns:
            A list of YouTubeSong objects representing the videos in the playlist.
            Returns an empty list if the playlist is not found, is empty,
            or an API error occurs.
        """
        if not self.youtube_service:
            logger.error(
                "YouTube service is not initialized. Cannot fetch playlist items.",
                exc_info=True,
            )
            return []

        all_songs: List[models.YouTubeSong] = []
        next_page_token: Optional[str] = None

        try:
            while True:
                request = self.youtube_service.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=playlist_id,
                    maxResults=config.YOUTUBE_MAX_RESULTS_PER_PAGE,
                    pageToken=next_page_token,
                )
                response: Dict[str, Any] = request.execute()

                for item in response.get("items", []):
                    snippet = item.get("snippet", {})
                    video_id = snippet.get("resourceId", {}).get("videoId")
                    original_title = snippet.get("title")
                    channel_title = snippet.get("channelTitle")
                    video_owner_channel_title = snippet.get("videoOwnerChannelTitle")

                    if not video_id or not original_title:
                        logger.warning(
                            f"Skipping item due to missing videoId or title: {item}"
                        )
                        continue

                    if (
                        original_title.lower() == "private video"
                        or original_title.lower() == "deleted video"
                    ):
                        logger.info(f"Skipping '{original_title}' (ID: {video_id})")
                        continue

                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    # Use the more specific videoOwnerChannelTitle if available, otherwise fallback to channelTitle
                    effective_channel_title = video_owner_channel_title or channel_title

                    # Clean and parse title
                    cleaned_title = utils.clean_youtube_title(original_title)
                    parsed_artist, parsed_song_name = (
                        utils.parse_artist_song_from_title(
                            cleaned_title, effective_channel_title
                        )
                    )

                    song = models.YouTubeSong(
                        video_id=video_id,
                        original_title=original_title,
                        channel_title=effective_channel_title
                        or "N/A",  # Ensure channel_title is not None
                        parsed_artist=parsed_artist,
                        parsed_song_name=parsed_song_name,
                        video_url=video_url,
                    )
                    all_songs.append(song)

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

            logger.info(
                f"Successfully fetched {len(all_songs)} items from playlist ID: {playlist_id}"
            )

        except HttpError as e:
            logger.error(
                f"An HTTP error occurred while fetching playlist '{playlist_id}': {e.resp.status} {e._get_reason()}",
                exc_info=True,
            )
            if e.resp.status == 404:
                logger.error(
                    f"Playlist with ID '{playlist_id}' not found.", exc_info=True
                )
            return []
        except Exception as e:
            logger.error(
                f"An unexpected error occurred while fetching playlist '{playlist_id}': {e}",
                exc_info=True,
            )
            return []

        return all_songs


if __name__ == "__main__":
    utils.ensure_data_directory_exists()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(config.APP_ERROR_LOG_FILE),
        ],
    )

    if not config.YOUTUBE_API_KEY:
        logger.error(
            "YOUTUBE_API_KEY not found in configuration. Please set it in your .env file.",
            exc_info=True,
        )
    else:
        try:
            yt_client = YouTubeClient(api_key=config.YOUTUBE_API_KEY)

            # Replace with a public playlist ID you want to test with
            # E.g., a popular music chart playlist or one of your own public playlists
            # test_playlist_id = "PLMC9KNkIncKtPzgY-5rmhvj7fax8fdxoj" # Example: Billboard Hot 100
            test_playlist_id = "PL9eEZ8DQbx7XnCd6jSj7lX6U9ToIsr63Y"

            if not test_playlist_id:
                logger.warning(
                    "Please set a 'test_playlist_id' in the __main__ block of youtube_client.py to test."
                )
            else:
                logger.info(
                    f"Attempting to fetch items from playlist: {test_playlist_id}"
                )
                songs = yt_client.get_playlist_items(test_playlist_id)

                if songs:
                    logger.info(f"\nFetched {len(songs)} songs. First 5 entries:")
                    for i, song in enumerate(songs):
                        print(f"  {i + 1}. Title: '{song.original_title}'")
                        print(
                            f"      Cleaned Title: '{utils.clean_youtube_title(song.original_title)}'"
                        )
                        print(
                            f"      Parsed Artist: '{song.parsed_artist}', Parsed Song: '{song.parsed_song_name}'"
                        )
                        print(f"      Channel: '{song.channel_title}'")
                        print(f"      Video ID: {song.video_id}, URL: {song.video_url}")
                        print("-" * 20)

                    # You could also write to a temporary CSV here for inspection
                    import csv

                    test_output_file = (
                        config.DATA_DIR / "youtube_client_test_output.csv"
                    )
                    with open(test_output_file, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(models.YouTubeSong.model_fields.keys())
                        for song_obj in songs:
                            writer.writerow(song_obj.model_dump().values())
                    logger.info(
                        f"Full list of fetched songs written to {test_output_file}"
                    )

                else:
                    logger.warning("No songs fetched or an error occurred.")

        except ValueError as ve:
            logger.error(f"Initialization error: {ve}", exc_info=True)
        except ConnectionError as ce:
            logger.error(f"Connection error during initialization: {ce}", exc_info=True)
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during testing: {e}", exc_info=True
            )
