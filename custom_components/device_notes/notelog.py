"""Pure note-log operations.

Deliberately free of any Home Assistant imports so the bug-prone log mechanics
(ordering, truncation, the dual entry/byte prune, undo) can be tested with plain
``pytest``. Each entry is a dict ``{"ts", "source", "text"}``; logs are ordered
newest-first. All functions are pure and return new lists (no mutation).
"""

from __future__ import annotations

import json

from .const import MAX_ENTRIES, MAX_ENTRY_CHARS, MAX_LOG_BYTES, MAX_STATE_CHARS


def make_entry(text: str, source: str, ts: str) -> dict:
    """Build a log entry, stripped and capped at the 255-char entry ceiling."""
    return {"ts": ts, "source": source, "text": text.strip()[:MAX_ENTRY_CHARS]}


def append(
    log: list[dict],
    entry: dict,
    *,
    max_entries: int = MAX_ENTRIES,
    max_bytes: int = MAX_LOG_BYTES,
) -> list[dict]:
    """Prepend ``entry`` (newest-first), then enforce the cap guardrails."""
    return prune([entry, *log], max_entries=max_entries, max_bytes=max_bytes)


def log_bytes(log: list[dict]) -> int:
    """Serialized UTF-8 size of the log, as stored/exposed as a JSON list."""
    return len(json.dumps(log, ensure_ascii=False).encode("utf-8"))


def prune(log: list[dict], *, max_entries: int, max_bytes: int) -> list[dict]:
    """Cap the log to the newest ``max_entries`` AND ``max_bytes``.

    Drops oldest entries (the tail of a newest-first list) until both limits
    hold. Always keeps at least the newest entry, even if it alone is large.
    """
    pruned = log[:max_entries]
    while len(pruned) > 1 and log_bytes(pruned) > max_bytes:
        pruned = pruned[:-1]
    return pruned


def delete_last(log: list[dict]) -> list[dict]:
    """Return a new log with the newest entry removed (undo). Empty-safe."""
    return log[1:]


def preview(log: list[dict]) -> str:
    """One-line sensor state: newest entry's text + ts, capped at the state limit."""
    if not log:
        return ""
    latest = log[0]
    return f"{latest['text']} ({latest['ts']})"[:MAX_STATE_CHARS]
