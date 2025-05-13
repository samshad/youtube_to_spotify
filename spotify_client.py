# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Client for interacting with the Spotify Web API using Spotipy.
# Handles OAuth authentication, track searching with fuzzy matching,
# playlist creation, and adding tracks to playlists.
# -----------------------------------------------------------------------------

import logging
import time
import math
from typing import List, Optional, Tuple

import spotipy
from spotipy.oauth2 import SpotifyOAuth, CacheFileHandler
from fuzzywuzzy import fuzz  # type: ignore # fuzzywuzzy doesn't have official stubs

import config
import models
import utils

logger = logging.getLogger(__name__)

# Define required Spotify scopes
SPOTIFY_SCOPES = "playlist-read-private playlist-modify-public playlist-modify-private user-library-read"


class SpotifyClient:
    """
    A client to interact with the Spotify Web API.
    Handles authentication, searching, and playlist modification.
    """

    def __init__(
        self,
        client_id: Optional[str],
        client_secret: Optional[str],
        redirect_uri: Optional[str],
        fuzzy_match_threshold: int = config.FUZZY_MATCH_THRESHOLD,
    ):
        """
        Initializes the Spotify client using SpotifyOAuth for user authorization.

        Args:
            client_id: Spotify application client ID.
            client_secret: Spotify application client secret.
            redirect_uri: Spotify application redirect URI.
            fuzzy_match_threshold: The minimum score (0-100) for a fuzzy match to be considered valid.

        Raises:
            ValueError: If required authentication credentials are missing.
            ConnectionError: If authentication fails or the user ID cannot be retrieved.
        """
        if not all([client_id, client_secret, redirect_uri]):
            msg = "Spotify client_id, client_secret, and redirect_uri are required."
            logger.error(msg)
            raise ValueError(msg)

        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.fuzzy_match_threshold = fuzzy_match_threshold

        # Configure cache handler to store token info in the project root
        cache_path = config.PROJECT_ROOT / ".spotify_token_cache"
        self._auth_manager = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=SPOTIFY_SCOPES,
            cache_handler=CacheFileHandler(cache_path=str(cache_path)),
            show_dialog=True,  # Force show dialog each time for user confirmation
        )

        try:
            # Attempt to get token and initialize Spotipy client
            # This might trigger browser authentication flow
            self.sp = spotipy.Spotify(auth_manager=self._auth_manager)
            # Verify authentication by fetching user ID
            self.user_id = self._get_user_id()
            if not self.user_id:
                raise ConnectionError(
                    "Failed to retrieve Spotify User ID after authentication."
                )
            logger.info(
                f"Spotify client initialized successfully for user ID: {self.user_id}"
            )

        except spotipy.SpotifyException as e:
            logger.error(f"Spotify authentication failed: {e}", exc_info=True)
            raise ConnectionError(f"Could not authenticate with Spotify: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}", exc_info=True)
            # Handle potential browser auth issues or other exceptions
            if "Could not automatically open browser" in str(e):
                logger.warning(
                    "Could not open browser automatically. Please open the printed URL manually."
                )
            raise ConnectionError(
                f"An unexpected error occurred during Spotify init: {e}"
            ) from e

    def _get_user_id(self) -> Optional[str]:
        """Fetches the current authenticated user's Spotify ID."""
        try:
            user_info = self.sp.current_user()
            return user_info["id"] if user_info else None
        except spotipy.SpotifyException as e:
            logger.error(f"Could not fetch Spotify user ID: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error fetching Spotify user ID: {e}", exc_info=True
            )
            return None

    def search_track(
        self, youtube_song: models.YouTubeSong
    ) -> Optional[Tuple[models.SpotifyTrack, int]]:
        """
        Searches Spotify for a track matching the given YouTube song details.

        Uses fuzzy matching to compare potential matches against the YouTube title.
        Performs an initial targeted search, and if no results, a broader search.

        Args:
            youtube_song: The YouTubeSong object containing parsed details.

        Returns:
            A tuple containing the best matching SpotifyTrack and the match score,
            or None if no suitable match is found above the threshold after all attempts.
        """
        if not youtube_song.parsed_song_name:
            logger.warning(
                f"Skipping search for video '{youtube_song.original_title}' (ID: {youtube_song.video_id}) due to missing parsed song name."
            )
            return None

        query_targeted: str
        if youtube_song.parsed_artist and youtube_song.parsed_song_name:
            query_targeted = f"track:{youtube_song.parsed_song_name} artist:{youtube_song.parsed_artist}"
        else:
            query_targeted = f"track:{youtube_song.parsed_song_name}"

        logger.debug(
            f"Spotify Search (Attempt 1 - Targeted): Query: '{query_targeted}'"
        )
        tracks: List[dict] = []

        try:
            results = self.sp.search(q=query_targeted, type="track", limit=10)
            tracks = results.get("tracks", {}).get("items", [])
        except spotipy.SpotifyException as e:
            logger.error(
                f"Spotify API search error for targeted query '{query_targeted}': {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"Unexpected error during targeted Spotify search for query '{query_targeted}': {e}",
                exc_info=True,
            )

        if not tracks:
            logger.info(
                f"No results from targeted search. Trying broader search for '{youtube_song.original_title}'."
            )
            # Construct a simpler query using parsed artist (if any) and song name
            query_simple = f"{youtube_song.parsed_artist or ''} {youtube_song.parsed_song_name}".strip()
            # Also consider using the cleaned YouTube title directly if parsing was minimal
            # Later-maybe: query_alternative = utils.clean_youtube_title(youtube_song.original_title)

            if not query_simple:
                logger.warning(
                    f"Skipping broader search for '{youtube_song.original_title}' as query_simple is empty."
                )
                return None

            logger.debug(
                f"Spotify Search (Attempt 2 - Broader): Query: '{query_simple}'"
            )
            try:
                # Add a small delay before the second API call if the first one was made
                time.sleep(2)  # 2s delay
                results = self.sp.search(q=query_simple, type="track", limit=10)
                tracks = results.get("tracks", {}).get("items", [])
            except spotipy.SpotifyException as e:
                logger.error(
                    f"Spotify API search error for broader query '{query_simple}': {e}",
                    exc_info=True,
                )
                return None
            except Exception as e:
                logger.error(
                    f"Unexpected error during broader Spotify search for query '{query_simple}': {e}",
                    exc_info=True,
                )
                return None

        if not tracks:
            logger.info(
                f"No Spotify tracks found for '{youtube_song.original_title}' after all search attempts."
            )
            return None

        # --- Process search results (common for both attempts) ---
        best_match: Optional[models.SpotifyTrack] = None
        highest_score: int = 0

        # Use parsed artist and song name to create a target string for fuzzy matching
        target_str = f"{youtube_song.parsed_artist or ''} {youtube_song.parsed_song_name}".strip()
        # If parsed_song_name is the primary component, ensure it's not empty
        if not target_str and youtube_song.original_title:
            target_str = utils.clean_youtube_title(youtube_song.original_title)

        if not target_str:
            logger.warning(
                f"Cannot perform fuzzy matching for '{youtube_song.original_title}' due to empty target string."
            )
            return None

        target_str_lower = target_str.lower()

        for item in tracks:
            spotify_name = item.get("name")
            spotify_artists_list = [
                artist.get("name")
                for artist in item.get("artists", [])
                if artist.get("name")
            ]
            if not spotify_name or not spotify_artists_list:
                continue

            candidate_str = f"{' & '.join(spotify_artists_list)} {spotify_name}".strip()
            candidate_str_lower = candidate_str.lower()

            score = fuzz.token_set_ratio(target_str_lower, candidate_str_lower)
            logger.debug(
                f"Comparing YT:'{target_str}' | SP:'{candidate_str}' | Score: {score}"
            )

            if score >= self.fuzzy_match_threshold and score > highest_score:
                highest_score = score
                spotify_uri = item.get("uri")
                spotify_id = item.get("id")
                album_name = item.get("album", {}).get("name")
                duration_ms = item.get("duration_ms")
                external_url = item.get("external_urls", {}).get("spotify")

                if spotify_uri and spotify_id:
                    best_match = models.SpotifyTrack(
                        uri=spotify_uri,
                        name=spotify_name,
                        artists=spotify_artists_list,
                        spotify_id=spotify_id,
                        album_name=album_name,
                        duration_ms=duration_ms,
                        external_url=external_url,
                    )

        # Add a small delay to avoid hitting rate limits too quickly if called in a loop,
        # especially after multiple search attempts within this function.
        time.sleep(2)  # 2s delay after each full search_track call.

        if best_match:
            logger.info(
                f"Found match for YT:'{target_str}' -> SP:'{best_match.name}' by {', '.join(best_match.artists)} (Score: {highest_score})"
            )
            return best_match, highest_score
        else:
            logger.info(
                f"No suitable match found above threshold {self.fuzzy_match_threshold} for YT:'{target_str}' after all attempts."
            )
            return None

    def create_or_get_playlist(
        self, playlist_name: str, public: bool = True, description: str = ""
    ) -> Optional[str]:
        """
        Finds a playlist by name for the current user, or creates it if not found.

        Args:
            playlist_name: The desired name of the playlist.
            public: Whether the playlist should be public (default True).
            description: A description for the playlist if created.

        Returns:
            The Spotify Playlist ID if found or created, otherwise None.
        """
        logger.info(f"Checking for existing Spotify playlist named: '{playlist_name}'")
        playlist_id: Optional[str] = None
        offset = 0
        limit = 50  # Max limit for current_user_playlists

        try:
            while True:
                playlists = self.sp.current_user_playlists(limit=limit, offset=offset)
                if not playlists or not playlists.get("items"):
                    break

                for playlist in playlists["items"]:
                    if (
                        playlist["name"] == playlist_name
                        and playlist["owner"]["id"] == self.user_id
                    ):
                        playlist_id = playlist["id"]
                        logger.info(
                            f"Found existing playlist '{playlist_name}' with ID: {playlist_id}"
                        )
                        break

                if playlist_id:
                    break

                # Prepare for next page if necessary
                offset += limit
                if offset >= playlists.get("total", 0):
                    break  # Reached the end

            if not playlist_id:
                logger.info(
                    f"Playlist '{playlist_name}' not found. Creating new playlist..."
                )
                new_playlist = self.sp.user_playlist_create(
                    user=self.user_id,
                    name=playlist_name,
                    public=public,
                    description=description,
                )
                playlist_id = new_playlist["id"]
                logger.info(
                    f"Successfully created playlist '{playlist_name}' with ID: {playlist_id}"
                )

        except spotipy.SpotifyException as e:
            logger.error(
                f"Spotify API error during playlist check/creation for '{playlist_name}': {e}",
                exc_info=True,
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error during playlist check/creation: {e}", exc_info=True
            )
            return None

        return playlist_id

    def add_tracks_to_playlist(self, playlist_id: str, track_uris: List[str]) -> bool:
        """
        Adds tracks to a specified Spotify playlist.

        Handles batching requests according to Spotify API limits.

        Args:
            playlist_id: The ID of the target Spotify playlist.
            track_uris: A list of Spotify track URIs (e.g., ["spotify:track:...", ...]).

        Returns:
            True if all tracks were added successfully (or if list was empty), False otherwise.
        """
        if not track_uris:
            logger.info("No track URIs provided to add to playlist.")
            return True

        logger.info(
            f"Attempting to add {len(track_uris)} tracks to playlist ID: {playlist_id}"
        )
        all_successful = True
        num_batches = math.ceil(
            len(track_uris) / config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST
        )

        for i in range(num_batches):
            start_index = i * config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST
            end_index = start_index + config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST
            batch = track_uris[start_index:end_index]

            logger.info(
                f"Adding batch {i + 1}/{num_batches} ({len(batch)} tracks) to playlist {playlist_id}..."
            )
            try:
                self.sp.playlist_add_items(playlist_id=playlist_id, items=batch)
                logger.info(f"Successfully added batch {i + 1}/{num_batches}.")
                # Add a small delay between batch requests
                if num_batches > 1:
                    time.sleep(2)  # 2s delay

            except spotipy.SpotifyException as e:
                logger.error(
                    f"Spotify API error adding batch {i + 1} to playlist {playlist_id}: {e}",
                    exc_info=True,
                )
                all_successful = False
                # Decide if you want to stop on first error or continue trying other batches
                # continue # Or break
            except Exception as e:
                logger.error(
                    f"Unexpected error adding batch {i + 1} to playlist {playlist_id}: {e}",
                    exc_info=True,
                )
                all_successful = False
                # continue # Or break

        if all_successful:
            logger.info(
                f"Successfully added all {len(track_uris)} tracks to playlist {playlist_id}."
            )
        else:
            logger.error(
                f"Failed to add some or all tracks to playlist {playlist_id}. Check logs."
            )

        return all_successful


if __name__ == "__main__":
    utils.ensure_data_directory_exists()
    utils.setup_logging()

    logger.info("--- SpotifyClient Test ---")

    if not config.validate_configuration():
        logger.error("Spotify configuration is missing in .env file. Cannot run test.")
    else:
        try:
            logger.info(
                "Initializing SpotifyClient (may require browser authentication)..."
            )
            spotify_client = SpotifyClient(
                client_id=config.SPOTIPY_CLIENT_ID,
                client_secret=config.SPOTIPY_CLIENT_SECRET,
                redirect_uri=config.SPOTIPY_REDIRECT_URI,
            )
            logger.info("SpotifyClient initialized.")

            logger.info("\n--- Testing Track Search ---")
            test_yt_song = models.YouTubeSong(
                video_id="test_vid_1",
                original_title="CHVRCHES - Death Stranding",
                channel_title="Naani",
                parsed_artist="CHVRCHES",
                parsed_song_name="Death Stranding",
                video_url="https://example.com",
            )
            search_result = spotify_client.search_track(test_yt_song)
            if search_result:
                track, score = search_result
                logger.info(
                    f"Search Result: Found '{track.name}' by {', '.join(track.artists)} with score {score}"
                )
                logger.info(f"   URI: {track.uri}")
                test_track_uri = track.uri
            else:
                logger.warning(
                    f"Search Result: Track for '{test_yt_song.original_title}' not found or below threshold."
                )
                test_track_uri = None

            logger.info("\n--- Testing Playlist Creation/Retrieval ---")
            test_playlist_name = "YT_SP_Migrator_Test_Playlist"
            playlist_id = spotify_client.create_or_get_playlist(
                test_playlist_name,
                description="Test playlist for youtube_to_spotify script.",
            )
            if playlist_id:
                logger.info(
                    f"Playlist Test: Successfully obtained playlist ID: {playlist_id}"
                )

                logger.info("\n--- Testing Adding Track(s) to Playlist ---")
                if test_track_uri:
                    tracks_to_add = [test_track_uri]
                    add_success = spotify_client.add_tracks_to_playlist(
                        playlist_id, tracks_to_add
                    )
                    if add_success:
                        logger.info(
                            f"Add Track Test: Successfully added tracks to playlist '{test_playlist_name}'."
                        )
                        logger.info(
                            f"Check your Spotify account for playlist '{test_playlist_name}'!"
                        )
                    else:
                        logger.error(
                            "Add Track Test: Failed to add tracks to the playlist."
                        )
                else:
                    logger.warning(
                        "Add Track Test: Skipping add track test because search failed to find a track URI."
                    )
            else:
                logger.error(
                    "Playlist Test: Failed to create or get the test playlist ID."
                )

        except ValueError as ve:
            logger.error(f"Initialization error: {ve}")
        except ConnectionError as ce:
            logger.error(f"Connection or Authentication error: {ce}")
        except Exception as e:
            logger.error(
                f"An unexpected error occurred during Spotify testing: {e}",
                exc_info=True,
            )

    logger.info("--- SpotifyClient Test End ---")
