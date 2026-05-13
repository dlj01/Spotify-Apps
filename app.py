import os
import threading
from datetime import datetime
from flask import Flask, redirect, request, session, jsonify, render_template

import spotify as sp_module
import top_tracks

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "change-me-in-production")

# ---------------------------------------------------------------------------
# Playlist definitions (same as your original update.py)
# ---------------------------------------------------------------------------

def _build_top_lists():
    current_date = datetime.now().strftime("%m/%d/%Y")
    return [
        {
            "name": "rotation",
            "desc": f"My top tracks of the last month (as of {current_date})",
            "time_range": "short_term",
            "num_tracks": 50,
        },
        {
            "name": "mid rotation",
            "desc": f"My top tracks of the last 6 months (as of {current_date})",
            "time_range": "medium_term",
            "num_tracks": 100,
        },
        {
            "name": "lost in rotation",
            "desc": f"My top tracks of the last year (as of {current_date})",
            "time_range": "long_term",
            "num_tracks": 100,
        },
    ]

# ---------------------------------------------------------------------------
# Simple in-memory job status (good enough for a single-user app)
# ---------------------------------------------------------------------------

job_status = {"running": False, "result": None}

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    tokens = sp_module._load_tokens()
    authed = "top_tracks" in tokens
    return render_template("index.html", authed=authed)


@app.route("/login")
def login():
    """Redirect the user's browser to Spotify's auth page."""
    top = top_tracks.TopTracks([])
    return redirect(top.spotify_url)


@app.route("/callback")
def callback():
    """Spotify redirects here after the user logs in. Exchange code for tokens."""
    code = request.args.get("code")
    if not code:
        return "Authorization failed — no code received.", 400

    resp = sp_module.requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  sp_module.REDIRECT_URI,
            "client_id":     sp_module.CLIENT_ID,
            "client_secret": sp_module.CLIENT_SECRET,
        }
    )
    data = resp.json()
    access_token  = data.get("access_token")
    refresh_token = data.get("refresh_token")

    if not access_token:
        return f"Token exchange failed: {data}", 400

    tokens = sp_module._load_tokens()
    tokens["top_tracks"] = {"refresh_token": refresh_token}
    sp_module._save_tokens(tokens)

    return redirect("/")


@app.route("/logout")
def logout():
    tokens = sp_module._load_tokens()
    tokens.pop("top_tracks", None)
    sp_module._save_tokens(tokens)
    return redirect("/")


@app.route("/update", methods=["POST"])
def update():
    """Kick off the playlist update in a background thread."""
    if job_status["running"]:
        return jsonify({"ok": False, "msg": "Already running"})

    job_status["running"] = True
    job_status["result"]  = None

    def run():
        try:
            top = top_tracks.TopTracks(_build_top_lists())
            top.update()
            job_status["result"] = "ok"
        except Exception as e:
            job_status["result"] = str(e)
        finally:
            job_status["running"] = False

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/status")
def status():
    return jsonify(job_status)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
