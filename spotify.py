import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv
import json
import errno

# to install librairies :

# pip install -r requirements.txt

# also need to replace whats in the example.env and renaming it to just ".env"

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

    max = len(tracks) - len(data["tracks"])
    print(f'Old data : {len(data["tracks"])}\nNew data : {len(tracks)}')
    i = 1
    tid = []
    changed = False
    for x in tracks:
        tid.append(x["track"]["id"])
        if x["track"]["id"] in data["tracks"]:
            continue
        changed = True
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

    for x, v in data["tracks"].copy().items():
        if x not in tid:
            changed = True
            print(f"removed {v['track']['name']}")
            data["tracks"].pop(x)
            # del data["tracks"][x]

    if changed:
        with open(jsfile, 'w+', encoding='utf-8') as outfile:
            outfile.truncate(0)
            json.dump(data, outfile)


def printtoexcel(data):
    headers = []
    content = []
    for trackid, trackdata in data["tracks"].items():
        line = ""
        for k, v in trackdata.items():
            if k not in ["track", "geniusdata", "added_by", "video_thumbnail", "is_local", "available_markets"]:
                if k not in headers:
                    headers.append(k)
                line += f"{v};"
        if "added_by" not in headers:
            headers.append("added_by")
        u = data["users"][trackdata["added_by"]["id"]]["display_name"]
        line += f"{u};"
        for k, v in trackdata["track"].items():
            if k not in ["album", "artists", "external_ids", "external_urls", "is_local", "available_markets"]:
                if "track-" + k not in headers:
                    headers.append("track-" + k)
                line += f"{v};"
        if "album_id" not in headers:
            headers.append("album_id")
        u = trackdata["track"]["album"]["id"]
        line += f"{u};"
        if "album_name" not in headers:
            headers.append("album_name")
        u = data["albums"][trackdata["track"]["album"]["id"]]["name"]
        line += f"{u};"
        if "artist_name" not in headers:
            headers.append("artist_name")
        txt = ""
        for a in trackdata["track"]["artists"]:
            txt += f'{data["artists"][a["id"]]["name"]}, '
        line += f"{txt[:-2]};"

        if "artist_genres" not in headers:
            headers.append("artist_genres")
        txt = ""
        for a in trackdata["track"]["artists"]:
            if data["artists"][a["id"]]["genres"] == []:
                txt += f'No data,'
            for g in data["artists"][a["id"]]["genres"]:
                txt += f'{g},'
            txt = txt[:-1] + "/"
        line += f"{txt[:-1]};"

        if trackdata["geniusdata"] is not None:
            for k, v in trackdata["geniusdata"]["result"].items():
                if isinstance(v, dict):
                    continue
                if "genius-" + k not in headers:
                    headers.append("genius-" + k)
                if isinstance(v, list):
                    txt = ""
                    for a in v:
                        txt += f'{a},'
                    line += f"{txt[:-1]};"
                else:
                    line += f"{v};"

        content.append(line)
    with open("output.csv", "w+", encoding='utf-8') as outfile:
        outfile.truncate(0)
        outfile.write(";".join(headers) + "\n")
        for l in content:
            outfile.write(f"{l}\n")


file = "experience_sociale.json"

playlistdict = load_data(file)
update_data(playlistdict, "https://open.spotify.com/playlist/7a32HegwUvzeauTv3wLBjj", file)
printtoexcel(playlistdict)
