#!/usr/bin/env python3
"""
app.py — GasCity Slack app entry point.

Uses slack-bolt in Socket Mode (no public URL needed for local dev).
To use HTTP mode instead, swap SocketModeHandler for Flask adapter.
"""

from __future__ import annotations

import logging
import os

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET", ""),
)

# ── lazy imports to keep startup fast ────────────────────────────────────────
import gc_slack.gc as gccmd
from gc_slack.blocks import (
    agents_blocks,
    bead_card_blocks,
    bead_list_blocks,
    city_status_blocks,
    doctor_blocks,
    error_blocks,
    mail_inbox_blocks,
    modal_bead_filter,
    modal_comment_bead,
    modal_create_bead,
    modal_nudge,
    modal_peek_agent,
    modal_send_mail,
    modal_update_bead,
    peek_result_blocks,
    success_blocks,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Slash commands
# ═══════════════════════════════════════════════════════════════════════════════


@app.command("/gc")
def handle_gc(ack, command, client):
    ack()
    text = (command.get("text") or "").strip()
    parts = text.split()
    sub = parts[0] if parts else "status"

    if sub == "status":
        r = gccmd.city_status()
        blocks = city_status_blocks(r.stdout) if r.ok else error_blocks(r.stderr or "gc status failed")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "agents":
        r = gccmd.session_list()
        rj = gccmd.session_list_json()
        try:
            sessions = rj.json if rj.ok else None
        except Exception:
            sessions = None
        blocks = agents_blocks(r.stdout, sessions=sessions) if r.ok else error_blocks(r.stderr or "gc session list failed")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "beads":
        r = gccmd.bead_list(status="open", limit=20)
        try:
            beads = r.json if r.ok else []
        except Exception:
            beads = []
        blocks = bead_list_blocks(beads, "📦 Open Beads")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "mail":
        r = gccmd.mail_inbox()
        blocks = mail_inbox_blocks(r.stdout) if r.ok else error_blocks(r.stderr or "gc mail inbox failed")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "doctor":
        r = gccmd.doctor()
        blocks = doctor_blocks(r.stdout, r.stderr)
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "start":
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="⏳ Starting GasCity…",
        )
        r = gccmd.city_start()
        if r.ok:
            from gc_slack.patrol import resume_patrol
            resume_patrol()
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                blocks=success_blocks("GasCity started", "Patrol alerts resumed."),
            )
        else:
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                blocks=error_blocks(r.stderr or r.stdout or "gc start failed"),
            )

    elif sub == "stop":
        # Pause patrol immediately — don't wait for gc stop to return
        # (gc stop can hang even when the city shuts down successfully)
        from gc_slack.patrol import pause_patrol
        pause_patrol()
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text="⏳ Stopping GasCity… (patrol alerts paused now)",
        )
        r = gccmd.city_stop()
        if r.ok or r.returncode == 124:  # 124 = timeout, city likely stopped anyway
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                blocks=success_blocks("GasCity stopped", "Patrol alerts paused — no more noise while the city is down."),
            )
        else:
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                blocks=error_blocks(r.stderr or r.stdout or "gc stop failed"),
            )

    else:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"Unknown subcommand `{sub}`. Available: status, agents, beads, mail, doctor, start, stop",
        )


@app.command("/bd")
def handle_bd(ack, command, client):
    ack()
    text = (command.get("text") or "").strip()
    parts = text.split()

    if not parts:
        client.views_open(
            trigger_id=command["trigger_id"],
            view=modal_create_bead(),
        )
        return

    sub = parts[0]

    if sub == "show" and len(parts) > 1:
        bead_id = parts[1]
        r = gccmd.bead_show(bead_id)
        try:
            bead = r.json[0] if r.ok else None
        except Exception:
            bead = None

        if not bead:
            client.chat_postEphemeral(
                channel=command["channel_id"],
                user=command["user_id"],
                blocks=error_blocks(f"Bead `{bead_id}` not found or error: {r.stderr}"),
            )
            return

        client.chat_postMessage(
            channel=command["channel_id"],
            blocks=bead_card_blocks(bead),
        )

    elif sub == "create":
        client.views_open(
            trigger_id=command["trigger_id"],
            view=modal_create_bead(),
        )

    elif sub == "list":
        status = parts[1] if len(parts) > 1 else "open"
        r = gccmd.bead_list(status=status, limit=20)
        try:
            beads = r.json if r.ok else []
        except Exception:
            beads = []
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=bead_list_blocks(beads),
        )

    else:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"Unknown subcommand `{sub}`. Try: show <id>, create, list [status]",
        )


@app.command("/gcmail")
def handle_gcmail(ack, command, client):
    ack()
    text = (command.get("text") or "").strip()
    parts = text.split()
    sub = parts[0] if parts else "inbox"

    if sub == "inbox":
        r = gccmd.mail_inbox()
        blocks = mail_inbox_blocks(r.stdout) if r.ok else error_blocks(r.stderr or "failed")
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            blocks=blocks,
        )

    elif sub == "send":
        client.views_open(
            trigger_id=command["trigger_id"],
            view=modal_send_mail(),
        )

    else:
        client.chat_postEphemeral(
            channel=command["channel_id"],
            user=command["user_id"],
            text=f"Unknown subcommand `{sub}`. Try: inbox, send",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Button actions → modal openers
# ═══════════════════════════════════════════════════════════════════════════════


@app.action("gc_status_refresh")
def action_status_refresh(ack, body, client):
    ack()
    r = gccmd.city_status()
    blocks = city_status_blocks(r.stdout) if r.ok else error_blocks(r.stderr or "failed")
    _update_or_ephemeral(client, body, blocks)


@app.action("gc_agents_list")
def action_agents_list(ack, body, client):
    ack()
    r = gccmd.session_list()
    rj = gccmd.session_list_json()
    try:
        sessions = rj.json if rj.ok else None
    except Exception:
        sessions = None
    blocks = agents_blocks(r.stdout, sessions=sessions) if r.ok else error_blocks(r.stderr or "failed")
    _update_or_ephemeral(client, body, blocks)


@app.action("gc_beads_open")
def action_beads_open(ack, body, client):
    ack()
    r = gccmd.bead_list(status="open", limit=20)
    try:
        beads = r.json if r.ok else []
    except Exception:
        beads = []
    blocks = bead_list_blocks(beads, "📦 Open Beads")
    _update_or_ephemeral(client, body, blocks)


@app.action("gc_mail_inbox")
def action_mail_inbox(ack, body, client):
    ack()
    r = gccmd.mail_inbox()
    blocks = mail_inbox_blocks(r.stdout) if r.ok else error_blocks(r.stderr or "failed")
    _update_or_ephemeral(client, body, blocks)


@app.action("gc_doctor_run")
def action_doctor_run(ack, body, client):
    ack()
    r = gccmd.doctor()
    blocks = doctor_blocks(r.stdout, r.stderr)
    _update_or_ephemeral(client, body, blocks)


@app.action("gc_mail_send_open")
def action_mail_send_open(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=modal_send_mail())


@app.action("gc_nudge_open")
def action_nudge_open(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=modal_nudge())


@app.action("gc_beads_filter_open")
def action_beads_filter_open(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=modal_bead_filter())


@app.action("bd_create_open")
def action_bd_create_open(ack, body, client):
    ack()
    client.views_open(trigger_id=body["trigger_id"], view=modal_create_bead())


@app.action("bd_show_bead")
def action_bd_show_bead(ack, body, client):
    ack()
    bead_id = body["actions"][0]["value"]
    r = gccmd.bead_show(bead_id)
    try:
        bead = r.json[0] if r.ok else None
    except Exception:
        bead = None

    channel = body.get("channel", {}).get("id") or body.get("container", {}).get("channel_id")
    user = body["user"]["id"]

    if not bead:
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            blocks=error_blocks(f"Bead `{bead_id}` not found"),
        )
        return

    client.chat_postMessage(channel=channel, blocks=bead_card_blocks(bead))


@app.action("bd_update_open")
def action_bd_update_open(ack, body, client):
    ack()
    bead_id = body["actions"][0]["value"]
    r = gccmd.bead_show(bead_id)
    try:
        bead = r.json[0] if r.ok else {"id": bead_id}
    except Exception:
        bead = {"id": bead_id}
    client.views_open(trigger_id=body["trigger_id"], view=modal_update_bead(bead))


@app.action("bd_comment_open")
def action_bd_comment_open(ack, body, client):
    ack()
    bead_id = body["actions"][0]["value"]
    client.views_open(trigger_id=body["trigger_id"], view=modal_comment_bead(bead_id))


@app.action("bd_mail_assignee_open")
def action_bd_mail_assignee_open(ack, body, client):
    ack()
    bead_id = body["actions"][0]["value"]
    r = gccmd.bead_show(bead_id)
    try:
        bead = r.json[0] if r.ok else {}
        assignee = bead.get("assignee") or ""
    except Exception:
        assignee = ""
    client.views_open(trigger_id=body["trigger_id"], view=modal_send_mail(initial_to=assignee))


@app.action("bd_close")
def action_bd_close(ack, body, client):
    ack()
    bead_id = body["actions"][0]["value"]
    r = gccmd.bead_close(bead_id)
    channel = body.get("channel", {}).get("id") or body.get("container", {}).get("channel_id")
    user = body["user"]["id"]

    if r.ok:
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            blocks=success_blocks(f"Closed `{bead_id}`"),
        )
    else:
        client.chat_postEphemeral(
            channel=channel,
            user=user,
            blocks=error_blocks(f"Failed to close `{bead_id}`: {r.stderr}"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Modal submissions
# ═══════════════════════════════════════════════════════════════════════════════


@app.view("modal_create_bead")
def view_create_bead(ack, body, client, view):
    ack()
    vals = view["state"]["values"]

    title = _val(vals, "title")
    description = _val(vals, "description") or ""
    btype = _val(vals, "type") or "task"
    priority = _val(vals, "priority") or "2"
    labels_raw = _val(vals, "labels") or ""
    assignee = _val(vals, "assignee") or None
    parent = _val(vals, "parent") or None

    labels = [l.strip() for l in labels_raw.split(",") if l.strip()] if labels_raw else None

    r = gccmd.bead_create(
        title,
        description=description,
        type_=btype,
        priority=priority,
        labels=labels,
        assignee=assignee,
        parent=parent,
    )

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]

    if r.ok:
        new_id = r.stdout.strip()
        # Fetch and post the full card
        show_r = gccmd.bead_show(new_id)
        try:
            bead = show_r.json[0]
            client.chat_postMessage(channel=dm_channel, blocks=bead_card_blocks(bead))
        except Exception:
            client.chat_postMessage(
                channel=dm_channel,
                blocks=success_blocks(f"Created bead `{new_id}`"),
            )
    else:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=error_blocks(f"Failed to create bead: {r.stderr}"),
        )


@app.view("modal_update_bead")
def view_update_bead(ack, body, client, view):
    ack()
    bead_id = view["private_metadata"]
    vals = view["state"]["values"]

    title = _val(vals, "title") or None
    status = _val(vals, "status") or None
    priority = _val(vals, "priority") or None
    assignee = _val(vals, "assignee") or None
    notes = _val(vals, "notes") or None

    r = gccmd.bead_update(
        bead_id,
        title=title,
        status=status,
        priority=priority,
        assignee=assignee,
        notes=notes,
    )

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]

    if r.ok:
        show_r = gccmd.bead_show(bead_id)
        try:
            bead = show_r.json[0]
            client.chat_postMessage(channel=dm_channel, blocks=bead_card_blocks(bead))
        except Exception:
            client.chat_postMessage(
                channel=dm_channel,
                blocks=success_blocks(f"Updated `{bead_id}`"),
            )
    else:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=error_blocks(f"Failed to update `{bead_id}`: {r.stderr}"),
        )


@app.view("modal_comment_bead")
def view_comment_bead(ack, body, client, view):
    ack()
    bead_id = view["private_metadata"]
    vals = view["state"]["values"]
    comment = _val(vals, "comment") or ""

    r = gccmd.bead_update(bead_id, notes=comment)

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]

    if r.ok:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=success_blocks(f"Comment added to `{bead_id}`"),
        )
    else:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=error_blocks(f"Failed: {r.stderr}"),
        )


@app.view("modal_send_mail")
def view_send_mail(ack, body, client, view):
    ack()
    vals = view["state"]["values"]
    to = _val(vals, "to") or ""
    subject = _val(vals, "subject") or ""
    mail_body = _val(vals, "body") or ""
    notify_opts = _checkboxes(vals, "notify")
    notify = "notify" in notify_opts

    r = gccmd.mail_send(to, subject, mail_body, notify=notify)

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]

    if r.ok:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=success_blocks(f"Mail sent to `{to}`: _{subject}_"),
        )
    else:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=error_blocks(f"Failed to send mail: {r.stderr}"),
        )


@app.view("modal_nudge")
def view_nudge(ack, body, client, view):
    ack()
    vals = view["state"]["values"]
    target = _val(vals, "target") or ""
    message = _val(vals, "message") or ""

    r = gccmd.nudge(target, message)

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]

    if r.ok:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=success_blocks(f"Nudged `{target}`"),
        )
    else:
        client.chat_postMessage(
            channel=dm_channel,
            blocks=error_blocks(f"Failed to nudge `{target}`: {r.stderr}"),
        )


@app.view("modal_bead_filter")
def view_bead_filter(ack, body, client, view):
    ack()
    vals = view["state"]["values"]
    status = _val(vals, "status") or None
    priority = _val(vals, "priority") or None
    assignee = _val(vals, "assignee") or None
    type_ = _val(vals, "type") or None

    r = gccmd.bead_list(status=status, priority=priority, assignee=assignee, type_=type_, limit=20)
    try:
        beads = r.json if r.ok else []
    except Exception:
        beads = []

    user = body["user"]["id"]
    dm = client.conversations_open(users=user)
    dm_channel = dm["channel"]["id"]
    client.chat_postMessage(channel=dm_channel, blocks=bead_list_blocks(beads))


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _val(vals: dict, block_id: str) -> str | None:
    """Extract a plain-text or select value from modal state."""
    block = vals.get(block_id, {})
    el = block.get("value", {})  # plain_text_input
    if el and el.get("type") == "plain_text_input":
        return el.get("value")
    # static_select
    for key, el in block.items():
        if isinstance(el, dict):
            if el.get("type") == "plain_text_input":
                return el.get("value")
            selected = el.get("selected_option")
            if selected:
                return selected.get("value")
    return None


def _checkboxes(vals: dict, block_id: str) -> list[str]:
    """Extract selected checkbox values."""
    block = vals.get(block_id, {})
    for key, el in block.items():
        if isinstance(el, dict):
            selected = el.get("selected_options", [])
            return [o["value"] for o in selected]
    return []


def _update_or_ephemeral(client, body: dict, blocks: list[dict]) -> None:
    """Try to update the original message; fall back to ephemeral."""
    channel = (
        body.get("channel", {}).get("id")
        or body.get("container", {}).get("channel_id")
    )
    ts = body.get("message", {}).get("ts") or body.get("container", {}).get("message_ts")
    user = body["user"]["id"]

    if channel and ts:
        try:
            client.chat_update(channel=channel, ts=ts, blocks=blocks)
            return
        except Exception as e:
            log.warning("chat_update failed, falling back to ephemeral: %s", e)

    if channel:
        client.chat_postEphemeral(channel=channel, user=user, blocks=blocks)


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":
    patrol_enabled = os.environ.get("GC_SLACK_PATROL_ENABLED", "true").lower() == "true"
    patrol_interval = int(os.environ.get("GC_SLACK_PATROL_INTERVAL", "120"))

    if patrol_enabled:
        from gc_slack.patrol import start_patrol
        start_patrol(app.client, interval_seconds=patrol_interval)

    app_token = os.environ.get("SLACK_APP_TOKEN")
    if app_token:
        log.info("Starting in Socket Mode")
        SocketModeHandler(app, app_token).start()
    else:
        log.info("Starting in HTTP mode on :3000")
        app.start(port=3000)
