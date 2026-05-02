# GasCity Slack Interface

## Overview
A Slack app that exposes GasCity operations through native Slack UI patterns.

## Core Commands

### `/gc [subcommand]`
Main interface to GasCity operations.

**Subcommands:**
- `/gc status` → ephemeral message with city overview + "Refresh" button
- `/gc agents` → list agents with session state, "Peek" buttons
- `/gc beads` → interactive bead browser (filters in modal)
- `/gc mail` → inbox view with mark-read/archive actions
- `/gc doctor` → run diagnostics, post results
- `/gc restart` → confirmation dialog → restart city

### `/bd [subcommand]`
Bead operations.

**Subcommands:**
- `/bd show <id>` → rich bead card with actions (assign, comment, close)
- `/bd create` → modal workflow (type, title, description, labels)
- `/bd search` → modal with filters → results with "Show" buttons
- `/bd mine` → your assigned beads
- `/bd watch <id>` → subscribe to updates in current channel/thread

### `/gcmail [subcommand]`
Mail operations (lighter weight than full `/gc mail`).

**Subcommands:**
- `/gcmail inbox` → unread count + quick links
- `/gcmail send` → modal (to, subject, body)
- `/gcmail peek <id>` → show mail without marking read

## Interactive Patterns

### 1. Bead Cards
Rich message blocks with:
- Header: type badge + ID + title
- Body: description (collapsed if long)
- Metadata: status, assignee, labels, created/updated
- Actions: Assign to me | Comment | Update | Close
- Attachments: linked artifacts, related beads

### 2. Agent Peek
- `/gc agents` shows list with "Peek" buttons
- Button → modal with last N lines of session output
- "Refresh" and "Full Log" (open in thread) options
- "Nudge" button → opens nudge compose modal

### 3. Bead Watch
- `/bd watch mi-abc123` subscribes channel/thread to updates
- Bot posts update cards when bead changes
- Updates thread if original watch was in thread
- Actions on update cards: unwatch, show full, comment

### 4. City Status Dashboard
- `/gc status` → ephemeral card with:
  - City state (running/stopped)
  - Active agents count + breakdown
  - Beads by status (chart or counts)
  - Recent activity (last 5 events)
  - Quick actions: Refresh | Agents | Beads | Doctor

## Background Jobs

### Patrol Notifications (optional, configurable)
- Every N minutes, check for notable events:
  - Agents crashed/restarted
  - High-priority beads created
  - Warrants filed
  - Mail to specific aliases
- Post to configured channel (e.g., `#gascity-alerts`)

### Scheduled Reports (optional)
- Daily digest: bead counts, agent uptime, mail volume
- Post to configured channel

## Implementation Notes

### Backend
- Python Flask or FastAPI app
- Uses `subprocess` to shell out to `gc` and `bd` commands
- Parses output (some commands may need `--json` flag added to gc/bd)
- Manages Slack workspace state (watched beads, subscriptions) in local DB (SQLite?)

### Environment
- Runs with same PATH as GasCity supervisor
- Reads `~/.gc/config` for city path, settings
- Optionally reads `gc-slack.toml` for:
  - Patrol settings
  - Default channels
  - Command aliases
  - Access control (restrict to specific Slack users/groups?)

### Slack Setup
- App manifest with slash commands, interactive components
- Bot token scopes: `commands`, `chat:write`, `users:read`, `channels:read`, `channels:history`
- Socket mode OR webhook endpoint (socket mode easier for local dev)

### Error Handling
- If gc command fails, show error in ephemeral message
- If city is stopped, show helpful message with "Start City" action
- Rate limiting on expensive commands (peek, doctor)

## Future Ideas
- `/gc convoy` subcommand for convoy operations
- Inline bead references: `#mi-abc123` auto-expands to card
- Thread-based "work session" — create bead, discuss, assign, close all in thread
- Integration with EDITH: `/edith do X in GasCity` → EDITH uses gc-slack backend
- Voice interface via Slack huddles (far future)

## Example Flows

### Create and assign a bead
1. User: `/bd create`
2. Bot: opens modal (type, title, description, labels)
3. User: fills modal, submits
4. Bot: runs `gc bd create ...`, posts bead card to channel
5. User: clicks "Assign to me" on card
6. Bot: runs `gc bd update <id> --assignee=<user_alias>`, updates card

### Watch a refinery session
1. User: `/gc agents`
2. Bot: shows agent list
3. User: clicks "Peek" on `mimir/gastown.refinery`
4. Bot: modal with last 50 lines of output
5. User: clicks "Watch in Thread"
6. Bot: posts thread in channel, updates on bead changes

### Patrol alert
1. (background job detects agent crash)
2. Bot posts to `#gascity-alerts`:
   > ⚠️ **Agent Down**
   > `saga/gastown.refinery` crashed at 14:32 UTC
   > Exit code: 1
   > Last log: "fatal: dolt connection timeout"
   > [Show Logs] [Restart Agent] [File Warrant]

---

## Next Steps
- [ ] Scaffold Flask app with slash command handling
- [ ] Implement `/gc status` and `/gc agents` as MVP
- [ ] Design Slack Block Kit templates for bead cards
- [ ] Add `--json` output flags to gc/bd commands (if needed)
- [ ] Deploy as launchd daemon or systemd service
- [ ] Write gc-slack.toml config schema
