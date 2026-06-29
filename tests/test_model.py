"""Tests for the pure persisted-data model (device-link + uuid keying).

No Home Assistant runtime: the model operates on a plain dict (the shape the
Store persists) and takes an injected ``key_factory`` so uuid minting is
deterministic in tests. Device-attach/re-link logic lives here so it can be
test-driven without HA.
"""

from custom_components.device_notes import model


def test_ensure_device_mints_a_new_key_for_unknown_device():
    data = {"devices": {}}
    keys = iter(["k1"])

    new_data, key = model.ensure_device(
        data,
        device_id="dev1",
        identifiers=[["mqtt", "abc"]],
        name="Lamp",
        key_factory=lambda: next(keys),
    )

    assert key == "k1"
    assert new_data["devices"]["k1"] == {
        "device_id": "dev1",
        "identifiers": [["mqtt", "abc"]],
        "name": "Lamp",
        "log": [],
    }
    assert data == {"devices": {}}  # input not mutated


def test_ensure_device_returns_existing_key_for_known_device_id():
    data = {
        "devices": {
            "k1": {
                "device_id": "dev1",
                "identifiers": [["mqtt", "abc"]],
                "name": "Lamp",
                "log": [],
            }
        }
    }

    new_data, key = model.ensure_device(
        data,
        device_id="dev1",
        identifiers=[["mqtt", "abc"]],
        name="Lamp",
        key_factory=lambda: "SHOULD_NOT_BE_CALLED",
    )

    assert key == "k1"
    assert new_data == data


def test_ensure_device_relinks_when_device_id_rotated_but_identifiers_match():
    existing_log = [{"ts": "t", "source": "agent", "text": "hi"}]
    data = {
        "devices": {
            "k1": {
                "device_id": "old",
                "identifiers": [["mqtt", "abc"]],
                "name": "Lamp",
                "log": existing_log,
            }
        }
    }

    new_data, key = model.ensure_device(
        data,
        device_id="new",
        identifiers=[["mqtt", "abc"]],
        name="Lamp",
        key_factory=lambda: "SHOULD_NOT_BE_CALLED",
    )

    assert key == "k1"  # same record, no new key minted
    assert new_data["devices"]["k1"]["device_id"] == "new"  # relinked
    assert new_data["devices"]["k1"]["log"] == existing_log  # log preserved


def test_relink_all_updates_stale_device_ids_by_identifiers():
    data = {
        "devices": {
            "k1": {
                "device_id": "old1",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": [],
            },
            "k2": {
                "device_id": "keep2",
                "identifiers": [["mqtt", "b"]],
                "name": "B",
                "log": [],
            },
        }
    }
    current = {
        frozenset({("mqtt", "a")}): "new1",
        frozenset({("mqtt", "b")}): "keep2",
    }

    def resolver(identifiers):
        return current.get(frozenset(tuple(i) for i in identifiers))

    result = model.relink_all(data, resolver)

    assert result["devices"]["k1"]["device_id"] == "new1"  # rotated -> relinked
    assert result["devices"]["k2"]["device_id"] == "keep2"  # unchanged
    assert data["devices"]["k1"]["device_id"] == "old1"  # input not mutated


def test_relink_all_leaves_record_when_device_unresolvable():
    log = [{"ts": "t", "source": "user", "text": "x"}]
    data = {
        "devices": {
            "k1": {
                "device_id": "old1",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": log,
            }
        }
    }

    result = model.relink_all(data, lambda ids: None)

    assert result["devices"]["k1"]["device_id"] == "old1"  # kept, not dropped
    assert result["devices"]["k1"]["log"] == log  # log preserved


def test_append_note_adds_entry_to_the_record_log():
    data = {
        "devices": {
            "k1": {
                "device_id": "d",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": [],
            }
        }
    }
    entry = {"ts": "t", "source": "agent", "text": "hi"}

    result = model.append_note(data, "k1", entry)

    assert result["devices"]["k1"]["log"] == [entry]
    assert data["devices"]["k1"]["log"] == []  # input not mutated


def test_delete_last_note_removes_newest_entry():
    data = {
        "devices": {
            "k1": {
                "device_id": "d",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": [
                    {"ts": "t2", "source": "agent", "text": "new"},
                    {"ts": "t1", "source": "user", "text": "old"},
                ],
            }
        }
    }

    result = model.delete_last_note(data, "k1")

    assert [e["text"] for e in result["devices"]["k1"]["log"]] == ["old"]


def test_clear_notes_empties_the_log():
    data = {
        "devices": {
            "k1": {
                "device_id": "d",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": [{"ts": "t", "source": "agent", "text": "x"}],
            }
        }
    }

    result = model.clear_notes(data, "k1")

    assert result["devices"]["k1"]["log"] == []


def test_delete_note_at_removes_the_matching_entry():
    data = {
        "devices": {
            "k1": {
                "device_id": "d",
                "identifiers": [["mqtt", "a"]],
                "name": "A",
                "log": [
                    {"ts": "t2", "source": "agent", "text": "new"},
                    {"ts": "t1", "source": "user", "text": "old"},
                ],
            }
        }
    }

    result = model.delete_note_at(data, "k1", "t2")

    assert [e["text"] for e in result["devices"]["k1"]["log"]] == ["old"]
    assert data["devices"]["k1"]["log"][0]["text"] == "new"  # input not mutated
