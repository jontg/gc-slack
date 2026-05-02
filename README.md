# gc-slack

Native Slack interface for GasCity. Runs entirely in **Socket Mode** — no
public URL, no ngrok, no reverse proxy needed. Works from inside a private
network alongside GasCity.

## Features

- `/gc` — city status, agents, mail, diagnostics
- `/bd` — bead browser, create, update, comment, close
- `/gcmail` — inbox, compose
- Interactive buttons and modals for all write operations
- Background patrol: alerts on downed always-awake agents and new P0/P1 beads

## How it works

```
Slack ←—— WebSocket (Socket Mode) ——→ app.py ——→ gc / bd CLI ——→ GasCity / Dolt
```

The app connects *out* to Slack over a persistent WebSocket. No inbound port
or public URL required.

## Setup

### 1. Create the Slack app

1. Go to https://api.slack.com/apps → **Create New App → From an app manifest**
   (or "From scratch" and follow the steps below)
2. **Basic Information → App-Level Tokens** → Generate a token with scope
   `connections:write`. Copy it — this is your `SLACK_APP_TOKEN` (`xapp-…`).
3. **Socket Mode** → Enable Socket Mode.
4. **Slash Commands** → Create three commands, all pointing at your app
   (no URL needed in Socket Mode — just fill in the description):
   - `/gc` — GasCity operations
   - `/bd` — Bead operations
   - `/gcmail` — Mail operations
5. **Interactivity & Shortcuts** → Enable Interactivity (no URL needed).
6. **OAuth & Permissions → Bot Token Scopes** — add:
   - `commands`
   - `chat:write`
   - `im:write`
   - `channels:read`
   - `users:read`
7. **Install App** → copy the **Bot User OAuth Token** (`xoxb-…`).

### 2. Configure

```bash
cd ~/Development/gc-slack
cp .env.example .env
```

Edit `.env`:

```
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...

GC_PATH=~/bin/gc
BD_PATH=~/bin/bd
GC_CITY_ROOT=~/Development/GasCity

# Patrol alerts channel (bot must be a member)
GC_SLACK_ALERTS_CHANNEL=#gascity-alerts
GC_SLACK_PATROL_INTERVAL=120
```

`SLACK_SIGNING_SECRET` is not required in Socket Mode but can be set if you
want to add HTTP mode later.

### 3. Install and run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

You should see:
```
INFO  slack_bolt.App: Starting in Socket Mode
INFO  slack_sdk.socket_mode: Connected to Slack
```

### 4. Run as a launchd service (optional)

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
    <string>$HOME/Development/gc-slack/.venv/bin/python</string>
    <string>$HOME/Development/gc-slack/app.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$HOME/Development/gc-slack</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:$HOME/bin:/usr/bin:/bin</string>
  </dict>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$HOME/.gc/gc-slack.log</string>
  <key>StandardErrorPath</key>
  <string>$HOME/.gc/gc-slack.log</string>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.gascity.slack.plist
```

## Usage

### City status
```
/gc status
```
Shows city state and agent list with **Refresh / Agents / Beads / Mail / Doctor** buttons.

### Agents
```
/gc agents
```
Live session list with **Nudge** and **Send Mail** buttons.

### Beads
```
/bd show gc-5fsy8a      # rich card with Update / Comment / Close / Mail buttons
/bd create              # opens Create Bead modal
/bd list open           # list by status
/gc beads               # open beads, with Filter and New Bead buttons
```

### Mail
```
/gcmail inbox           # unread messages
/gcmail send            # opens Send Mail modal
```

### Nudge an agent
Use the **Nudge Agent** button from `/gc agents`, or the **Mail** button on
any bead card.

### Diagnostics
```
/gc doctor
```

## Patrol

When `GC_SLACK_PATROL_ENABLED=true` (default), the app polls GasCity every
`GC_SLACK_PATROL_INTERVAL` seconds and posts to `GC_SLACK_ALERTS_CHANNEL`:

- 🚨 **Agent Down** — any always-awake agent (mayor, deacon, witness, boot) is stopped
- ⚠️ **New high-priority beads** — new P0/P1 open beads since last check

Make sure the bot is invited to the alerts channel: `/invite @GasCity`

## Architecture

```
gc_slack/
  gc.py       — subprocess wrapper for gc and bd (JSON output, correct PATH)
  blocks.py   — Block Kit builders for all views and modals
  patrol.py   — APScheduler background patrol
app.py        — slack-bolt app: slash commands, button actions, modal submissions
```

## TODO

- [ ] Launchd plist: load `.env` file (or inline vars in plist)
- [ ] `/gc session peek <agent>` → modal with last N lines
- [ ] Bead watch subscriptions (SQLite state, post on bead change)
- [ ] User → GasCity alias mapping (for "assign to me")
- [ ] Warrant filing shortcut
- [ ] Patrol: detect warrant beads, post with agent actions
