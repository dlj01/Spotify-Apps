import json
import os
import requests
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Token storage — saved to tokens.json in the project root
# ---------------------------------------------------------------------------

TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json")

def _load_tokens():
    if os.path.exists(TOKEN_PATH):
        with open(TOKEN_PATH, "r") as f:
            return json.load(f)
    return {}

def _save_tokens(data: dict):
    with open(TOKEN_PATH, "w") as f:
        json.dump(data, f)


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

CLIENT_ID     = os.environ.get("SPOTIFY_CLIENT_ID",     "b639cc95a4ae4574b11457ee2391f279")
CLIENT_SECRET = os.environ.get("SPOTIFY_CLIENT_SECRET", "12df184b9d464f7d9396f4e8adf72b61")
REDIRECT_URI  = os.environ.get("SPOTIFY_REDIRECT_URI",  "http://127.0.0.1:5000/callback")


class RedirectHandler(BaseHTTPRequestHandler):
    """Handles the local OAuth redirect (only used for the initial login)."""
    code_value = ""

    def do_GET(self):
        parsed = urlparse(self.path[1:])
        params = parse_qs(parsed.query)
        RedirectHandler.code_value = params.get("code", [""])[0]
        html = b"<html><head><script>setTimeout(()=>window.close(),500)</script></head><body></body></html>"
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(html)

    def log_message(self, format, *args):
        pass  # suppress server logs


# ---------------------------------------------------------------------------
# Base Playlist class
# ---------------------------------------------------------------------------

class Playlist:
    """Base class shared by TopTracks and Rewind."""

    def __init__(self):
        self.client_id     = CLIENT_ID
        self.client_secret = CLIENT_SECRET
        self.redirect_uri  = REDIRECT_URI
        self.spotify_url   = ""
        self.playlist_name = ""
        # Subclasses set this so each scope gets its own stored token
        self.scope_key = "default"

    # ------------------------------------------------------------------
    # Public: get a valid access token (refreshes silently when possible)
    # ------------------------------------------------------------------

    def getAccessToken(self):
        tokens      = _load_tokens()
        scope_data  = tokens.get(self.scope_key, {})
        refresh_tok = scope_data.get("refresh_token")

        if refresh_tok:
            access_token, new_refresh = self._refresh_access_token(refresh_tok)
            if access_token:
                scope_data["refresh_token"] = new_refresh or refresh_tok
                tokens[self.scope_key] = scope_data
                _save_tokens(tokens)
                return access_token

        # No stored refresh token — do the one-time browser login
        access_token, refresh_tok = self._browser_auth()
        tokens[self.scope_key] = {"refresh_token": refresh_tok}
        _save_tokens(tokens)
        return access_token

    # ------------------------------------------------------------------
    # Internal: exchange a stored refresh token for a new access token
    # ------------------------------------------------------------------

    def _refresh_access_token(self, refresh_token):
        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
                "client_id":     self.client_id,
                "client_secret": self.client_secret,
            }
        )
        data = resp.json()
        return data.get("access_token"), data.get("refresh_token")

    # ------------------------------------------------------------------
    # Internal: one-time browser auth (local server catches the redirect)
    # ------------------------------------------------------------------

    def _browser_auth(self):
        httpd = HTTPServer(("127.0.0.1", 5000), RedirectHandler)
        webbrowser.open(self.spotify_url)
        httpd.handle_request()
        httpd.server_close()

        resp = requests.post(
            "https://accounts.spotify.com/api/token",
            data={
                "grant_type":   "authorization_code",
                "code":         RedirectHandler.code_value,
                "redirect_uri": self.redirect_uri,
                "client_id":    self.client_id,
                "client_secret": self.client_secret,
            }
        )
        data = resp.json()
        return data.get("access_token"), data.get("refresh_token")

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def getPlaylist(self, playlists, name):
        for pl in playlists["items"]:
            if pl and pl["name"] == name:
                return pl

    def printTracks(self, tracks):
        for i, track in enumerate(tracks, 1):
            print(i, track["artists"][0]["name"], "–", track["name"])
