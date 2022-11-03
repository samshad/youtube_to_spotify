import os
import json

import spotipy
from spotipy.oauth2 import SpotifyOAuth


sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=os.getenv('client_id'),
                                               client_secret=os.getenv('client_secret'),
                                               redirect_uri=os.getenv('redirect_uri'),
                                               scope="playlist-modify-public"))

with open("../data/all_songs.json", "r", encoding='utf-8') as f:
    songs = json.load(f)

songs_uri = []
songs_not_found = []


'''get uri of songs'''
def get_uri():
    for song in songs['items']:
        title = song['snippet']['title'].lower()
        title = title.replace('lyrics', '')
        title = title.replace('official video', '')
        title = title.replace('()', '').strip()

        result = sp.search(q=title, limit=1)

        if result['tracks']['items']:
            songs_uri.append(result['tracks']['items'][0]['uri'])
        else:
            songs_not_found.append(title)


if __name__ == '__main__':
    get_uri()

    sp.user_playlist_create(user=os.getenv('username'), name='Solitude', public=True)
    playlists = sp.user_playlists(user=os.getenv('username'))
    playlist_id = playlists['items'][0]['id']

    for i in range(0, len(songs_uri), 90):
        print(f'Adding songs {i} to {i+90}')
        sp.playlist_add_items(playlist_id=playlist_id, items=songs_uri[i:i+90])

    # sp.user_playlist_add_tracks(user=os.getenv('username'), playlist_id=playlist_id, tracks=songs_uri, position=None)

    if songs_not_found:
        songs_404 = {'songs': songs_not_found}

        with open("../data/songs_404.json", "w", encoding='utf-8') as f:
            json.dump(songs_404, f, indent=4)
