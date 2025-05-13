# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Unit tests for the Models module.
# -----------------------------------------------------------------------------

import pytest
from pydantic import ValidationError

from models import YouTubeSong, SpotifyTrack, MigrationResult

# --- Tests for YouTubeSong ---


def test_youtube_song_valid_data():
    """Test creating YouTubeSong with valid data."""
    data = {
        "video_id": "dQw4w9WgXcQ",
        "original_title": "Rick Astley - Never Gonna Give You Up (Official Music Video)  ",  # Note trailing space
        "channel_title": "RickAstleyVEVO",
        "parsed_artist": "Rick Astley",
        "parsed_song_name": "Never Gonna Give You Up",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    }
    song = YouTubeSong(**data)
    assert song.video_id == "dQw4w9WgXcQ"
    # Check str_strip_whitespace effect (Pydantic v2 uses str_strip_whitespace in ConfigDict)
    assert (
        song.original_title
        == "Rick Astley - Never Gonna Give You Up (Official Music Video)"
    )
    assert song.channel_title == "RickAstleyVEVO"
    assert song.parsed_artist == "Rick Astley"
    assert song.parsed_song_name == "Never Gonna Give You Up"
    assert str(song.video_url) == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_youtube_song_missing_required_fields():
    """Test YouTubeSong raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError) as excinfo:
        YouTubeSong(
            original_title="A title",
            channel_title="A channel",
            video_url="https://example.com",
        )
    # Check that 'video_id' is mentioned in the error details
    assert "video_id" in str(excinfo.value).lower()
    assert "field required" in str(excinfo.value).lower()

    with pytest.raises(ValidationError):
        YouTubeSong(
            video_id="123", channel_title="A channel", video_url="https://example.com"
        )  # Missing original_title
    with pytest.raises(ValidationError):
        YouTubeSong(
            video_id="123", original_title="A title", video_url="https://example.com"
        )  # Missing channel_title
    with pytest.raises(ValidationError):
        YouTubeSong(
            video_id="123", original_title="A title", channel_title="A channel"
        )  # Missing video_url


def test_youtube_song_invalid_url():
    """Test YouTubeSong raises ValidationError for invalid video_url."""
    data = {
        "video_id": "123",
        "original_title": "A title",
        "channel_title": "A channel",
        "video_url": "not-a-valid-url",  # Invalid HttpUrl
    }
    with pytest.raises(ValidationError) as excinfo:
        YouTubeSong(**data)
    assert "video_url" in str(excinfo.value).lower()
    # Pydantic v2 error messages for URL might be more specific
    assert "url" in str(excinfo.value).lower()  # Check for general URL related error


# --- Tests for SpotifyTrack ---


def test_spotify_track_valid_data():
    """Test creating SpotifyTrack with valid data."""
    data = {
        "uri": "spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        "name": "  Never Gonna Give You Up  ",  # Test stripping
        "artists": ["Rick Astley"],
        "spotify_id": "4uLU6hMCjMI75M1A2tKUQC",
        "album_name": "Whenever You Need Somebody",
        "duration_ms": 212000,
        "external_url": "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
    }
    track = SpotifyTrack(**data)
    assert track.uri == "spotify:track:4uLU6hMCjMI75M1A2tKUQC"
    assert track.name == "Never Gonna Give You Up"  # Stripped
    assert track.artists == ["Rick Astley"]
    assert track.spotify_id == "4uLU6hMCjMI75M1A2tKUQC"
    assert track.album_name == "Whenever You Need Somebody"
    assert track.duration_ms == 212000
    assert (
        str(track.external_url)
        == "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC"
    )


def test_spotify_track_optional_fields_none():
    """Test SpotifyTrack with optional fields being None."""
    data = {
        "uri": "spotify:track:valid",
        "name": "A Song",
        "artists": ["An Artist"],
        "spotify_id": "valid_id",
        # album_name, duration_ms, external_url are optional
    }
    track = SpotifyTrack(**data)
    assert track.album_name is None
    assert track.duration_ms is None
    assert track.external_url is None


def test_spotify_track_missing_required_fields():
    """Test SpotifyTrack raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError):
        SpotifyTrack(name="A Song", artists=["Artist"], spotify_id="id")  # Missing uri
    with pytest.raises(ValidationError):
        SpotifyTrack(uri="uri", artists=["Artist"], spotify_id="id")  # Missing name
    # ... test other required fields


# --- Tests for MigrationResult ---


@pytest.fixture
def sample_yt_song_instance():
    """Provides a valid YouTubeSong instance for MigrationResult tests."""
    return YouTubeSong(
        video_id="yt123",
        original_title="YT Song",
        channel_title="YT Channel",
        video_url="https://youtube.com/watch?v=yt123",
    )


@pytest.fixture
def sample_sp_track_instance():
    """Provides a valid SpotifyTrack instance for MigrationResult tests."""
    return SpotifyTrack(
        uri="sp:track:sp123",
        name="SP Song",
        artists=["SP Artist"],
        spotify_id="sp123",
        external_url="https://open.spotify.com/track/sp123",
    )


def test_migration_result_success_valid(
    sample_yt_song_instance, sample_sp_track_instance
):
    """Test MigrationResult for a successful migration with valid data."""
    data = {
        "youtube_song": sample_yt_song_instance,
        "spotify_track": sample_sp_track_instance,
        "match_score": 95,
        "status": "SUCCESS",
        "message": "Migrated successfully",
    }
    result = MigrationResult(**data)
    assert result.youtube_song == sample_yt_song_instance
    assert result.spotify_track == sample_sp_track_instance
    assert result.match_score == 95
    assert result.status == "SUCCESS"
    assert result.message == "Migrated successfully"


def test_migration_result_not_found_valid(sample_yt_song_instance):
    """Test MigrationResult for a 'not found' case."""
    data = {
        "youtube_song": sample_yt_song_instance,
        # spotify_track is Optional, so can be None
        "match_score": None,  # Optional
        "status": "NOT_FOUND",
        "message": "Song not found on Spotify.",
    }
    result = MigrationResult(**data)
    assert result.youtube_song == sample_yt_song_instance
    assert result.spotify_track is None
    assert result.match_score is None
    assert result.status == "NOT_FOUND"
    assert result.message == "Song not found on Spotify."


def test_migration_result_missing_required_fields(
    sample_yt_song_instance, sample_sp_track_instance
):
    """Test MigrationResult raises ValidationError for missing required fields."""
    with pytest.raises(ValidationError) as excinfo_missing_yt:
        MigrationResult(spotify_track=sample_sp_track_instance, status="SUCCESS")
    assert "youtube_song" in str(excinfo_missing_yt.value).lower()

    with pytest.raises(ValidationError) as excinfo_missing_status:
        MigrationResult(youtube_song=sample_yt_song_instance)
    assert "status" in str(excinfo_missing_status.value).lower()


def test_migration_result_invalid_match_score(sample_yt_song_instance):
    """Test MigrationResult validates match_score constraints (ge=0, le=100)."""
    valid_data_base = {"youtube_song": sample_yt_song_instance, "status": "SUCCESS"}
    # Valid scores
    MigrationResult(**valid_data_base, match_score=0)
    MigrationResult(**valid_data_base, match_score=100)
    MigrationResult(**valid_data_base, match_score=50)

    # Invalid scores
    with pytest.raises(ValidationError) as excinfo_low:
        MigrationResult(**valid_data_base, match_score=-10)
    assert "match_score" in str(excinfo_low.value).lower()
    # Pydantic v2 error message for ge/le is usually like "Input should be greater than or equal to 0"
    assert "greater than or equal to 0" in str(excinfo_low.value).lower()

    with pytest.raises(ValidationError) as excinfo_high:
        MigrationResult(**valid_data_base, match_score=101)
    assert "match_score" in str(excinfo_high.value).lower()
    assert "less than or equal to 100" in str(excinfo_high.value).lower()


def test_models_str_strip_whitespace_config():
    """Test the str_strip_whitespace config works for string fields."""
    yt_song = YouTubeSong(
        video_id=" test ",  # Input with spaces
        original_title="  A Title  ",  # Input with spaces
        channel_title=" A Channel  ",  # Input with spaces
        video_url="https://example.com/path",  # HttpUrl is not a simple str for this config
    )
    assert yt_song.video_id == "test"  # Expect stripped
    assert yt_song.original_title == "A Title"  # Expect stripped
    assert yt_song.channel_title == "A Channel"  # Expect stripped
    # For HttpUrl, stripping behavior is more nuanced and generally applies to the input string before URL parsing.
    # The path itself usually isn't stripped unless it has leading/trailing whitespace *within* the path segment.
    assert str(yt_song.video_url) == "https://example.com/path"
