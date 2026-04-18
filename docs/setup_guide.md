# Setup Guide — Connecting Your Accounts

Welcome! Before you can use Komoot-Strava-Sync, you need to link two things: your **Komoot account** and a **Strava API application**. This guide walks you through both.

---

## Step 1 — Find Your Komoot User ID

Your Komoot User ID is a numeric identifier found in the URL of your public profile.

1. Open [komoot.com](https://www.komoot.com) and log in.
2. Click your **profile picture** (top-right) → **"Profile"**.
3. Look at the URL in your browser's address bar. It will look like:
   ```
   https://www.komoot.com/user/1234567890123
   ```
4. The long number at the end is your **Komoot User ID** (e.g. `1234567890123`).

> **Tip:** You can also find it via the Komoot mobile app → Profile → Share Profile → copy the link.

---

## Step 2 — Create a Strava API Application

The sync service communicates with Strava on your behalf using your own private API credentials. This keeps your data fully under your control and avoids sharing tokens with third parties.

1. Visit **[strava.com/settings/api](https://www.strava.com/settings/api)** (you must be logged in).

2. Fill in the form as follows:

   | Field | What to enter |
   |---|---|
   | **Application Name** | `Komoot Sync` (or any name you like) |
   | **Category** | `Other` |
   | **Club** | Leave blank |
   | **Website** | `http://localhost:3000` (for local setups) or your hosted domain |
   | **Application Description** | `Synchronises Komoot tours to Strava automatically` |
   | **Authorization Callback Domain** | `localhost` (local) or your server domain (e.g. `sync.yourdomain.com`) |

3. Click **"Create"**. Strava will now show you your app credentials:

   | Value | Where to find it |
   |---|---|
   | **Client ID** | Shown prominently on the API settings page |
   | **Client Secret** | Click **"Show"** next to "Client Secret" |

4. Copy both values into the setup form in this dashboard.

---

## Step 3 — Authorise Strava (Get Your Access Token)

After entering your Client ID and Secret, click **"Connect with Strava"** in the dashboard. You will be redirected to Strava to approve the connection.

Once approved, Strava redirects you back and the sync service stores your access token securely (encrypted with AES-256). You do **not** need to copy any tokens manually.

> **Note:** Strava tokens expire every 6 hours. The backend automatically refreshes them using your Client Secret, so you only need to authorise once.

---

## Step 4 — Enter Your Komoot Credentials

Your Komoot email and password are needed so the service can download your tour GPX files.

- These credentials are **never stored in plain text**. They are encrypted immediately using AES-256 (Fernet) and only decrypted in-memory when a sync job runs.
- You can revoke access at any time by removing your credentials from the **Vault** page.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| "No Strava account linked" | Click "Connect with Strava" on the Dashboard page |
| "Missing Komoot credentials" | Re-enter your email/password in the Vault section |
| Sync shows 0 activities | Check the Activity Feed for error badges; confirm Komoot has public or logged-in tours |
| Strava API 429 error | The app is rate-limited. Syncs will retry automatically within 15 minutes |
