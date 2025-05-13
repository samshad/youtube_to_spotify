# -----------------------------------------------------------------------------
# Project: youtube_to_spotify
# Author: Md Samshad Rahman
# Year: 2025
# License: MIT License (See LICENSE file for details)
# Description: Pydantic models for representing song and track data structures.
# -----------------------------------------------------------------------------

from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class YouTubeSong(BaseModel):
    """
    Represents a song extracted from a YouTube playlist item.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    video_id: str = Field(..., description="Unique YouTube video ID.")
    original_title: str = Field(
        ..., description="The original title of the YouTube video."
    )
    channel_title: str = Field(
        ..., description="The title of the YouTube channel that uploaded the video."
    )
    parsed_artist: Optional[str] = Field(
        None, description="Artist name parsed from the title or channel."
    )
    parsed_song_name: Optional[str] = Field(
        None, description="Song name parsed from the title."
    )
    video_url: HttpUrl = Field(..., description="URL to the YouTube video.")


class SpotifyTrack(BaseModel):
    """
    Represents a track found on Spotify.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    uri: str = Field(
        ..., description="Spotify Track URI (e.g., spotify:track:TRACK_ID)."
    )
    name: str = Field(..., description="Name of the track on Spotify.")
    artists: List[str] = Field(
        ..., description="List of artist names for the track on Spotify."
    )
    spotify_id: str = Field(..., description="Spotify's unique ID for the track.")
    album_name: Optional[str] = Field(None, description="Album name, if available.")
    duration_ms: Optional[int] = Field(
        None, description="Duration of the track in milliseconds."
    )
    external_url: Optional[HttpUrl] = Field(
        None, description="URL to the track on Spotify's website."
    )


class MigrationResult(BaseModel):
    """
    Represents the result of attempting to migrate a single YouTube song to Spotify.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    youtube_song: YouTubeSong
    spotify_track: Optional[SpotifyTrack] = None
    match_score: Optional[int] = Field(
        None, ge=0, le=100, description="Fuzzy match score (0-100)."
    )
    status: str = Field(
        ...,
        description="Migration status (e.g., 'SUCCESS', 'NOT_FOUND', 'API_ERROR', 'SKIPPED').",
    )
    message: Optional[str] = Field(
        None, description="Additional details or error message."
    )


if __name__ == "__main__":
    sample_yt_song = YouTubeSong(
        video_id="dQw4w9WgXcQ",
        original_title="Rick Astley - Never Gonna Give You Up (Official Music Video)",
        channel_title="RickAstleyVEVO",
        parsed_artist="Rick Astley",
        parsed_song_name="Never Gonna Give You Up",
        video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    print("Sample YouTubeSong:", sample_yt_song.model_dump_json(indent=2))

    sample_sp_track = SpotifyTrack(
        uri="spotify:track:4uLU6hMCjMI75M1A2tKUQC",
        name="Never Gonna Give You Up",
        artists=["Rick Astley"],
        spotify_id="4uLU6hMCjMI75M1A2tKUQC",
        album_name="Whenever You Need Somebody",
        duration_ms=212,  # Placeholder
        external_url="https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
    )
    print("\nSample SpotifyTrack:", sample_sp_track.model_dump_json(indent=2))

    sample_migration_success = MigrationResult(
        youtube_song=sample_yt_song,
        spotify_track=sample_sp_track,
        match_score=95,
        status="SUCCESS",
        message=None,
    )

    print(
        "\nSample MigrationResult (Success):",
        sample_migration_success.model_dump_json(indent=2),
    )

    sample_migration_failure = MigrationResult(
        youtube_song=sample_yt_song,
        status="NOT_FOUND",
        message="No suitable match found on Spotify above threshold.",
        match_score=None,
    )

    print(
        "\nSample MigrationResult (Not Found):",
        sample_migration_failure.model_dump_json(indent=2),
    )
