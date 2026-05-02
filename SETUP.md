# gc-slack Setup Guide

Everything you need to go from zero to a running GasCity Slack app.

---

## 1. Create the Slack App

Go to **https://api.slack.com/apps** → **Create New App → From scratch**
(name it something like "GasCity", pick your workspace).

---

## 2. Enable Socket Mode

**Settings → Socket Mode** → toggle **Enable Socket Mode** on.

Then: **Settings → Basic Information → App-Level Tokens** → **Generate Token and Scopes**
- Name: `gc-slack` (or anything)
- Scope: `connections:write`
- Click Generate → copy the token (`xapp-…`)

This is your **`SLACK_APP_TOKEN`**.

---

## 3. Add Bot Token Scopes

**Features → OAuth & Permissions → Bot Token Scopes** — add all of these:

| Scope | Why |
|---|---|
| `commands` | Slash command routing |
| `chat:write` | Post messages and ephemeral replies |
| `im:write` | DM users with modal results |
| `channels:read` | Resolve channel names for patrol alerts |
| `users:read` | Resolve user IDs (for future features) |

---

## 4. Register Slash Commands

**Features → Slash Commands** → Create each of these (no URL needed in Socket Mode):

| Command | Description | Usage hint |
|---|---|---|
| `/gc` | GasCity operations | `status \| agents \| beads \| mail \| doctor` |
| `/bd` | Bead operations | `[show <id> \| create \| list [status]]` |
| `/gcmail` | Agent mail | `inbox \| send` |

For each command:
- **Request URL**: put anything (e.g. `https://example.com/slack/events`) — it's ignored in Socket Mode
- **Escape channels, users, and links**: up to you; the app doesn't need it

---

## 5. Enable Interactivity

**Features → Interactivity & Shortcuts** → toggle **Interactivity** on.

- **Request URL**: again, ignored in Socket Mode — put any valid URL as a placeholder.

This is required for button actions and modals to work.

---

## 6. Install the App

**Settings → Install App** → **Install to Workspace** → Authorize.

Copy the **Bot User OAuth Token** (`xoxb-…`). This is your **`SLACK_BOT_TOKEN`**.

---

## 7. Configure the Environment

```bash
cd ~/Development/gc-slack
cp .env.example .env   # if the example exists; otherwise create .env from scratch
```

Minimum required `.env`:

```dotenv
# ── Slack tokens ──────────────────────────────────────────────
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

# ── GasCity paths ─────────────────────────────────────────────
GC_PATH=~/bin/gc
BD_PATH=~/bin/bd
GC_CITY_ROOT=~/Development/GasCity

# ── Patrol alerts ─────────────────────────────────────────────
# Bot must be /invite'd to this channel
GC_SLACK_ALERTS_CHANNEL=#gascity-alerts

# ── Optional tuning ───────────────────────────────────────────
# GC_SLACK_PATROL_ENABLED=true   # default: true
# GC_SLACK_PATROL_INTERVAL=120   # seconds between patrol ticks, default: 120
# SLACK_SIGNING_SECRET=...       # only needed if you later switch to HTTP mode
```

---

## 8. Invite the Bot to Your Alerts Channel

In Slack, go to your alerts channel (e.g. `#gascity-alerts`) and run:

```
/invite @GasCity
```

(Use whatever you named the bot in step 1.)

---

## 9. Install Python Dependencies and Run

```bash
cd ~/Development/gc-slack
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

You should see:
```
INFO  slack_bolt.App: Starting in Socket Mode
INFO  slack_sdk.socket_mode: Connected to Slack
INFO  patrol: started, interval=120s, channel=#gascity-alerts
```

Test with `/gc status` in any Slack channel.

---

## 10. Run as a launchd Service (optional, recommended)

Create `~/Library/LaunchAgents/com.gascity.slack.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.gascity.slack</string>
  <key>ProgramArguments</key>
  <array>
    <string>/Users/your-username/Development/gc-slack/.venv/bin/python</string>
    <string>/Users/your-username/Development/gc-slack/app.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/your-username/Development/gc-slack</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/Users/your-username/bin:/usr/bin:/bin</string>
    <!-- Slack tokens — or load via a .env file and remove these -->
    <key>SLACK_BOT_TOKEN</key>
    <string>xoxb-...</string>
    <key>SLACK_APP_TOKEN</key>
    <string>xapp-...</string>
    <key>GC_PATH</key>
    <string>/Users/your-username/bin/gc</string>
    <key>BD_PATH</key>
    <string>/Users/your-username/bin/bd</string>
    <key>GC_CITY_ROOT</key>
    <string>/Users/your-username/Development/GasCity</string>
    <key>GC_SLACK_ALERTS_CHANNEL</key>
    <string>#gascity-alerts</string>
  </dict>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/your-username/.gc/gc-slack.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/your-username/.gc/gc-slack.log</string>
</dict>
</plist>
```

> ⚠️ **Note:** launchd doesn't load `.env` files automatically. Either inline the vars in the plist (as shown above) or add a small wrapper script that sources `.env` before launching Python.

```bash
launchctl load ~/Library/LaunchAgents/com.gascity.slack.plist
launchctl start com.gascity.slack

# Check it's alive:
tail -f ~/.gc/gc-slack.log
```

---

## Quick Reference: What Each Token Does

| Token | Prefix | Where to find it | Used for |
|---|---|---|---|
| `SLACK_BOT_TOKEN` | `xoxb-` | OAuth & Permissions → Install App | Posting messages, interacting with users |
| `SLACK_APP_TOKEN` | `xapp-` | Basic Information → App-Level Tokens | Socket Mode WebSocket connection |

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `SLACK_APP_TOKEN not set` or no Socket Mode connection | Check `xapp-` token is in `.env` and Socket Mode is enabled in the app config |
| Slash commands do nothing | Make sure the commands are registered AND Interactivity is enabled |
| Buttons/modals silently fail | Interactivity must be enabled (step 5) |
| Patrol alerts not appearing | Bot not invited to channel — run `/invite @GasCity` in the alerts channel |
| `gc` / `bd` commands fail | Check `GC_PATH`, `BD_PATH`, and that `PATH` in launchd includes `/opt/homebrew/bin` and `~/bin` |
| Session peek buttons missing | Known PascalCase bug — already fixed in `blocks.py` |
