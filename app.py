import os
import threading
from datetime import datetime
from flask import Flask, redirect, request, session, jsonify, render_template_string

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
# HTML template (mobile-friendly, single file — no separate templates folder)
# ---------------------------------------------------------------------------

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Spotify Updater</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0d0d0d;
      color: #e8e6e0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }
    h1 { font-size: 22px; font-weight: 500; margin-bottom: 6px; }
    p.sub { font-size: 14px; color: #888; margin-bottom: 32px; }
    .card {
      background: #1a1a1a;
      border: 1px solid #2a2a2a;
      border-radius: 16px;
      padding: 28px 24px;
      width: 100%;
      max-width: 380px;
      text-align: center;
    }
    .btn {
      display: block;
      width: 100%;
      padding: 14px;
      border-radius: 50px;
      border: none;
      font-size: 16px;
      font-weight: 500;
      cursor: pointer;
      transition: opacity .15s;
    }
    .btn:active { opacity: .75; }
    .btn-green  { background: #1db954; color: #000; }
    .btn-gray   { background: #2a2a2a; color: #888; cursor: default; }
    .btn-link   { background: none; color: #1db954; font-size: 14px; text-decoration: underline; padding: 6px; margin-top: 12px; }
    #status {
      margin-top: 20px;
      font-size: 14px;
      color: #888;
      min-height: 20px;
    }
    .dot {
      display: inline-block;
      width: 8px; height: 8px;
      border-radius: 50%;
      background: #1db954;
      margin-right: 6px;
      animation: pulse 1.2s ease-in-out infinite;
    }
    @keyframes pulse {
      0%,100% { opacity: 1; }
      50%      { opacity: .3; }
    }
    .success { color: #1db954; }
    .error   { color: #e24b4a; }
    .playlists { margin-top: 20px; text-align: left; }
    .playlists li {
      font-size: 13px;
      color: #666;
      padding: 5px 0;
      border-bottom: 1px solid #222;
      list-style: none;
    }
    .playlists li span { color: #aaa; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Spotify Updater</h1>
    <p class="sub">Tap to refresh your playlists</p>

    {% if not authed %}
      <a href="/login" class="btn btn-green" style="text-decoration:none;display:block;padding:14px;">
        Connect Spotify
      </a>
    {% else %}
      <button class="btn btn-green" id="update-btn" onclick="triggerUpdate()">
        Update playlists
      </button>
    {% endif %}

    <div id="status">
      {% if not authed %}
        <span style="color:#666">Not connected</span>
      {% endif %}
    </div>

    <ul class="playlists">
      <li>rotation <span>– last month, 50 tracks</span></li>
      <li>mid rotation <span>– last 6 months, 100 tracks</span></li>
      <li>lost in rotation <span>– last year, 100 tracks</span></li>
    </ul>

    {% if authed %}
      <button class="btn btn-link" onclick="window.location='/logout'">Disconnect</button>
    {% endif %}
  </div>

  <script>
    function triggerUpdate() {
      const btn = document.getElementById("update-btn");
      const status = document.getElementById("status");
      btn.className = "btn btn-gray";
      btn.disabled = true;
      status.innerHTML = '<span class="dot"></span>Updating playlists…';

      fetch("/update", { method: "POST" })
        .then(r => r.json())
        .then(d => poll());
    }

    function poll() {
      fetch("/status")
        .then(r => r.json())
        .then(d => {
          const btn = document.getElementById("update-btn");
          const status = document.getElementById("status");
          if (d.running) {
            setTimeout(poll, 2000);
          } else if (d.result === "ok") {
            status.innerHTML = '<span class="success">✓ All playlists updated</span>';
            btn.className = "btn btn-green";
            btn.disabled = false;
          } else if (d.result) {
            status.innerHTML = '<span class="error">Error: ' + d.result + '</span>';
            btn.className = "btn btn-green";
            btn.disabled = false;
          }
        });
    }
  </script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    tokens = sp_module._load_tokens()
    authed = "top_tracks" in tokens
    return render_template_string(HTML, authed=authed)


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
