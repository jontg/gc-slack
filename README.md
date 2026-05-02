# GasCity Slack Interface

A Slack app that provides native UI for GasCity operations.

## Features
- `/gc` — city status, agents, mail, diagnostics
- `/bd` — bead browser, create, show, watch
- `/gcmail` — inbox, send, peek
- Interactive buttons and modals
- Optional patrol alerts for crashes, high-priority beads

## Setup

### 1. Create Slack App
1. Go to https://api.slack.com/apps
2. "Create New App" → "From scratch"
3. Name: `GasCity`, workspace: your workspace
4. Add slash commands:
   - `/gc` → Request URL: `https://your-domain.com/slack/commands`
   - `/bd` → Request URL: `https://your-domain.com/slack/commands`
   - `/gcmail` → Request URL: `https://your-domain.com/slack/commands`
5. Enable Interactivity → Request URL: `https://your-domain.com/slack/interactive`
6. OAuth & Permissions → Add scopes:
   - `commands`
   - `chat:write`
   - `users:read`
   - `channels:read`
7. Install app to workspace
8. Copy Bot User OAuth Token and Signing Secret

### 2. Configure
```bash
cp gc-slack.toml.example gc-slack.toml
# Edit gc-slack.toml with your tokens and paths
```

### 3. Run
```bash
pip install -r requirements.txt

# Development
export SLACK_BOT_TOKEN="xoxb-..."
export SLACK_SIGNING_SECRET="..."
python app.py

# Production (with gunicorn)
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 4. Expose to Slack
For local dev, use ngrok:
```bash
ngrok http 5000
# Update Slack app Request URLs to ngrok URL
```

For production, deploy behind nginx/caddy with HTTPS.

## Usage

### View city status
```
/gc status
```
→ Shows city state, agent counts, quick action buttons

### List agents
```
/gc agents
```
→ Shows active sessions with peek buttons

### Show a bead
```
/bd show mi-abc123
```
→ Bead card with assign/comment/watch actions

### Check mail
```
/gcmail inbox
```
→ Unread messages

### Run diagnostics
```
/gc doctor
```
→ Health checks

## Development

### Adding a new command
1. Add handler function in `app.py`
2. Add route to slash command handler
3. Test with ngrok + Slack

### Adding button handlers
1. Add action handler in `handle_interactive()`
2. Use `action_id` to route to handler
3. Return updated message blocks

### TODO
- [ ] Implement interactive button handlers
- [ ] Add modal workflows (create bead, send mail)
- [ ] Parse structured output from gc/bd (add --json flags)
- [ ] Background patrol job (APScheduler or celery)
- [ ] User → alias mapping (from config)
- [ ] Bead watch subscriptions (SQLite state)
- [ ] Agent peek (via gc session peek)
- [ ] Thread-based bead discussions

## Architecture

```
Slack → Flask app → subprocess → gc/bd CLI → GasCity/Dolt
                  ↓
               SQLite (subscriptions, state)
```

## Security Notes
- Verify Slack request signatures (already done)
- Don't expose gc commands that can delete data without confirmation
- Consider restricting commands to specific users/channels
- Run behind reverse proxy with rate limiting
- Keep bot token secret (use env vars, not in code)

## License
MIT
