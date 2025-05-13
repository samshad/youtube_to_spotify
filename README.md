# Youtube to Spotify Playlist Migrator

## Prerequisites

1.  **Python:** Python 3.12
2.  **Google Account & API Key:**
    *   You need a Google Cloud Project with the **YouTube Data API v3** enabled.
    *   Generate an **API Key** for your project.
    *   See: [Google Cloud Console](https://console.cloud.google.com/)
3.  **Spotify Account & Developer App:**
    *   A Spotify account (Free or Premium).
    *   Create a Spotify App in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).
    *   Note down your **Client ID** and **Client Secret**.
    *   In your Spotify App settings, add a **Redirect URI**. A common one for local development is `http://localhost:8888/callback`. Make sure the URI you set here *exactly* matches the one you put in your `.env` file.

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd youtube-to-spotify
    ```

2.  **Create a virtual environment:**
    ```bash
    # Linux / macOS
    python3 -m venv venv
    source venv/bin/activate

    # Windows (cmd/powershell)
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure API Keys (.env file):**
    *   Create a file named `.env` in the project root directory (`youtube_to_spotify/`).
    *   Add your API keys and Spotify credentials to this file. **Do NOT commit this file to Git.**

    ```env
    # youtube_to_spotify/.env

    # Get from Google Cloud Console (YouTube Data API v3 enabled)
    YOUTUBE_API_KEY="YOUR_YOUTUBE_API_KEY"

    # Get from Spotify Developer Dashboard
    SPOTIPY_CLIENT_ID="YOUR_SPOTIFY_CLIENT_ID"
    SPOTIPY_CLIENT_SECRET="YOUR_SPOTIFY_CLIENT_SECRET"
    # Must EXACTLY match one of the Redirect URIs set in Spotify Dashboard
    SPOTIPY_REDIRECT_URI="http://localhost:8888/callback"
    ```

## How to Run

1.  **Ensure your virtual environment is active.**
2.  **Run the main script from the project root directory:**
    ```bash
    python -m youtube_to_spotify.main
    ```
    Alternatively, if inside the `youtube_to_spotify` directory:
    ```bash
    python main.py
    ```

3.  **Follow the prompts:**
    *   Enter the **YouTube Playlist ID** when prompted. This is the string of characters in the playlist URL after `list=`, e.g., `PLxxxxxxxxxxxxxxxxx`.
    *   Enter the desired name for the new **Spotify playlist**. You can press Enter to accept the default name.

4.  **Spotify Authentication (First Run / Token Expired):**
    *   Your web browser should automatically open, asking you to log in to Spotify and authorize the application to access your account (based on the scopes requested).
    *   If the browser doesn't open automatically, check the console output for a URL to copy and paste manually.
    *   After authorization, you'll be redirected (likely to the `localhost` address you specified), and the script will capture the authentication token. A `.spotify_token_cache` file will be created to store the token for future runs.

5.  **Monitor Progress:** The script will log its progress to the console, including fetching songs, searching Spotify, and adding tracks.

## Output

*   **Console:** Logs showing the script's progress, found songs, cache hits/misses, and any warnings/errors.
*   **Spotify:** A new playlist (or updated existing one) in your Spotify account containing the successfully matched songs.
*   **`data/` Directory:**
    *   `youtube_songs_fetched.csv`: A record of every video fetched from the YouTube playlist, including parsed details.
    *   `successfully_migrated.csv`: Details of YouTube songs successfully matched and added to Spotify, including the Spotify track info and match score.
    *   `not_found_on_spotify.csv`: Details of YouTube songs that could not be matched on Spotify or resulted in an error during processing.
    *   `app_errors.log`: Contains logs of warnings and errors encountered during script execution (including API errors, file writing issues, etc.).

## Configuration

*   **API Keys:** Managed via the `.env` file (see Setup).
*   **Fuzzy Matching Threshold:** The minimum similarity score (0-100) required for a Spotify track to be considered a match. Can be adjusted in `config.py` (`FUZZY_MATCH_THRESHOLD`, default is 85). Lowering it may find more matches but increases the risk of incorrect matches. Increasing it makes matching stricter.

## Troubleshooting

*   **`UnicodeEncodeError` on Windows Console:** This happens when song titles contain characters your default Windows console encoding (like `cp1252`) cannot display.
    *   **Recommended Fix:** Set the `PYTHONUTF8=1` environment variable before running the script. In your terminal:
        *   CMD: `set PYTHONUTF8=1`
        *   PowerShell: `$env:PYTHONUTF8 = "1"`
        *   Run the script from the *same* terminal. Consider setting this system-wide for Python development on Windows.
    *   Using **Windows Terminal** is also recommended as it has better Unicode support.
*   **Spotify Authentication Errors:**
    *   Ensure `SPOTIPY_REDIRECT_URI` in `.env` *exactly* matches one registered in your Spotify Developer Dashboard.
    *   Verify your `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` are correct.
    *   Try deleting the `.spotify_token_cache` file in the project root to force a fresh authentication flow.
*   **Songs Not Found:**
    *   YouTube titles can be inconsistent. The parsing logic in `utils.py` might not extract the artist/song correctly for all titles.
    *   Fuzzy matching (`fuzzywuzzy`) is powerful but not perfect. Some legitimate songs might score below the threshold, or incorrect songs might score above it. Review `not_found_on_spotify.csv`.
    *   The song might genuinely not be available on Spotify.
*   **API Rate Limits:** If you process very large playlists quickly, you might encounter rate limits from YouTube or Spotify. The script includes small delays, but excessive use might require waiting.

## Limitations

*   **Public Playlists Only:** Currently uses a YouTube API Key, which generally works only for public playlists. Migrating private playlists would require implementing YouTube OAuth 2.0 authentication.
*   **Parsing Accuracy:** Extracting artist/song from YouTube titles is heuristic and may fail for unconventional titles.
*   **Matching Accuracy:** Relies on fuzzy string matching, which can sometimes lead to mismatches or missed matches. Manual review of the created Spotify playlist and the `not_found_on_spotify.csv` log is recommended.
*   **YouTube Mixes:** Does not work with YouTube auto-generated "Mix" playlists. Requires a standard playlist ID.

## License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.  
© 2025 Md Samshad Rahman

---

Happy Migrating! 🎶