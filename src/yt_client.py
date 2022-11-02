import os
import json

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors


'''init api client'''
def init_api_client():
    # Disable OAuthlib's HTTPS verification when running locally.
    # *DO NOT* leave this option enabled in production.
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "0"
    scopes = ["https://www.googleapis.com/auth/youtube.readonly"]

    api_service_name = "youtube"
    api_version = "v3"
    client_secrets_file = "../cred/yt_client_secret.json" # yt_client_secret.json file path

    # Get credentials and create an API client
    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, scopes)
    credentials = flow.run_console()
    youtube = googleapiclient.discovery.build(
        api_service_name, api_version, credentials=credentials)

    return youtube


'''get all the playlists'''
def get_playlists(yt):
    request = yt.playlists().list(
        part="snippet,contentDetails",
        maxResults=25,
        mine=True
    )
    response = request.execute()

    print(response)


'''get items from next page'''
def get_nextpage_items(yt, playlist_id, next_page_token):
    request = yt.playlistItems().list(
        part="snippet,contentDetails",
        pageToken=next_page_token,
        maxResults=50,
        playlistId=playlist_id
    )
    return request.execute()


'''get specified numbers of playlist items'''
def get_playlist_items(yt, playlist_id):
    all_items = []
    request = yt.playlistItems().list(
        part="snippet,contentDetails",
        maxResults=50,
        playlistId=playlist_id
    )
    response = request.execute()
    all_items += response['items']

    if response.get('nextPageToken'):
        while response.get('nextPageToken'):
            response = get_nextpage_items(yt, playlist_id, response['nextPageToken'])
            all_items += response['items']

    # store data as preference, I'm using json
    data = {'items': all_items}

    with open("../data/playlist_items.json", "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4)


if __name__ == "__main__":
    # pass playlist id to get playlist items
    get_playlist_items(init_api_client(), os.getenv('playlist_id'))
    print("successfully done!")
