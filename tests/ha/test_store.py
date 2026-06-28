"""HA-coupled tests for the async Store wrapper (real helpers.storage.Store)."""

from custom_components.device_notes.store import DeviceNotesStore


async def test_append_persists_and_reloads(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()

    key = await store.async_append(
        device_id="dev1",
        identifiers={("mqtt", "abc")},
        name="Lamp",
        entry={"ts": "t", "source": "agent", "text": "hello"},
    )
    await hass.async_block_till_done()

    # A fresh wrapper reads back the persisted data.
    fresh = DeviceNotesStore(hass)
    data = await fresh.async_load()

    assert data["devices"][key]["device_id"] == "dev1"
    assert data["devices"][key]["log"] == [
        {"ts": "t", "source": "agent", "text": "hello"}
    ]


async def _seed(store, *, device_id="d", text="x", ts="t"):
    return await store.async_append(
        device_id=device_id,
        identifiers={("mqtt", "a")},
        name="A",
        entry={"ts": ts, "source": "agent", "text": text},
    )


async def test_clear_empties_a_record_log(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()
    key = await _seed(store)

    await store.async_clear(key)
    await hass.async_block_till_done()

    assert store.data["devices"][key]["log"] == []


async def test_delete_last_removes_the_newest_entry(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()
    key = await _seed(store, text="old", ts="t1")
    await _seed(store, text="new", ts="t2")

    await store.async_delete_last(key)
    await hass.async_block_till_done()

    assert [e["text"] for e in store.data["devices"][key]["log"]] == ["old"]


async def test_key_for_device_id_returns_the_record_key(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()
    key = await _seed(store, device_id="d")

    assert store.key_for_device_id("d") == key
    assert store.key_for_device_id("unknown") is None


async def test_relink_updates_device_id_by_identifiers(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()
    key = await _seed(store, device_id="old")

    def resolver(identifiers):
        match = frozenset(tuple(i) for i in identifiers) == frozenset({("mqtt", "a")})
        return "new" if match else None

    await store.async_relink(resolver)
    await hass.async_block_till_done()

    assert store.data["devices"][key]["device_id"] == "new"


async def test_ensure_creates_a_record_without_a_note(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()

    key = await store.async_ensure(device_id="d", identifiers={("mqtt", "a")}, name="A")

    assert store.data["devices"][key]["log"] == []
    assert store.key_for_device_id("d") == key
