import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import json
import errno

load_dotenv()
GENIUS_CLIENT_ID = os.getenv('GENIUS_CLIENT_TOKEN')

auth_manager = SpotifyClientCredentials()
sp = spotipy.Spotify(auth_manager=auth_manager)


def load_data(filename):
    try:
        with open(filename, "r+", encoding='utf-8') as json_file:
            try:
                d = json.load(json_file)
                return d
            except:
                return {"tracks": {}, "artists": {}, "albums": {}, "users": {}}
    except FileNotFoundError:
        try:
            open(filename, "w+")
            return load_data(filename)
        except:
            try:
                os.makedirs(os.path.dirname(filename))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise
            return load_data(filename)


def request_song_info(song_title, artist_name):
    base_url = 'https://api.genius.com'
    headers = {'Authorization': 'Bearer ' + GENIUS_CLIENT_ID}
    search_url = base_url + '/search'
    d = {'q': song_title + ' ' + artist_name}
    response = requests.get(search_url, data=d, headers=headers)

    return response


def update_data(data, pl, jsfile):
    playlists = sp.playlist_tracks(pl)
    tracks = playlists['items']
    while playlists['next']:
        playlists = sp.next(playlists)
        tracks.extend(playlists['items'])

    max = len(tracks)
    i = 1
    for x in tracks:
        if x["track"]["id"] in data["tracks"]:
            continue
        u = sp.user(x["added_by"]["id"])
        print(f'{u["display_name"]} : {x["track"]["name"]} {i}/{max}')
        data["users"][x["added_by"]["id"]] = u
        for y in x["track"]["artists"]:
            artist = sp.artist(y['id'])
            data["artists"][y["id"]] = artist
            artist_name = artist["name"]
            response = request_song_info(artist_name, x["track"]["name"])
            j = response.json()
            remote_song_info = None
            for hit in j['response']['hits']:
                if artist_name.lower() in hit['result']['primary_artist']['name'].lower():
                    remote_song_info = hit
                break
            if "geniusdata" not in x or ("geniusdata" in x and remote_song_info is not None):
                x["geniusdata"] = remote_song_info
        data["albums"][x["track"]["album"]["id"]] = sp.album(x["track"]["album"]["id"])

        data["tracks"][x["track"]["id"]] = x

        i += 1
    with open(jsfile, 'w+', encoding='utf-8') as outfile:
        outfile.truncate(0)
        json.dump(data, outfile)


file = "experience_sociales.json"

playlistdict = load_data(file)
update_data(playlistdict, "https://open.spotify.com/playlist/7a32HegwUvzeauTv3wLBjj", file)
