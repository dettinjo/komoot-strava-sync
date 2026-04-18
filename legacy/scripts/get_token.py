#!/usr/bin/env python3
"""One-time Strava OAuth helper — run this on your local machine.

Usage:
    python scripts/get_token.py

Requirements (install with pip):
    pip install requests

What it does:
  1. Reads STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET from environment or prompts you.
  2. Prints the Strava authorization URL — open it in your browser.
  3. Starts a temporary local HTTP server on port 8080 to catch the OAuth callback.
  4. Exchanges the authorization code for tokens.
  5. Prints the three env-var lines to copy into your .env file.

Your Strava app must have "localhost" or "127.0.0.1" as the authorised callback domain
(set at https://www.strava.com/settings/api).
The redirect URI used is: http://localhost:8080/callback
"""

import http.server
import os
import threading
import urllib.parse
import webbrowser

import requests

REDIRECT_URI = "http://localhost:8080/callback"
AUTH_URL = "https://www.strava.com/oauth/authorize"
TOKEN_URL = "https://www.strava.com/oauth/token"
SCOPE = "activity:write,activity:read_all"

# Filled in after the callback is received
_auth_code: str | None = None
_server_done = threading.Event()


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default access log

    def do_GET(self):
        global _auth_code
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self._send("404 Not Found", "Not found")
            return

        params = urllib.parse.parse_qs(parsed.query)
        if "error" in params:
            self._send("400 Bad Request", f"Authorization denied: {params['error']}")
            _server_done.set()
            return

        code = params.get("code", [None])[0]
        if not code:
            self._send("400 Bad Request", "Missing 'code' parameter")
            return

        _auth_code = code
        self._send(
            "200 OK",
            "<html><body><h2>Authorization successful!</h2>"
            "<p>You can close this tab and return to the terminal.</p></body></html>",
        )
        _server_done.set()

    def _send(self, status: str, body: str):
        code = int(status.split()[0])
        self.send_response(code)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())


def _get_env(name: str, prompt: str) -> str:
    value = os.getenv(name)
    if value:
        print(f"  Using {name} from environment.")
        return value
    return input(f"  {prompt}: ").strip()


def main():
    print("\n=== Strava OAuth Token Helper ===\n")
    client_id = _get_env("STRAVA_CLIENT_ID", "Enter your Strava Client ID")
    client_secret = _get_env("STRAVA_CLIENT_SECRET", "Enter your Strava Client Secret")

    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "approval_prompt": "auto",
        "scope": SCOPE,
    })
    auth_url = f"{AUTH_URL}?{params}"

    print(f"\nOpening Strava authorization page…\nIf it does not open automatically, visit:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("Waiting for authorization callback on http://localhost:8080/callback …")
    server = http.server.HTTPServer(("", 8080), _CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    _server_done.wait(timeout=120)
    server.server_close()

    if not _auth_code:
        print("\n[ERROR] No authorization code received. Did you authorize in the browser?")
        return

    print("\nExchanging authorization code for tokens…")
    resp = requests.post(
        TOKEN_URL,
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": _auth_code,
            "grant_type": "authorization_code",
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    access_token = data["access_token"]
    refresh_token = data["refresh_token"]
    expires_at = data["expires_at"]

    print("\n" + "=" * 60)
    print("SUCCESS — add these lines to your .env file:")
    print("=" * 60)
    print(f"STRAVA_ACCESS_TOKEN={access_token}")
    print(f"STRAVA_REFRESH_TOKEN={refresh_token}")
    print(f"STRAVA_TOKEN_EXPIRES_AT={expires_at}")
    print("=" * 60)
    print(f"\nAuthorized athlete: {data.get('athlete', {}).get('firstname', '')} {data.get('athlete', {}).get('lastname', '')}")
    print("Done.\n")


if __name__ == "__main__":
    main()
