import spotipy
from spotipy.oauth2 import SpotifyOAuth
from datetime import datetime, timedelta

''' modules '''
import spotify


class Rewind(spotify.Playlist):
    ''' rewind '''
    def __init__(self):
        super().__init__()
        self.spotify_url = "https://accounts.spotify.com/authorize?client_id=b639cc95a4ae4574b11457ee2391f279&response_type=code&redirect_uri=http://localhost:8080&scope=user-read-recently-played%20playlist-modify-public"
        self.playlist_name = "rewind"
        yesterday_date = datetime.now() - timedelta(days=1)
        yesterday = yesterday_date.strftime("%m/%d/%Y")
        self.description = f"Every song that I played yesterday ({yesterday})"
        self.time_range = ""
        self.num_tracks = 0

    def update(self):
        token = self.getAccessToken()
        sp, playlists = self.getRecPlaylists(token)
        self.updatePlaylist(sp, playlists)

    def getRecPlaylists(self, token):
        ''' helper function - get user playlists w/ recent tracks token '''
        sp = spotipy.Spotify(auth=token, auth_manager=SpotifyOAuth(
            client_id=self.client_id, client_secret=self.client_secret, redirect_uri=self.redirect_uri,
            scope="user-read-recently-played playlist-modify-public", open_browser=False,
        ))
        user_playlists = sp.current_user_playlists()
        return sp, user_playlists

    def updatePlaylist(self, sp, playlists):
        # get playlist
        playlist = self.getPlaylist(playlists)

        # update playlist description
        sp.playlist_change_details(playlist_id=playlist['id'], description=self.description)

        # update playlist tracks
        track_uris = self.getRecTracks(sp=sp)
        sp.playlist_replace_items(playlist_id=playlist['id'], items=track_uris)

    def getRecTracks(self, sp):
        ''' helper function - get tracks for playlist '''
        all_tracks = []
        seen_tracks = []
        remove_tracks = []

        # retrieve desired number of tracks
        now = datetime.now()
        midnight_today = datetime(now.year, now.month, now.day, 5, 0, 0)
        midnight_yesterday = midnight_today - timedelta(days=1)
        after = int(midnight_yesterday.timestamp() * 1000)
        before = int(midnight_today.timestamp() * 1000)
        print("start loop, after =", after)
        print("before =", before)
        while before > after:
            # retrieve more tracks
            #recent_tracks = sp.current_user_recently_played(limit=1, before=before)
            recent_tracks = sp.current_user_recently_played(limit=1, after=after)
            #recent_tracks['items'] = sorted(recent_tracks['items'], key=lambda x: x['played_at'], reverse=True)
            recent_tracks['items'] = sorted(recent_tracks['items'], key=lambda x: x['played_at'], reverse=False)

            # # record duplicates
            # for idx, track in enumerate(recent_tracks['items']):
            #     song = (track['track']['artists'][0]['name'], track['track']['name'])  # (artist, name) pair
            #     if song in seen_tracks:
            #         remove_tracks.append(track)
            #     else:
            #         seen_tracks.append(song)
            #
            # # remove the duplicates
            # for track in remove_tracks:
            #     if track in recent_tracks['items']:
            #         recent_tracks['items'].remove(track)

            # update list of track URIs
            for track in recent_tracks['items']:
                all_tracks.append(track)

            # reset the offset
            all_tracks = sorted(all_tracks, key=lambda x: x['played_at'], reverse=False)
            # self.printTracks(all_tracks)
            # earliest_track_time = all_tracks[-1]['played_at']
            self.printTracks(recent_tracks['items'])
            # earliest_track_time = all_tracks[-1]['played_at']
            # print("new earliest =", earliest_track_time)
            # before = int(datetime.strptime(earliest_track_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp() * 1000)
            # print("new before =", before)
            latest_track_time = all_tracks[-1]['played_at']
            # print("new latest =", latest_track_time)
            latest = datetime.strptime(latest_track_time, '%Y-%m-%dT%H:%M:%S.%fZ')
            after = int((latest - timedelta(hours=5)).timestamp() * 1000)
            print("new after =", after)

        # return track URIs
        print("REWIND")
        self.printTracks(all_tracks)
        track_uris = [track['track']['uri'] for track in all_tracks]
        return track_uris

    def printTracks(self, tracks):
        ''' helper function - print added tracks '''
        for track in tracks:
            played_time = datetime.strptime(track['played_at'], '%Y-%m-%dT%H:%M:%S.%fZ').strftime('%H:%M:%S')
            print(
                played_time,
                track['track']['artists'][0]['name'],
                " – ",
                track['track']['name']
            )
