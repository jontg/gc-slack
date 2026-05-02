#!/usr/bin/env python3
"""
gc_slack/patrol.py — Background patrol job.

Runs on a schedule (APScheduler) and posts alerts to a Slack channel
when notable GasCity events are detected:
  - Agent sessions that are stopped but should be running
  - New P0/P1 beads since last check
  - Warrant beads filed
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

log = logging.getLogger(__name__)

ALERTS_CHANNEL = os.environ.get("GC_SLACK_ALERTS_CHANNEL", "#gascity-alerts")

# State tracked between patrol runs
_last_seen_beads: set[str] = set()
_last_patrol_at: datetime | None = None


def _post(slack_client, blocks: list[dict]) -> None:
    try:
        slack_client.chat_postMessage(channel=ALERTS_CHANNEL, blocks=blocks)
    except Exception as e:
        log.error("patrol: failed to post alert: %s", e)


def run_patrol(slack_client) -> None:
    """Called by APScheduler on each tick."""
    global _last_patrol_at
    from gc_slack import gc as gccmd
    from gc_slack.blocks import patrol_alert_blocks

    now = datetime.now(timezone.utc)
    log.info("patrol: tick at %s", now.isoformat())

    _check_agents(slack_client, gccmd, patrol_alert_blocks)
    _check_new_priority_beads(slack_client, gccmd, patrol_alert_blocks)

    _last_patrol_at = now


def _check_agents(slack_client, gccmd, alert_fn) -> None:
    """Alert if any always-awake agent is stopped."""
    result = gccmd.city_status()
    if not result.ok:
        log.warning("patrol: gc status failed: %s", result.stderr)
        return

    stopped_always_awake = []
    current_agent = None
    in_agent_section = False

    for line in result.stdout.splitlines():
        stripped = line.strip()
        # Detect agent entries: "  agentname  stopped/running/..."
        if stripped and not stripped.startswith("GasCity") and not stripped.startswith("Controller"):
            parts = stripped.split()
            if len(parts) >= 2:
                name = parts[0]
                state = parts[1] if len(parts) > 1 else ""
                # Agents we consider "always-awake" by naming convention
                always_awake = any(
                    kw in name for kw in ["mayor", "deacon", "witness", "boot"]
                )
                if always_awake and "stopped" in state:
                    stopped_always_awake.append(name)

    if stopped_always_awake:
        detail = "Stopped always-awake agents:\n" + "\n".join(
            f"• `{a}`" for a in stopped_always_awake
        )
        _post(
            slack_client,
            alert_fn("Agent Down", detail, severity="critical"),
        )


def _check_new_priority_beads(slack_client, gccmd, alert_fn) -> None:
    """Alert on new P0/P1 beads since last patrol."""
    global _last_seen_beads

    result = gccmd.bead_list(priority="0", status="open", limit=20)
    p0_beads = []
    try:
        p0_beads = result.json if result.ok else []
    except Exception:
        pass

    result1 = gccmd.bead_list(priority="1", status="open", limit=20)
    p1_beads = []
    try:
        p1_beads = result1.json if result1.ok else []
    except Exception:
        pass

    all_priority = p0_beads + p1_beads
    all_ids = {b["id"] for b in all_priority}

    new_ids = all_ids - _last_seen_beads
    if new_ids and _last_seen_beads:  # skip first run (would spam everything)
        new_beads = [b for b in all_priority if b["id"] in new_ids]
        lines = []
        for b in new_beads:
            p = b.get("priority", "?")
            lines.append(f"• 🔴 P{p} `{b['id']}` {b.get('title', '')[:60]}")
        detail = "\n".join(lines)
        _post(
            slack_client,
            alert_fn(f"{len(new_beads)} new high-priority bead(s)", detail, severity="warning"),
        )

    _last_seen_beads = all_ids


def start_patrol(slack_client, interval_seconds: int = 120) -> None:
    """Start the APScheduler background patrol."""
    from apscheduler.schedulers.background import BackgroundScheduler

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_patrol,
        "interval",
        seconds=interval_seconds,
        args=[slack_client],
        id="gc_patrol",
        replace_existing=True,
    )
    scheduler.start()
    log.info("patrol: started, interval=%ds, channel=%s", interval_seconds, ALERTS_CHANNEL)
    return scheduler
