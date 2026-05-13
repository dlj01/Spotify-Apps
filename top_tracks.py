import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth

import spotify


class TopTracks(spotify.Playlist):
    """Updates the three top-tracks playlists."""

    def __init__(self, playlists):
        super().__init__()
        self.scope_key   = "top_tracks"
        self.scope       = "user-top-read playlist-modify-public"
        self.spotify_url = (
            f"https://accounts.spotify.com/authorize"
            f"?client_id={self.client_id}"
            f"&response_type=code"
            f"&redirect_uri={self.redirect_uri}"
            f"&scope=user-top-read%20playlist-modify-public"
        )
        self.playlists = playlists

    def update(self):
        token       = self.getAccessToken()
        sp, pls     = self._get_sp(token)
        self._update_playlists(sp, pls)

    # ------------------------------------------------------------------

    def _get_sp(self, token):
        sp = spotipy.Spotify(
            auth=token,
            auth_manager=SpotifyOAuth(
                client_id=self.client_id,
                client_secret=self.client_secret,
                redirect_uri=self.redirect_uri,
                scope=self.scope,
                open_browser=False,
            )
        )
        return sp, sp.current_user_playlists()

    def _update_playlists(self, sp, pls):
        for plist in self.playlists:
            playlist = self.getPlaylist(pls, plist["name"])
            sp.playlist_change_details(playlist_id=playlist["id"], description=plist["desc"])
            track_uris = self._get_top_tracks(sp, plist["time_range"], plist["num_tracks"], plist["name"])
            sp.playlist_replace_items(playlist_id=playlist["id"], items=track_uris)

    def _get_top_tracks(self, sp, time_range, num_tracks, name):
        all_tracks   = []
        seen_tracks  = []
        remove_tracks = []

        while len(all_tracks) < num_tracks:
            limit  = min(num_tracks - len(all_tracks), 50)
            offset = len(all_tracks) + len(remove_tracks)
            result = sp.current_user_top_tracks(limit, offset, time_range)

            for track in result["items"]:
                song = (track["artists"][0]["name"], track["name"])
                if song in seen_tracks:
                    remove_tracks.append(track)
                else:
                    seen_tracks.append(song)

            for track in remove_tracks:
                if track in result["items"]:
                    result["items"].remove(track)

            all_tracks.extend(result["items"])

        print(name.upper())
        self.printTracks(all_tracks)
        return [t["uri"] for t in all_tracks]
