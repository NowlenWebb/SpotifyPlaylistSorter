# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# [START gae_python38_render_template]
# [START gae_python3_render_template]
import datetime
import json
import constants
import random
import requests

from flask import Flask, render_template
from flask import Flask, request, redirect
from google.cloud import datastore

app = Flask(__name__)
client = datastore.Client()
  
@app.route('/')
def root():
    return render_template('index.html')

@app.route('/toSpotify')
def toSpotify(): #This Function is for authentication
    info = datastore.entity.Entity(key=client.key(constants.info))
    info_key = client.key("info", "my_key")    
    info = datastore.Entity(key=info_key)

    url = "https://accounts.spotify.com/authorize?"
    scope = "scope=" + "playlist-read-private playlist-read-collaborative playlist-modify-public playlist-modify-private"
    response_type = "response_type=" + "code"
    state = str(random.randint(1,100000))
    redirect_uri = "redirect_uri=" + "https://playlist-sorter.wl.r.appspot.com/playlists"
    client_id = "client_id=" + ""

    full_uri = url + scope + "&" + response_type + "&" + "state=" + state + "&" + redirect_uri + "&" + client_id

    info['state'] = state

    client.put(info)

    return redirect(full_uri, code=302)

@app.route('/playlists')
def when_returning():
    info_key = client.key("info", "my_key")
    info = client.get(info_key)
    info.update({'access_code': request.args.get('code', type=str)})
    
    if info['state'] != request.args.get("state"):
        return("Error: State does not match")

    #Set Request variables
    url = 'https://accounts.spotify.com/api/token'
    my_data = { 'code': request.args.get('code', type=str),
                'client_id': '',
                'client_secret': '',
                'redirect_uri': '',
                'grant_type':'authorization_code'}

    #Make request
    r = requests.post(url, data = my_data)
    print("*Playlists* r is: ", r)
    r_json = r.json()
    print("*Playlists* r is: ", r_json)

    info.update({'access_token': r_json['access_token'], 'expires_in': r_json['expires_in'], 'refresh_token': r_json['refresh_token']})

    header = {
        "Authorization": "Bearer " + info['access_token'],
        "Content-Type": 'application/json'
    }
 
    #Make request for user info
    r2 = requests.get("https://api.spotify.com/v1/me", headers=header)
    print('*playlists* r2 is ', r2)
    r2_json = r2.json()
    print('*playlists* r2 is ', r2_json)
    info.update({'username': r2_json['display_name'], 'user_id': r2_json['id']})

    #Get user's playlists
    base_url = 'https://api.spotify.com/v1'
    r3_url = base_url + "/users/" + info['user_id'] + '/playlists' + '?limit=50'
    r3 = requests.get(url=r3_url, headers=header)
    print("*Playlists* r3 is: ", r3)
    r3_json = r3.json()
    print("*Playlists* r3_json is: ", r3_json)
    info.update({'playlists': r3_json['items']})

    client.put(info)

    return render_template('playlists.html', info=info)

@app.route('/songs/<pid>')
def show_songs(pid):
    info_key = client.key("info", "my_key")
    info = client.get(info_key)

    header = {
        "Authorization": "Bearer " + info['access_token'],
        "Content-Type": 'application/json'
    }
    print(header)    
 
    #Get user's playlist
    base_url = 'https://api.spotify.com/v1'
    r1_url = base_url + "/playlists/" + pid
    r1 = requests.get(url=r1_url, headers=header)
    print("*songs* r1 is: ", r1)
    r1_json = r1.json()
    print("*songs* r1_json is: ", r1_json)

    '''
    #get next batch of tracks
    if(r1_json['tracks']['next'] is not None):
        r2 = requests.get(url=r1_json['tracks']['next'], headers=header)
        r2_json = r2.json()
        print("From songs, r2_json is: ", r2_json)
        r1_json['tracks']['items'] = r1_json['tracks']['items'] + r2_json['items']

    #Keep grabbing next tracks till full playlist
    while r2_json['next'] is not None:
        r2 = requests.get(url=r2_json['next']+'?fields=items.track(name,id,duration_ms,album(release_date))', headers=header)
        r2_json = r2.json()
        print("From songs, r2_json is: ", r2_json)
        r1_json['tracks']['items'] = r1_json['tracks']['items'] + r2_json['items']
    '''

    info.update({'selected_playlist': r1_json})

    client.put(info)

    return render_template('songs.html', info=info)

@app.route('/results/<choice>')
def show_results(choice):
    info_key = client.key("info", "my_key")
    info = client.get(info_key)

    header = {
        "Authorization": "Bearer " + info['access_token'],
        "Content-Type": 'application/json'
    }

    id_list = info['selected_playlist']['tracks']['items'][0]['track']['id']
    for x in range(1, len(info['selected_playlist']['tracks']['items'])):
        id_list = id_list + ',' + info['selected_playlist']['tracks']['items'][x]['track']['id']

    #Get audio features for tracks in user's playlist
    base_url = 'https://api.spotify.com/v1'
    r1_url = base_url + '/audio-features?ids=' + id_list
    r1 = requests.get(url=r1_url, headers=header)
    print("*results* r1 from results: ", r1)
    r1_json = r1.json()
    print("*results* r1_json from results is: ", r1_json)

    #copy elements into audio features object
    for x in range(len(info['selected_playlist']['tracks']['items'])):
        if info['selected_playlist']['tracks']['items'][x]['track']['id'] == r1_json['audio_features'][x]['id']:
            r1_json['audio_features'][x]['name'] = info['selected_playlist']['tracks']['items'][x]['track']['name']
            r1_json['audio_features'][x]['artist'] = info['selected_playlist']['tracks']['items'][x]['track']['artists'][0]['name']
            r1_json['audio_features'][x]['duration_ms'] = info['selected_playlist']['tracks']['items'][x]['track']['duration_ms']
            r1_json['audio_features'][x]['release_date'] = info['selected_playlist']['tracks']['items'][x]['track']['album']['release_date']
            r1_json['audio_features'][x]['uri'] = info['selected_playlist']['tracks']['items'][x]['track']['uri']

    #sort playlist by option
    sorted_list = sorted(r1_json['audio_features'], key=lambda d: d[choice])

    info['sorted_playlist'] = sorted_list
    info['user_choice'] = choice

    client.put(info) 

    return render_template('results.html', info=info)

@app.route('/publish')
def publish_playlist():
    info_key = client.key("info", "my_key")
    info = client.get(info_key)

    header = {
        "Authorization": "Bearer " + info['access_token'],
        "Content-Type": 'application/json'
    }

    #Get user's playlists
    base_url = 'https://api.spotify.com/v1'
    r1_url = base_url + "/users/" + info['user_id'] + '/playlists'
    mydata = {   
        "name": "SPS - " + info['selected_playlist']['name'] + ' - ' + info['user_choice'],
        "description": str("Here is your new playlist from the Spotify Playlist Sorter by Nono. This is based of your playlist - " + info['selected_playlist']['name'] + ' - and is sorted by - ' + info['user_choice'])
    }

    print("*publish* data is: ", mydata)

    #create playlist
    r1 = requests.post(url=r1_url, headers=header, data=json.dumps(mydata))
    print("*publish* r1 is: ", r1)
    r1_json = r1.json()

    print('*publish* r1_json is ', r1_json)

    #make uri list
    uri_list = "spotify:track:" + info['sorted_playlist'][0]['id']
    for x in range(1, len(info['sorted_playlist'])):
        uri_list = uri_list + "," + "spotify:track:" + str(info['sorted_playlist'][x]['id'])
    
    r2_url = base_url + "/playlists/" + r1_json['id'] + '/tracks'
    r2 = requests.post(url=r2_url + '?uris=' + uri_list, headers=header)
    print('*publish* r2 is', r2)
    print('*publish* r2_json is ', r2.json())

    #Get new playlists
    base_url = 'https://api.spotify.com/v1'
    r3_url = base_url + "/playlists/" + r1_json['id']
    r3 = requests.get(url=r3_url, headers=header)
    print("*songs* r3 is: ", r3)
    r3_json = r3.json()
    print("*songs* r3_json is: ", r3_json)

    info['new_playlist'] = r3_json

    client.put(info)

    return render_template('publish.html', info=info)

if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.
    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
# [END gae_python3_render_template]
# [END gae_python38_render_template]

'''
list = playlist[0]
counter = 1
for x in range(1,  len(playlist)):
    if counter >= len(playlist):
        make request and append to list of song ids
        break
    if counter < 100    
        list = ',' + str(playlist[x])
        counter ++
    else:
        make request and append to list of song ids
        list = playlist[x]
        counter = 1
'''