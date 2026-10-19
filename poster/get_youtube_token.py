#!/usr/bin/env python3
"""One-time helper: get a YouTube refresh token for one channel.

Run this on YOUR computer (it opens a browser to sign in with Google). No extra packages needed.

  python3 poster/get_youtube_token.py CLIENT_ID CLIENT_SECRET

Sign in with the Google account that owns the channel (for a Brand Account channel, pick the
channel when Google asks). The script prints the refresh token and the channel it belongs to.
Paste the values into GitHub repo secrets as described in poster/SETUP.md.
"""
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
PORT = 8765


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(1)
    client_id, client_secret = sys.argv[1], sys.argv[2]
    redirect = f"http://127.0.0.1:{PORT}/"
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": client_id, "redirect_uri": redirect, "response_type": "code",
        "scope": SCOPES, "access_type": "offline", "prompt": "consent", "state": state})
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Done. You can close this tab and go back to the terminal.</h2>")

        def log_message(self, *a):
            pass

    print("Opening your browser to sign in. If it doesn't open, visit:\n\n" + url + "\n")
    webbrowser.open(url)
    srv = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if "error" in got or got.get("state") != state:
        sys.exit(f"Sign-in failed: {got}")
    data = urllib.parse.urlencode({
        "code": got["code"], "client_id": client_id, "client_secret": client_secret,
        "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    tok = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", data))
    if "refresh_token" not in tok:
        sys.exit(f"No refresh token returned: {tok}")
    req = urllib.request.Request(
        "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
        headers={"Authorization": f"Bearer {tok['access_token']}"})
    ch = json.load(urllib.request.urlopen(req)).get("items", [])
    print("\nSigned in to channel:",
          ", ".join(f"{c['snippet']['title']} ({c['id']})" for c in ch) or "(none found!)")
    print("\nRefresh token (keep it secret):\n\n" + tok["refresh_token"] + "\n")


if __name__ == "__main__":
    main()
