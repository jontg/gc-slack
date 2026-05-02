#!/usr/bin/env python3
"""
gc_slack/blocks.py — Slack Block Kit builders.

Functions return lists of block dicts ready to pass to
response_body["blocks"] or client.chat_postMessage(blocks=...).
"""

from __future__ import annotations

from typing import Any

PRIORITY_EMOJI = {0: "🔴", 1: "🟠", 2: "🟡", 3: "🔵", 4: "⚪"}
STATUS_EMOJI = {
    "open": "○",
    "in_progress": "⚙️",
    "blocked": "🚫",
    "deferred": "💤",
    "closed": "✅",
}
TYPE_EMOJI = {
    "bug": "🐛",
    "feature": "✨",
    "task": "📋",
    "epic": "🗺️",
    "chore": "🔧",
    "decision": "⚖️",
}


def _trunc(text: str, n: int = 300) -> str:
    return text if len(text) <= n else text[:n] + "…"


# ── City Status ───────────────────────────────────────────────────────────────


def city_status_blocks(raw_output: str) -> list[dict]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🏙️ GasCity Status", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{raw_output.strip()}```"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                _btn("🔄 Refresh", "gc_status_refresh"),
                _btn("👥 Agents", "gc_agents_list"),
                _btn("📦 Beads", "gc_beads_open"),
                _btn("📬 Mail", "gc_mail_inbox"),
                _btn("🩺 Doctor", "gc_doctor_run", style="danger"),
            ],
        },
    ]


# ── Agents ────────────────────────────────────────────────────────────────────


def agents_blocks(raw_output: str, sessions: list[dict] | None = None) -> list[dict]:
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "👥 Agents", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{raw_output.strip()}```"},
        },
    ]

    # If we have structured session data, add a Peek button per active session
    if sessions:
        peek_elements = []
        for s in sessions:
            # gc session list --json uses PascalCase keys; fall back to lowercase
            alias = s.get("Alias") or s.get("alias") or ""
            # Skip orphaned sessions with no alias (leftover from previous run)
            if not alias:
                continue
            peek_elements.append(_btn(f"👁 {alias}", "gc_peek_open", value=alias))
            if len(peek_elements) >= 5:  # max 5 buttons per actions block
                break
        if peek_elements:
            blocks += [
                {"type": "divider"},
                {"type": "actions", "elements": peek_elements},
            ]

    blocks += [
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                _btn("🔄 Refresh", "gc_agents_list"),
                _btn("👁 Peek Agent", "gc_peek_open"),
                _btn("✉️ Nudge Agent", "gc_nudge_open"),
                _btn("✉️ Send Mail", "gc_mail_send_open"),
            ],
        },
    ]
    return blocks


# ── Bead Card ─────────────────────────────────────────────────────────────────


def bead_card_blocks(bead: dict, *, show_actions: bool = True) -> list[dict]:
    bid = bead.get("id", "?")
    title = bead.get("title", "(no title)")
    status = bead.get("status", "open")
    priority = bead.get("priority", 2)
    btype = bead.get("issue_type", "task")
    assignee = bead.get("assignee") or bead.get("owner") or "—"
    created = (bead.get("created_at") or "")[:10]
    updated = (bead.get("updated_at") or "")[:10]
    desc = _trunc(bead.get("description") or "", 280)
    labels = bead.get("labels") or []

    p_emoji = PRIORITY_EMOJI.get(priority, "🟡")
    s_emoji = STATUS_EMOJI.get(status, "○")
    t_emoji = TYPE_EMOJI.get(btype, "📋")

    label_str = ("  •  " + "  ".join(f"`{l}`" for l in labels)) if labels else ""
    header = f"{t_emoji} *{bid}*  {p_emoji} P{priority}  {s_emoji} {status}{label_str}"

    blocks: list[dict] = [
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{title}*"},
        },
    ]

    if desc:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": desc}}
        )

    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"assignee: `{assignee}`  •  created: {created}  •  updated: {updated}",
                }
            ],
        }
    )

    if show_actions:
        blocks += [
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    _btn("✅ Close", "bd_close", value=bid, style="primary"),
                    _btn("✏️ Update", "bd_update_open", value=bid),
                    _btn("💬 Comment", "bd_comment_open", value=bid),
                    _btn("📬 Mail Assignee", "bd_mail_assignee_open", value=bid),
                ],
            },
        ]

    return blocks


# ── Bead List ─────────────────────────────────────────────────────────────────


def bead_list_blocks(beads: list[dict], title: str = "📦 Beads") -> list[dict]:
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": title, "emoji": True},
        }
    ]

    if not beads:
        blocks.append(
            {"type": "section", "text": {"type": "mrkdwn", "text": "_No beads found._"}}
        )
    else:
        for b in beads[:20]:  # Block Kit cap
            bid = b.get("id", "?")
            title_text = _trunc(b.get("title", "(no title)"), 80)
            status = b.get("status", "open")
            priority = b.get("priority", 2)
            p_emoji = PRIORITY_EMOJI.get(priority, "🟡")
            s_emoji = STATUS_EMOJI.get(status, "○")
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{s_emoji} {p_emoji} *{bid}*  {title_text}",
                    },
                    "accessory": _btn("Show", "bd_show_bead", value=bid),
                }
            )

    blocks += [
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                _btn("🔍 Filter", "gc_beads_filter_open"),
                _btn("➕ New Bead", "bd_create_open"),
            ],
        },
    ]
    return blocks


# ── Mail ──────────────────────────────────────────────────────────────────────


def mail_inbox_blocks(raw_output: str) -> list[dict]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "📬 Mail Inbox", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{raw_output.strip()}```"},
        },
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                _btn("✉️ Send Mail", "gc_mail_send_open"),
                _btn("🔄 Refresh", "gc_mail_inbox"),
            ],
        },
    ]


# ── Doctor ────────────────────────────────────────────────────────────────────


def doctor_blocks(raw_output: str, stderr: str = "") -> list[dict]:
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "🩺 Doctor", "emoji": True},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"```{raw_output.strip()}```"},
        },
    ]
    if stderr.strip():
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"⚠️ *stderr:*\n```{stderr.strip()}```"},
            }
        )
    return blocks


# ── Patrol alert ──────────────────────────────────────────────────────────────


def patrol_alert_blocks(
    title: str,
    detail: str,
    severity: str = "warning",  # warning | critical | info
) -> list[dict]:
    icon = {"warning": "⚠️", "critical": "🚨", "info": "ℹ️"}.get(severity, "⚠️")
    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"{icon} *{title}*\n{detail}"},
        }
    ]


# ── Error / success ───────────────────────────────────────────────────────────


def error_blocks(message: str) -> list[dict]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": f"❌ {message}"}}]


def success_blocks(message: str) -> list[dict]:
    return [{"type": "section", "text": {"type": "mrkdwn", "text": f"✅ {message}"}}]


# ── Modals ────────────────────────────────────────────────────────────────────


def modal_create_bead(trigger_id: str | None = None) -> dict:
    """View payload for the 'Create Bead' modal."""
    return {
        "type": "modal",
        "callback_id": "modal_create_bead",
        "title": {"type": "plain_text", "text": "Create Bead"},
        "submit": {"type": "plain_text", "text": "Create"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title",
                "label": {"type": "plain_text", "text": "Title"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Short summary of the bead"},
                },
            },
            {
                "type": "input",
                "block_id": "description",
                "optional": True,
                "label": {"type": "plain_text", "text": "Description"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Context, acceptance criteria, etc.",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "type",
                "label": {"type": "plain_text", "text": "Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": _opt("task", "📋 Task"),
                    "options": [
                        _opt("task", "📋 Task"),
                        _opt("bug", "🐛 Bug"),
                        _opt("feature", "✨ Feature"),
                        _opt("chore", "🔧 Chore"),
                        _opt("epic", "🗺️ Epic"),
                        _opt("decision", "⚖️ Decision"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "priority",
                "label": {"type": "plain_text", "text": "Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": _opt("2", "🟡 P2 — Normal"),
                    "options": [
                        _opt("0", "🔴 P0 — Critical"),
                        _opt("1", "🟠 P1 — High"),
                        _opt("2", "🟡 P2 — Normal"),
                        _opt("3", "🔵 P3 — Low"),
                        _opt("4", "⚪ P4 — Icebox"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "labels",
                "optional": True,
                "label": {"type": "plain_text", "text": "Labels"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "comma-separated, e.g. gastown,P1"},
                },
            },
            {
                "type": "input",
                "block_id": "assignee",
                "optional": True,
                "label": {"type": "plain_text", "text": "Assignee"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. mimir/gastown.refinery or gastown__mayor",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "parent",
                "optional": True,
                "label": {"type": "plain_text", "text": "Parent bead ID"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "e.g. gc-10v"},
                },
            },
        ],
    }


def modal_update_bead(bead: dict) -> dict:
    """View payload for the 'Update Bead' modal, pre-filled with current values."""
    bid = bead.get("id", "")
    return {
        "type": "modal",
        "callback_id": "modal_update_bead",
        "private_metadata": bid,
        "title": {"type": "plain_text", "text": f"Update {bid}"},
        "submit": {"type": "plain_text", "text": "Update"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "title",
                "optional": True,
                "label": {"type": "plain_text", "text": "Title"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": bead.get("title", ""),
                },
            },
            {
                "type": "input",
                "block_id": "status",
                "optional": True,
                "label": {"type": "plain_text", "text": "Status"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": _opt(
                        bead.get("status", "open"),
                        bead.get("status", "open").replace("_", " ").title(),
                    ),
                    "options": [
                        _opt("open", "○ Open"),
                        _opt("in_progress", "⚙️ In Progress"),
                        _opt("blocked", "🚫 Blocked"),
                        _opt("deferred", "💤 Deferred"),
                        _opt("closed", "✅ Closed"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "priority",
                "optional": True,
                "label": {"type": "plain_text", "text": "Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": _opt(
                        str(bead.get("priority", 2)),
                        f"P{bead.get('priority', 2)}",
                    ),
                    "options": [
                        _opt("0", "🔴 P0 — Critical"),
                        _opt("1", "🟠 P1 — High"),
                        _opt("2", "🟡 P2 — Normal"),
                        _opt("3", "🔵 P3 — Low"),
                        _opt("4", "⚪ P4 — Icebox"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "assignee",
                "optional": True,
                "label": {"type": "plain_text", "text": "Assignee"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": bead.get("assignee") or "",
                    "placeholder": {"type": "plain_text", "text": "GasCity alias"},
                },
            },
            {
                "type": "input",
                "block_id": "notes",
                "optional": True,
                "label": {"type": "plain_text", "text": "Append note"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Appended to existing notes"},
                },
            },
        ],
    }


def modal_comment_bead(bead_id: str) -> dict:
    return {
        "type": "modal",
        "callback_id": "modal_comment_bead",
        "private_metadata": bead_id,
        "title": {"type": "plain_text", "text": f"Comment on {bead_id}"},
        "submit": {"type": "plain_text", "text": "Add Comment"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "comment",
                "label": {"type": "plain_text", "text": "Comment"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Your comment (appended to notes)"},
                },
            }
        ],
    }


def modal_send_mail(initial_to: str = "") -> dict:
    return {
        "type": "modal",
        "callback_id": "modal_send_mail",
        "title": {"type": "plain_text", "text": "Send Mail"},
        "submit": {"type": "plain_text", "text": "Send"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "to",
                "label": {"type": "plain_text", "text": "To"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": initial_to,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. gastown__mayor or mimir/gastown.refinery",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "subject",
                "label": {"type": "plain_text", "text": "Subject"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Brief subject line"},
                },
            },
            {
                "type": "input",
                "block_id": "body",
                "optional": True,
                "label": {"type": "plain_text", "text": "Body"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Message body"},
                },
            },
            {
                "type": "input",
                "block_id": "notify",
                "optional": True,
                "label": {"type": "plain_text", "text": "Options"},
                "element": {
                    "type": "checkboxes",
                    "action_id": "value",
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "Nudge recipient after sending"},
                            "value": "notify",
                        }
                    ],
                    "initial_options": [
                        {
                            "text": {"type": "plain_text", "text": "Nudge recipient after sending"},
                            "value": "notify",
                        }
                    ],
                },
            },
        ],
    }


def modal_nudge(initial_target: str = "") -> dict:
    return {
        "type": "modal",
        "callback_id": "modal_nudge",
        "title": {"type": "plain_text", "text": "Nudge Agent"},
        "submit": {"type": "plain_text", "text": "Nudge"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "target",
                "label": {"type": "plain_text", "text": "Target"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": initial_target,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. gastown__mayor or mimir/gastown.refinery",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "message",
                "label": {"type": "plain_text", "text": "Message"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "multiline": True,
                    "placeholder": {"type": "plain_text", "text": "Ephemeral message to the agent"},
                },
            },
        ],
    }


def modal_peek_agent(initial_agent: str = "", initial_lines: int = 50) -> dict:
    return {
        "type": "modal",
        "callback_id": "modal_peek_agent",
        "title": {"type": "plain_text", "text": "Peek Agent"},
        "submit": {"type": "plain_text", "text": "Peek"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "agent",
                "label": {"type": "plain_text", "text": "Agent"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "initial_value": initial_agent,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g. gastown__mayor or mimir/gastown.refinery",
                    },
                },
            },
            {
                "type": "input",
                "block_id": "lines",
                "optional": True,
                "label": {"type": "plain_text", "text": "Lines"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "initial_option": _opt(str(initial_lines), f"{initial_lines} lines"),
                    "options": [
                        _opt("20", "20 lines"),
                        _opt("50", "50 lines"),
                        _opt("100", "100 lines"),
                        _opt("200", "200 lines"),
                    ],
                },
            },
        ],
    }


def peek_result_blocks(agent: str, output: str, lines: int) -> list[dict]:
    """Blocks for the peek result posted to the channel after modal submit."""
    # Slack code blocks have a hard 3000-char limit per block
    MAX = 2900
    safe = output.strip()
    truncated = False
    if len(safe) > MAX:
        safe = safe[-MAX:]  # keep the tail (most recent output)
        truncated = True

    header = f"👁 *{agent}* — last {lines} lines"
    if truncated:
        header += "  _(truncated to fit)_"

    return [
        {"type": "section", "text": {"type": "mrkdwn", "text": header}},
        {"type": "section", "text": {"type": "mrkdwn", "text": f"```{safe}```"}},
        {"type": "divider"},
        {
            "type": "actions",
            "elements": [
                _btn("🔄 Peek again", "gc_peek_open", value=agent),
                _btn("✉️ Nudge", "gc_nudge_open", value=agent),
                _btn("✉️ Mail", "gc_mail_send_open", value=agent),
            ],
        },
    ]


def modal_bead_filter() -> dict:
    return {
        "type": "modal",
        "callback_id": "modal_bead_filter",
        "title": {"type": "plain_text", "text": "Filter Beads"},
        "submit": {"type": "plain_text", "text": "Search"},
        "close": {"type": "plain_text", "text": "Cancel"},
        "blocks": [
            {
                "type": "input",
                "block_id": "status",
                "optional": True,
                "label": {"type": "plain_text", "text": "Status"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Any"},
                    "options": [
                        _opt("open", "○ Open"),
                        _opt("in_progress", "⚙️ In Progress"),
                        _opt("blocked", "🚫 Blocked"),
                        _opt("deferred", "💤 Deferred"),
                        _opt("closed", "✅ Closed"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "priority",
                "optional": True,
                "label": {"type": "plain_text", "text": "Priority"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Any"},
                    "options": [
                        _opt("0", "🔴 P0"),
                        _opt("1", "🟠 P1"),
                        _opt("2", "🟡 P2"),
                        _opt("3", "🔵 P3"),
                        _opt("4", "⚪ P4"),
                    ],
                },
            },
            {
                "type": "input",
                "block_id": "assignee",
                "optional": True,
                "label": {"type": "plain_text", "text": "Assignee"},
                "element": {
                    "type": "plain_text_input",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "GasCity alias"},
                },
            },
            {
                "type": "input",
                "block_id": "type",
                "optional": True,
                "label": {"type": "plain_text", "text": "Type"},
                "element": {
                    "type": "static_select",
                    "action_id": "value",
                    "placeholder": {"type": "plain_text", "text": "Any"},
                    "options": [
                        _opt("task", "📋 Task"),
                        _opt("bug", "🐛 Bug"),
                        _opt("feature", "✨ Feature"),
                        _opt("chore", "🔧 Chore"),
                        _opt("epic", "🗺️ Epic"),
                        _opt("decision", "⚖️ Decision"),
                    ],
                },
            },
        ],
    }


# ── internal helpers ──────────────────────────────────────────────────────────


def _btn(
    label: str,
    action_id: str,
    value: str = "",
    style: str | None = None,
) -> dict[str, Any]:
    b: dict[str, Any] = {
        "type": "button",
        "text": {"type": "plain_text", "text": label, "emoji": True},
        "action_id": action_id,
    }
    if value:
        b["value"] = value
    if style:
        b["style"] = style
    return b


def _opt(value: str, label: str) -> dict:
    return {
        "text": {"type": "plain_text", "text": label, "emoji": True},
        "value": value,
    }
