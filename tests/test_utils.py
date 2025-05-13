# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Unit tests for the Utils module.
# -----------------------------------------------------------------------------

import pytest
from unittest.mock import patch, MagicMock
import logging

import utils
import config
import sys


# --- Tests for clean_youtube_title ---


@pytest.mark.parametrize(
    "original_title, expected_cleaned_title",
    [
        ("Artist - Song (Official Music Video) [HD]", "Artist - Song"),
        ("My Awesome Song (Lyrics Video) #Pop #Rock", "My Awesome Song"),
        ("Track Title (feat. Guest Artist) (prod. by Producer)", "Track Title"),
        ("Song Name (Official Audio) | Visualizer", "Song Name"),
        ("Live Performance (Live at Venue)", "Live Performance"),
        ("Cool Song (Full Album Version)", "Cool Song"),
        (
            "  Some Song with Spaces   ",
            "Some Song with Spaces",
        ),  # Stripping is done at the very end
        ("Artist - Song - Part 2 (Remastered)", "Artist - Song - Part 2 (Remastered)"),
        # Assuming "Remastered" isn't in patterns
        ("NoSuffixesHere", "NoSuffixesHere"),
        ("", ""),  # Empty string
        (
            "Artist - Song (weird suffix not in list)",
            "Artist - Song (weird suffix not in list)",
        ),
        ("Song Title (Soundtrack Version)", "Song Title"),
        (
            " leading spaces - Artist - Song - trailing spaces ",
            "leading spaces - Artist - Song - trailing spaces",
        ),
        ("Artist | Song | Extra (Official)", "Artist | Song | Extra"),
        ("Artist - Song (ft. Someone) (HD)", "Artist - Song"),
        ("Artist - Song (HQ) [4K]", "Artist - Song"),
        (
            'Song (From "Movie") (Audio)',
            'Song (From "Movie")',
        ),  # (Audio) removed, inner quote remains
    ],
)
def test_clean_youtube_title(original_title, expected_cleaned_title):
    """Test clean_youtube_title with various inputs."""
    assert utils.clean_youtube_title(original_title) == expected_cleaned_title


# --- Tests for parse_artist_song_from_title ---


@patch("utils.get_artist_title")  # Patch the imported name within the utils module
def test_parse_artist_song_from_title_with_library_success(mock_get_artist_title):
    """Test parsing when youtube_title_parse.get_artist_title returns a valid result."""
    mock_get_artist_title.return_value = ("Library Artist", "Library Song")

    cleaned_title = "Some Cleaned Title"  # Input to our function
    channel_title = "Some Channel"

    artist, song = utils.parse_artist_song_from_title(cleaned_title, channel_title)

    mock_get_artist_title.assert_called_once_with(cleaned_title)
    assert artist == "Library Artist"
    assert song == "Library Song"


@patch("utils.get_artist_title")
def test_parse_artist_song_from_title_with_library_short_parts_fallback(
    mock_get_artist_title,
):
    """Test fallback when library returns short artist/song names."""
    mock_get_artist_title.return_value = ("L", "S")  # Short parts

    cleaned_title = "Actual Full Cleaned Title"
    channel_title = "Artist Channel VEVO"

    artist, song = utils.parse_artist_song_from_title(cleaned_title, channel_title)

    mock_get_artist_title.assert_called_once_with(cleaned_title)
    # Expect fallback logic to be used
    assert song == "Actual Full Cleaned Title"
    assert artist == "Artist Channel"  # Channel title cleaned


@patch("utils.get_artist_title")
def test_parse_artist_song_from_title_library_returns_none(mock_get_artist_title):
    """Test parsing when youtube_title_parse.get_artist_title returns None."""
    mock_get_artist_title.return_value = None

    cleaned_title = "This Title Is Not Parsable By Library"
    channel_title = "Fallback Channel Records"

    artist, song = utils.parse_artist_song_from_title(cleaned_title, channel_title)

    mock_get_artist_title.assert_called_once_with(cleaned_title)
    # Expect fallback logic
    assert song == "This Title Is Not Parsable By Library"
    assert artist == "Fallback Channel"  # Channel title cleaned


@patch("utils.get_artist_title")
def test_parse_artist_song_from_title_no_channel_title_fallback(mock_get_artist_title):
    """Test fallback when library fails and no channel title is provided."""
    mock_get_artist_title.return_value = None

    cleaned_title = "Only Song Title Here"

    artist, song = utils.parse_artist_song_from_title(
        cleaned_title, None
    )  # No channel title

    mock_get_artist_title.assert_called_once_with(cleaned_title)
    assert song == "Only Song Title Here"
    assert artist is None  # Artist should be None


def test_parse_artist_song_from_title_empty_cleaned_title():
    """Test with an empty cleaned_title string."""
    artist, song = utils.parse_artist_song_from_title("", "Some Channel")
    assert artist is None
    assert song is None


@patch("utils.get_artist_title")
def test_parse_artist_song_from_title_final_stripping(mock_get_artist_title):
    """Test that final stripping is applied to artist and song."""
    mock_get_artist_title.return_value = ("  Library Artist  ", "  Library Song  ")

    artist, song = utils.parse_artist_song_from_title("Anything", "Anything")
    assert artist == "Library Artist"
    assert song == "Library Song"

    # Test fallback stripping
    mock_get_artist_title.return_value = None
    artist_fallback, song_fallback = utils.parse_artist_song_from_title(
        "  Fallback Song Title  ", "  Fallback Artist Channel VEVO  "
    )
    assert song_fallback == "Fallback Song Title"
    assert artist_fallback == "Fallback Artist Channel"


# Test for "SongB by ArtistB" case using the actual library (if desired, or mock it)
# This test depends on how youtube_title_parse actually handles this.
# For a true unit test of *our* logic, we should continue mocking get_artist_title
@patch("utils.get_artist_title")
def test_parse_artist_song_from_title_song_by_artist_format(mock_get_artist_title):
    """Test 'Song by Artist' format assuming library handles it or we test fallback."""
    # Scenario 1: Library handles it perfectly
    mock_get_artist_title.return_value = ("ArtistB", "SongB")
    artist, song = utils.parse_artist_song_from_title(
        "SongB by ArtistB", "ArtistB Official"
    )
    assert artist == "ArtistB"
    assert song == "SongB"
    mock_get_artist_title.assert_called_with("SongB by ArtistB")
    mock_get_artist_title.reset_mock()  # Reset for next scenario

    # Scenario 2: Library fails, our fallback should use channel
    mock_get_artist_title.return_value = None
    artist, song = utils.parse_artist_song_from_title(
        "SongB by ArtistB", "ArtistB Official"
    )
    assert song == "SongB by ArtistB"  # Our fallback logic
    assert artist == "ArtistB"  # Our fallback logic using cleaned channel
    mock_get_artist_title.assert_called_with("SongB by ArtistB")


# --- Tests for ensure_data_directory_exists ---


@patch("config.DATA_DIR")  # Mock the DATA_DIR Path object itself
def test_ensure_data_directory_exists_creates_dir(mock_data_dir_path_obj):
    """Test that mkdir is called if directory does not exist."""
    # mock_data_dir_path_obj is now a MagicMock replacing config.DATA_DIR
    # We configure its methods like mkdir
    mock_data_dir_path_obj.mkdir.return_value = (
        None  # mkdir doesn't return anything significant
    )

    utils.ensure_data_directory_exists()

    mock_data_dir_path_obj.mkdir.assert_called_once_with(parents=True, exist_ok=True)


@patch("config.DATA_DIR")
@patch.object(logging.getLoggerClass(), "error")  # Patch the logger's error method
def test_ensure_data_directory_exists_handles_os_error(
    mock_logger_error, mock_data_dir_path_obj
):
    """Test that OSError during mkdir is caught, logged, and re-raised."""
    mock_data_dir_path_obj.mkdir.side_effect = OSError("Test OS Error")

    with pytest.raises(OSError, match="Test OS Error"):
        utils.ensure_data_directory_exists()

    mock_logger_error.assert_called_once()
    # Check parts of the log message if necessary
    # args, _ = mock_logger_error.call_args
    # assert "Could not create data directory" in args[0]


# --- Tests for setup_logging (Basic) ---
# Full testing of logging is complex. We'll do a basic check.
@patch("utils.ensure_data_directory_exists")  # Mock dependency
@patch("logging.FileHandler")
@patch("logging.StreamHandler")
@patch("logging.getLogger")  # Mock getLogger to get a mock root logger
def test_setup_logging_runs_and_configures_handlers(
    mock_getLogger, mock_StreamHandler, mock_FileHandler, mock_ensure_data_dir
):
    """Test that setup_logging runs, attempts to add handlers."""
    mock_root_logger = MagicMock()
    mock_getLogger.return_value = mock_root_logger  # When logging.getLogger() is called

    # For the hasattr(console_handler.stream, "reconfigure") part
    mock_console_stream = MagicMock()
    mock_console_stream.reconfigure = MagicMock()  # Make reconfigure a callable mock
    mock_StreamHandler.return_value.stream = mock_console_stream

    utils.setup_logging()

    mock_ensure_data_dir.assert_called_once()
    mock_FileHandler.assert_called_once_with(
        config.APP_ERROR_LOG_FILE, encoding="utf-8"
    )
    mock_StreamHandler.assert_called_once_with(sys.stdout)

    # Check that handlers were added to the (mocked) root logger
    assert mock_root_logger.addHandler.call_count >= 2  # At least File and Stream
    # Could also check specific calls if needed:
    # mock_root_logger.addHandler.assert_any_call(mock_FileHandler.return_value)
    # mock_root_logger.addHandler.assert_any_call(mock_StreamHandler.return_value)

    if hasattr(
        sys.stdout, "reconfigure"
    ):  # Only assert reconfigure if the real sys.stdout has it
        mock_console_stream.reconfigure.assert_called_once_with(encoding="utf-8")
    else:
        mock_console_stream.reconfigure.assert_not_called()
