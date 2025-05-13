# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Unit tests for the SpotifyClient class.
# -----------------------------------------------------------------------------

import pytest
from unittest.mock import patch, call

from spotify_client import SpotifyClient, SPOTIFY_SCOPES
from models import YouTubeSong, SpotifyTrack
import config
from spotipy.oauth2 import CacheFileHandler
from spotipy import SpotifyException  # For simulating errors

# --- Sample Data ---
SAMPLE_YOUTUBE_SONG_PARSED = YouTubeSong(
    video_id="yt123",
    original_title="ArtistX - SongX (Official)",
    channel_title="ArtistX Channel",
    parsed_artist="ArtistX",
    parsed_song_name="SongX",
    video_url="https://youtube.com/watch?v=yt123",
)
SAMPLE_YOUTUBE_SONG_NO_ARTIST = YouTubeSong(
    video_id="yt456",
    original_title="Just A Song Title",
    channel_title="Some Uploader",
    parsed_artist=None,  # No artist parsed
    parsed_song_name="Just A Song Title",
    video_url="https://youtube.com/watch?v=yt456",
)
SAMPLE_YOUTUBE_SONG_NO_NAME = YouTubeSong(
    video_id="yt789",
    original_title="Artist Only - (Video)",
    channel_title="Artist Channel",
    parsed_artist="Artist Only",
    parsed_song_name=None,  # No song name parsed
    video_url="https://youtube.com/watch?v=yt789",
)

# What we expect spotipy.search to return
SPOTIFY_SEARCH_RESULT_ITEM_1 = {
    "name": "SongX Matched",
    "artists": [{"name": "ArtistX"}],
    "uri": "spotify:track:track_id_X",
    "id": "track_id_X",
    "album": {"name": "AlbumX"},
    "duration_ms": 200000,
    "external_urls": {"spotify": "https://open.spotify.com/track/track_id_X"},
}
SPOTIFY_SEARCH_RESULT_ITEM_2_LOW_SCORE = {  # For testing fuzzy match threshold
    "name": "SongY Different",
    "artists": [{"name": "ArtistY"}],
    "uri": "spotify:track:track_id_Y",
    "id": "track_id_Y",
    "album": {"name": "AlbumY"},
    "duration_ms": 210000,
    "external_urls": {"spotify": "https://open.spotify.com/track/track_id_Y"},
}

SPOTIFY_USER_PLAYLIST_ITEM_EXISTING = {
    "name": "MyTestPlaylist",
    "id": "existing_playlist_id",
    "owner": {
        "id": "test_user_id_spotify"
    },  # Match this with what current_user returns
}
SPOTIFY_USER_PLAYLIST_ITEM_OTHER = {
    "name": "OtherUserPlaylist",
    "id": "other_playlist_id",
    "owner": {"id": "other_user_id"},
}


# --- Fixtures ---


@pytest.fixture
def mock_spotipy_oauth():
    """Mocks spotipy.oauth2.SpotifyOAuth."""
    # SpotifyOAuth is instantiated in SpotifyClient.__init__
    # We want to mock the class itself so when SpotifyClient calls SpotifyOAuth(...),
    # it gets our mock instance.
    with patch("spotify_client.SpotifyOAuth", autospec=True) as mock_oauth_class:
        # Configure the instance that SpotifyOAuth(...) will return
        mock_oauth_instance = mock_oauth_class.return_value
        # mock_oauth_instance.get_cached_token.return_value = {"access_token": "fake_token", ...} # If needed
        yield mock_oauth_class, mock_oauth_instance


@pytest.fixture
def mock_spotipy_spotify(
    mock_spotipy_oauth,
):  # Depends on mock_spotipy_oauth to ensure OAuth is mocked first
    """Mocks spotipy.Spotify class and its instance methods."""
    # Similar to OAuth, we mock the spotipy.Spotify class
    with patch("spotify_client.spotipy.Spotify", autospec=True) as mock_spotify_class:
        mock_spotify_instance = (
            mock_spotify_class.return_value
        )  # This is what self.sp becomes

        # Pre-configure common methods that are called during init or frequently
        mock_spotify_instance.current_user.return_value = {
            "id": "test_user_id_spotify",
            "display_name": "Test User",
        }

        yield mock_spotify_class, mock_spotify_instance


@pytest.fixture
def spotify_client_instance(mock_spotipy_spotify):  # Depends on mock_spotipy_spotify
    """Provides a SpotifyClient instance with mocked Spotipy dependencies."""
    # mock_spotipy_spotify fixture already handles mocking SpotifyOAuth and Spotify classes
    client = SpotifyClient(
        client_id="fake_client_id",
        client_secret="fake_client_secret",
        redirect_uri="http://localhost:8888/callback",
        fuzzy_match_threshold=85,  # Can override in specific tests if needed
    )
    return client


# --- Test Cases ---


# Initialization Tests
def test_spotify_client_initialization_success(
    mock_spotipy_oauth, mock_spotipy_spotify
):
    """Test successful initialization of SpotifyClient."""
    mock_oauth_class, mock_oauth_instance = mock_spotipy_oauth
    mock_spotify_class, mock_spotify_instance = mock_spotipy_spotify

    client = SpotifyClient(
        client_id="test_id", client_secret="test_secret", redirect_uri="http://test.com"
    )

    assert client.sp is mock_spotify_instance
    assert client.user_id == "test_user_id_spotify"

    actual_call_args = mock_oauth_class.call_args
    assert isinstance(actual_call_args[1]["cache_handler"], CacheFileHandler)

    mock_oauth_class.assert_called_once_with(
        client_id="test_id",
        client_secret="test_secret",
        redirect_uri="http://test.com",
        scope=SPOTIFY_SCOPES,
        cache_handler=actual_call_args[1][
            "cache_handler"
        ],  # Use the actual passed handler
        show_dialog=True,
    )

    mock_spotify_class.assert_called_once_with(auth_manager=mock_oauth_instance)
    mock_spotify_instance.current_user.assert_called_once()


def test_spotify_client_init_missing_credentials():
    """Test ValueError if credentials are missing."""
    with pytest.raises(
        ValueError, match="client_id, client_secret, and redirect_uri are required"
    ):
        SpotifyClient(client_id=None, client_secret="secret", redirect_uri="uri")
    # ... test other combinations of missing credentials ...


@patch("spotify_client.SpotifyOAuth")
@patch("spotify_client.spotipy.Spotify", autospec=True)
def test_spotify_client_init_oauth_constructor_direct_exception(
    mock_spotify_class, mock_oauth_class_basic
):
    """Test that SpotifyClient init fails if SpotifyOAuth constructor raises directly."""
    mock_oauth_class_basic.side_effect = ValueError(
        "OAuth constructor direct fail"
    )  # Use a specific stdlib error

    with pytest.raises(
        ValueError, match="OAuth constructor direct fail"
    ):  # Expect the mock's direct error
        SpotifyClient("id", "secret", "uri")


@patch("spotify_client.SpotifyOAuth", autospec=True)
@patch("spotify_client.spotipy.Spotify", autospec=True)
def test_spotify_client_init_spotipy_auth_failure(mock_spotify_class, mock_oauth_class):
    """Test ConnectionError if spotipy.Spotify authentication fails."""
    mock_spotify_class.side_effect = SpotifyException(
        401, -1, "Auth failed"
    )  # spotipy.Spotify(...) raises
    with pytest.raises(ConnectionError, match="Could not authenticate with Spotify"):
        SpotifyClient("id", "secret", "uri")


@patch("spotify_client.SpotifyOAuth", autospec=True)
@patch("spotify_client.spotipy.Spotify", autospec=True)
def test_spotify_client_init_get_user_id_fails(mock_spotify_class, mock_oauth_class):
    """Test ConnectionError if _get_user_id returns None during init."""
    mock_spotify_instance = mock_spotify_class.return_value
    mock_spotify_instance.current_user.return_value = (
        None  # _get_user_id will return None
    )

    with pytest.raises(
        ConnectionError, match="Failed to retrieve Spotify User ID after authentication"
    ):
        SpotifyClient("id", "secret", "uri")


# _get_user_id Tests (testing this private method more directly for clarity)
def test_get_user_id_success(spotify_client_instance, mock_spotipy_spotify):
    # spotify_client_instance already has .sp mocked by mock_spotipy_spotify
    # _get_user_id is called during its __init__
    # We can also call it again to test its isolated behavior if needed,
    # or re-configure the mock for current_user for this specific test.
    _, mock_sp = mock_spotipy_spotify
    mock_sp.current_user.return_value = {
        "id": "another_user",
        "display_name": "Another",
    }
    assert spotify_client_instance._get_user_id() == "another_user"  # Call it directly
    mock_sp.current_user.assert_called()  # current_user was called


def test_get_user_id_api_error(spotify_client_instance, mock_spotipy_spotify):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.current_user.side_effect = SpotifyException(500, -1, "Server error")
    assert spotify_client_instance._get_user_id() is None


# search_track Tests
@patch("spotify_client.time.sleep")  # Mock time.sleep to speed up tests
def test_search_track_success_targeted(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.search.return_value = {"tracks": {"items": [SPOTIFY_SEARCH_RESULT_ITEM_1]}}

    result_track, score = spotify_client_instance.search_track(
        SAMPLE_YOUTUBE_SONG_PARSED
    )

    assert isinstance(result_track, SpotifyTrack)
    assert result_track.name == "SongX Matched"
    assert score >= spotify_client_instance.fuzzy_match_threshold
    mock_sp.search.assert_called_once_with(
        q=f"track:{SAMPLE_YOUTUBE_SONG_PARSED.parsed_song_name} artist:{SAMPLE_YOUTUBE_SONG_PARSED.parsed_artist}",
        type="track",
        limit=10,
    )
    mock_sleep.assert_called_once_with(
        2
    )  # Check the small delay after processing results


@patch("spotify_client.time.sleep")
def test_search_track_success_broader_search(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    # Simulate targeted search returning no results, then broader search succeeding
    mock_sp.search.side_effect = [
        {"tracks": {"items": []}},  # Result of targeted search
        {
            "tracks": {"items": [SPOTIFY_SEARCH_RESULT_ITEM_1]}
        },  # Result of broader search
    ]

    result_track, score = spotify_client_instance.search_track(
        SAMPLE_YOUTUBE_SONG_PARSED
    )

    assert isinstance(result_track, SpotifyTrack)
    assert result_track.name == "SongX Matched"
    assert mock_sp.search.call_count == 2
    targeted_query = f"track:{SAMPLE_YOUTUBE_SONG_PARSED.parsed_song_name} artist:{SAMPLE_YOUTUBE_SONG_PARSED.parsed_artist}"
    broader_query = f"{SAMPLE_YOUTUBE_SONG_PARSED.parsed_artist} {SAMPLE_YOUTUBE_SONG_PARSED.parsed_song_name}".strip()
    expected_calls = [
        call(q=targeted_query, type="track", limit=10),
        call(q=broader_query, type="track", limit=10),
    ]
    mock_sp.search.assert_has_calls(expected_calls)
    # Check that time.sleep(2) was called before the broader search
    # And time.sleep(2) was called at the end.
    assert mock_sleep.call_count == 2
    assert call(2) in mock_sleep.call_args_list  # Delay before broader search
    assert call(2) in mock_sleep.call_args_list  # Final delay


@patch("spotify_client.time.sleep")
def test_search_track_no_results_after_both_searches(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.search.side_effect = [
        {"tracks": {"items": []}},  # Targeted
        {"tracks": {"items": []}},  # Broader
    ]
    assert spotify_client_instance.search_track(SAMPLE_YOUTUBE_SONG_PARSED) is None
    assert mock_sp.search.call_count == 2


@patch("spotify_client.time.sleep")
def test_search_track_below_threshold(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.search.return_value = {
        "tracks": {"items": [SPOTIFY_SEARCH_RESULT_ITEM_2_LOW_SCORE]}
    }
    # Set threshold high for this test
    spotify_client_instance.fuzzy_match_threshold = 95

    assert spotify_client_instance.search_track(SAMPLE_YOUTUBE_SONG_PARSED) is None
    spotify_client_instance.fuzzy_match_threshold = (
        config.FUZZY_MATCH_THRESHOLD
    )  # Reset


@patch("spotify_client.time.sleep")
def test_search_track_missing_parsed_song_name(mock_sleep, spotify_client_instance):
    assert spotify_client_instance.search_track(SAMPLE_YOUTUBE_SONG_NO_NAME) is None
    mock_sleep.assert_not_called()  # No API call should be made, so no sleeps


@patch("spotify_client.time.sleep")
def test_search_track_api_error_targeted(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.search.side_effect = SpotifyException(500, -1, "Targeted search error")
    # Broader search should still be attempted. To test return None here, make broader also fail.
    # For now, let's assume it proceeds to broader if targeted fails with API error
    # Let's make broader search succeed
    mock_sp.search.side_effect = [
        SpotifyException(500, -1, "Targeted search error"),
        {"tracks": {"items": [SPOTIFY_SEARCH_RESULT_ITEM_1]}},
    ]
    result_track, _ = spotify_client_instance.search_track(SAMPLE_YOUTUBE_SONG_PARSED)
    assert result_track is not None
    assert mock_sp.search.call_count == 2


@patch("spotify_client.time.sleep")
def test_search_track_api_error_broader(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.search.side_effect = [
        {"tracks": {"items": []}},  # Targeted returns no items
        SpotifyException(500, -1, "Broader search error"),  # Broader search fails
    ]
    assert spotify_client_instance.search_track(SAMPLE_YOUTUBE_SONG_PARSED) is None
    assert mock_sp.search.call_count == 2


# create_or_get_playlist Tests
def test_create_or_get_playlist_exists(spotify_client_instance, mock_spotipy_spotify):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.current_user_playlists.return_value = {
        "items": [
            SPOTIFY_USER_PLAYLIST_ITEM_EXISTING,
            SPOTIFY_USER_PLAYLIST_ITEM_OTHER,
        ],
        "total": 2,
    }
    playlist_id = spotify_client_instance.create_or_get_playlist("MyTestPlaylist")
    assert playlist_id == "existing_playlist_id"
    mock_sp.current_user_playlists.assert_called_once_with(limit=50, offset=0)
    mock_sp.user_playlist_create.assert_not_called()


def test_create_or_get_playlist_creates_new(
    spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.current_user_playlists.return_value = {
        "items": [],
        "total": 0,
    }  # No playlists exist
    mock_sp.user_playlist_create.return_value = {"id": "new_playlist_id_123"}

    playlist_id = spotify_client_instance.create_or_get_playlist(
        "NewUniquePlaylist", public=False, description="Desc"
    )

    assert playlist_id == "new_playlist_id_123"
    mock_sp.current_user_playlists.assert_called_once_with(limit=50, offset=0)
    mock_sp.user_playlist_create.assert_called_once_with(
        user=spotify_client_instance.user_id,
        name="NewUniquePlaylist",
        public=False,
        description="Desc",
    )


def test_create_or_get_playlist_pagination(
    spotify_client_instance, mock_spotipy_spotify
):
    """Test playlist finding with pagination."""
    _, mock_sp = mock_spotipy_spotify
    # Simulate playlist found on the second page
    mock_sp.current_user_playlists.side_effect = [
        {
            "items": [SPOTIFY_USER_PLAYLIST_ITEM_OTHER] * 50,
            "total": 100,
            "offset": 0,
        },  # Page 1
        {
            "items": [SPOTIFY_USER_PLAYLIST_ITEM_EXISTING],
            "total": 100,
            "offset": 50,
        },  # Page 2
    ]
    playlist_id = spotify_client_instance.create_or_get_playlist("MyTestPlaylist")
    assert playlist_id == "existing_playlist_id"
    assert mock_sp.current_user_playlists.call_count == 2
    expected_calls = [call(limit=50, offset=0), call(limit=50, offset=50)]
    mock_sp.current_user_playlists.assert_has_calls(expected_calls)


def test_create_or_get_playlist_api_error(
    spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    mock_sp.current_user_playlists.side_effect = SpotifyException(500, -1, "API error")
    assert spotify_client_instance.create_or_get_playlist("AnyName") is None


# add_tracks_to_playlist Tests
@patch("spotify_client.time.sleep")
def test_add_tracks_to_playlist_empty_list(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    assert spotify_client_instance.add_tracks_to_playlist("pid", []) is True
    mock_sp.playlist_add_items.assert_not_called()
    mock_sleep.assert_not_called()


@patch("spotify_client.time.sleep")
def test_add_tracks_to_playlist_single_batch(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    track_uris = ["uri1", "uri2"]
    assert (
        spotify_client_instance.add_tracks_to_playlist("playlist1", track_uris) is True
    )
    mock_sp.playlist_add_items.assert_called_once_with(
        playlist_id="playlist1", items=track_uris
    )
    mock_sleep.assert_not_called()  # No sleep for single batch if num_batches > 1 condition


@patch("spotify_client.time.sleep")
def test_add_tracks_to_playlist_multiple_batches(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    # Create 105 track URIs to force two batches (100, 5)
    track_uris = [f"spotify:track:id{i}" for i in range(105)]

    # Ensure SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST is as expected for this test
    original_max_tracks = config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST
    config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST = (
        100  # Explicitly set for test predictability
    )

    assert (
        spotify_client_instance.add_tracks_to_playlist("playlist_multi", track_uris)
        is True
    )

    assert mock_sp.playlist_add_items.call_count == 2

    mock_sleep.assert_has_calls([call(2), call(2)], any_order=True)

    config.SPOTIFY_MAX_TRACKS_PER_ADD_REQUEST = original_max_tracks


@patch("spotify_client.time.sleep")
def test_add_tracks_to_playlist_api_error_in_batch(
    mock_sleep, spotify_client_instance, mock_spotipy_spotify
):
    _, mock_sp = mock_spotipy_spotify
    track_uris = ["uri1", "uri2"]
    mock_sp.playlist_add_items.side_effect = SpotifyException(
        500, -1, "Failed to add batch"
    )

    assert (
        spotify_client_instance.add_tracks_to_playlist("playlist_err", track_uris)
        is False
    )
    mock_sp.playlist_add_items.assert_called_once()
