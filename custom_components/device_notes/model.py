"""Pure operations over the persisted data dict (device-link + uuid keying).

The persisted shape is::

    {"devices": {"<key>": {"device_id", "identifiers", "name", "log"}}}

``<key>`` is a stable internal uuid minted per opted-in device, so the Store and
entity unique_ids never depend on ``device_id`` (which rotates when an
integration is removed/re-added). ``identifiers`` is stored JSON-friendly as a
list of ``[domain, id]`` pairs and is the durable handle used to re-link a
record to a device after its ``device_id`` changes.

No Home Assistant imports: this is test-driven on plain pytest. The async Store
wrapper and registry lookups live in ``store.py``.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Iterable

from . import notelog


def _norm(identifiers: Iterable) -> frozenset[tuple]:
    """Order-independent comparable form of an identifiers collection."""
    return frozenset(tuple(i) for i in identifiers)


def find_key_by_device_id(data: dict, device_id: str) -> str | None:
    """Return the record key whose stored device_id matches, else None."""
    for key, rec in data["devices"].items():
        if rec["device_id"] == device_id:
            return key
    return None


def find_key_by_identifiers(data: dict, identifiers: Iterable) -> str | None:
    """Return the record key whose identifiers match (the re-link handle)."""
    target = _norm(identifiers)
    for key, rec in data["devices"].items():
        if _norm(rec["identifiers"]) == target:
            return key
    return None


def ensure_device(
    data: dict,
    *,
    device_id: str,
    identifiers: Iterable,
    name: str | None,
    key_factory: Callable[[], str],
) -> tuple[dict, str]:
    """Return ``(data, key)`` for this device, creating or re-linking as needed.

    - Known device_id -> return its existing key, data unchanged.
    - device_id rotated but identifiers match -> re-link (update the record's
      device_id/name), keep the same key and its log.
    - Otherwise -> mint a new key via ``key_factory``.

    Pure: never mutates the input ``data``.
    """
    key = find_key_by_device_id(data, device_id)
    if key is not None:
        return data, key

    new_data = copy.deepcopy(data)

    key = find_key_by_identifiers(new_data, identifiers)
    if key is not None:
        rec = new_data["devices"][key]
        rec["device_id"] = device_id
        rec["name"] = name
        return new_data, key

    key = key_factory()
    new_data["devices"][key] = {
        "device_id": device_id,
        "identifiers": [list(i) for i in identifiers],
        "name": name,
        "log": [],
    }
    return new_data, key


def relink_all(
    data: dict, current_device_id_for: Callable[[Iterable], str | None]
) -> dict:
    """Refresh stale device_ids from identifiers (startup re-link sweep).

    For each record, resolve the current device_id from its identifiers; if it
    resolved and changed, update it. Unresolvable devices keep their last known
    device_id (record + log preserved). Pure.
    """
    new_data = copy.deepcopy(data)
    for rec in new_data["devices"].values():
        current = current_device_id_for(rec["identifiers"])
        if current is not None and current != rec["device_id"]:
            rec["device_id"] = current
    return new_data


def append_note(data: dict, key: str, entry: dict) -> dict:
    """Append an entry to a record's log (cap-enforced via notelog). Pure."""
    new_data = copy.deepcopy(data)
    rec = new_data["devices"][key]
    rec["log"] = notelog.append(rec["log"], entry)
    return new_data


def delete_last_note(data: dict, key: str) -> dict:
    """Remove the newest entry from a record's log (undo). Pure."""
    new_data = copy.deepcopy(data)
    rec = new_data["devices"][key]
    rec["log"] = notelog.delete_last(rec["log"])
    return new_data


def delete_note_at(data: dict, key: str, ts: str) -> dict:
    """Remove the entry matching ``ts`` from a record's log. Pure."""
    new_data = copy.deepcopy(data)
    rec = new_data["devices"][key]
    rec["log"] = notelog.delete_at(rec["log"], ts)
    return new_data


def clear_notes(data: dict, key: str) -> dict:
    """Empty a record's log. Pure."""
    new_data = copy.deepcopy(data)
    new_data["devices"][key]["log"] = []
    return new_data
