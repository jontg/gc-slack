#!/usr/bin/env python3
"""
gc_slack/gc.py — thin wrapper around gc and bd CLI commands.

All commands run with the correct PATH (homebrew + ~/bin) and cwd set
to GC_CITY_ROOT.  JSON output is requested where possible so callers
get structured data rather than screen-formatted text.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any

GC_PATH = os.environ.get("GC_PATH", os.path.expanduser("~/bin/gc"))
BD_PATH = os.environ.get("BD_PATH", os.path.expanduser("~/bin/bd"))
GC_CITY_ROOT = os.environ.get("GC_CITY_ROOT", os.path.expanduser("~/Development/GasCity"))

_GC_ENV: dict[str, str] | None = None


def _env() -> dict[str, str]:
    global _GC_ENV
    if _GC_ENV is None:
        e = os.environ.copy()
        e["PATH"] = f"/opt/homebrew/bin:{os.path.expanduser('~/bin')}:{e.get('PATH', '')}"
        _GC_ENV = e
    return _GC_ENV


@dataclass
class CmdResult:
    stdout: str
    stderr: str
    returncode: int
    ok: bool

    @property
    def json(self) -> Any:
        """Parse stdout as JSON (strips trailing status lines bd appends)."""
        text = self.stdout.strip()
        # bd sometimes appends "Showing N issues; more results…" after the JSON
        # Find the last ] or } and truncate there.
        for end_char in ("]", "}"):
            idx = text.rfind(end_char)
            if idx != -1:
                try:
                    return json.loads(text[: idx + 1])
                except json.JSONDecodeError:
                    pass
        return json.loads(text)


def _run(binary: str, args: list[str]) -> CmdResult:
    r = subprocess.run(
        [binary] + args,
        cwd=GC_CITY_ROOT,
        capture_output=True,
        text=True,
        env=_env(),
    )
    return CmdResult(r.stdout, r.stderr, r.returncode, r.returncode == 0)


def gc(*args: str) -> CmdResult:
    return _run(GC_PATH, list(args))


def bd(*args: str) -> CmdResult:
    return _run(BD_PATH, list(args))


# ── high-level helpers ────────────────────────────────────────────────────────


def city_status() -> CmdResult:
    return gc("status")


def session_list() -> CmdResult:
    return gc("session", "list")


def doctor() -> CmdResult:
    return gc("doctor")


def mail_inbox() -> CmdResult:
    return gc("mail", "inbox")


def mail_send(to: str, subject: str, body: str, notify: bool = True) -> CmdResult:
    args = ["mail", "send", to, "-s", subject, "-m", body]
    if notify:
        args.append("--notify")
    return gc(*args)


def nudge(target: str, message: str) -> CmdResult:
    return gc("nudge", target, message)


def bead_list(
    *,
    status: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    type_: str | None = None,
    limit: int = 30,
) -> CmdResult:
    args = ["list", "--json", "--no-pager", "--limit", str(limit)]
    if status:
        args += ["--status", status]
    if assignee:
        args += ["--assignee", assignee]
    if priority:
        args += ["--priority", priority]
    if type_:
        args += ["--type", type_]
    return bd(*args)


def bead_show(bead_id: str) -> CmdResult:
    return bd("show", bead_id, "--json")


def bead_create(
    title: str,
    *,
    description: str = "",
    type_: str = "task",
    priority: str = "2",
    labels: list[str] | None = None,
    assignee: str | None = None,
    parent: str | None = None,
) -> CmdResult:
    args = ["create", "--silent", "--title", title, "--type", type_, "--priority", priority]
    if description:
        args += ["--description", description]
    if labels:
        args += ["--labels", ",".join(labels)]
    if assignee:
        args += ["--assignee", assignee]
    if parent:
        args += ["--parent", parent]
    return bd(*args)


def bead_update(
    bead_id: str,
    *,
    status: str | None = None,
    assignee: str | None = None,
    priority: str | None = None,
    add_label: str | None = None,
    remove_label: str | None = None,
    notes: str | None = None,
    title: str | None = None,
) -> CmdResult:
    args = ["update", bead_id]
    if status:
        args += ["--status", status]
    if assignee:
        args += ["--assignee", assignee]
    if priority:
        args += ["--priority", priority]
    if add_label:
        args += ["--add-label", add_label]
    if remove_label:
        args += ["--remove-label", remove_label]
    if notes:
        args += ["--append-notes", notes]
    if title:
        args += ["--title", title]
    return bd(*args)


def bead_close(bead_id: str) -> CmdResult:
    return bd("update", bead_id, "--status", "closed")


def session_list_json() -> CmdResult:
    return gc("session", "list", "--json")


def session_peek(agent: str, lines: int = 50) -> CmdResult:
    return gc("session", "peek", agent, "--lines", str(lines))


def city_start() -> CmdResult:
    return gc("start")


def city_stop() -> CmdResult:
    return gc("stop")
