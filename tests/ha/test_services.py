"""HA-coupled tests for the service surface (append/clear/delete_last)."""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import (
    DOMAIN,
    EVENT_NOTE_ADDED,
    SERVICE_APPEND,
    SERVICE_CLEAR,
    SERVICE_DELETE,
    SERVICE_DELETE_LAST,
)
from custom_components.device_notes.services import async_setup_services
from custom_components.device_notes.store import DeviceNotesStore


def _add_device(hass, *, identifiers=(("demo", "xyz"),), name="Demo Device"):
    entry = MockConfigEntry(domain="demo")
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={tuple(i) for i in identifiers},
        name=name,
    )
    return entry, device


async def _setup(hass):
    store = DeviceNotesStore(hass)
    await store.async_load()
    await async_setup_services(hass, store)
    return store


async def test_append_via_device_id_defaults_source_to_agent(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {"device_id": device.id, "note": "hello from agent"},
        blocking=True,
    )

    key = store.key_for_device_id(device.id)
    assert key is not None
    entry = store.data["devices"][key]["log"][0]
    assert entry["text"] == "hello from agent"
    assert entry["source"] == "agent"


async def test_append_via_entity_id_resolves_to_device(hass):
    entry_cfg, device = _add_device(hass)
    ent = er.async_get(hass).async_get_or_create(
        "sensor", "demo", "unique-1", config_entry=entry_cfg, device_id=device.id
    )
    store = await _setup(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {"entity_id": ent.entity_id, "note": "via entity"},
        blocking=True,
    )

    key = store.key_for_device_id(device.id)
    assert store.data["devices"][key]["log"][0]["text"] == "via entity"


async def test_append_passes_through_explicit_source(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {"device_id": device.id, "note": "human note", "source": "user"},
        blocking=True,
    )

    key = store.key_for_device_id(device.id)
    assert store.data["devices"][key]["log"][0]["source"] == "user"


async def test_append_records_category_and_severity(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {
            "device_id": device.id,
            "note": "valve stuck open",
            "category": "maintenance",
            "severity": "error",
        },
        blocking=True,
    )

    key = store.key_for_device_id(device.id)
    entry = store.data["devices"][key]["log"][0]
    assert entry["category"] == "maintenance"
    assert entry["severity"] == "error"


async def test_append_defaults_severity_to_info(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)

    await hass.services.async_call(
        DOMAIN, SERVICE_APPEND, {"device_id": device.id, "note": "fyi"}, blocking=True
    )

    key = store.key_for_device_id(device.id)
    assert store.data["devices"][key]["log"][0]["severity"] == "info"


async def test_append_fires_note_added_event(hass):
    _, device = _add_device(hass)
    await _setup(hass)

    events = []
    hass.bus.async_listen(EVENT_NOTE_ADDED, events.append)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {"device_id": device.id, "note": "leak detected", "severity": "warning"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert len(events) == 1
    data = events[0].data
    assert data["device_id"] == device.id
    assert data["text"] == "leak detected"
    assert data["severity"] == "warning"


async def test_clear_service_empties_the_log(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)
    await hass.services.async_call(
        DOMAIN, SERVICE_APPEND, {"device_id": device.id, "note": "x"}, blocking=True
    )

    await hass.services.async_call(
        DOMAIN, SERVICE_CLEAR, {"device_id": device.id}, blocking=True
    )

    key = store.key_for_device_id(device.id)
    assert store.data["devices"][key]["log"] == []


async def test_delete_last_service_removes_newest(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)
    await hass.services.async_call(
        DOMAIN, SERVICE_APPEND, {"device_id": device.id, "note": "old"}, blocking=True
    )
    await hass.services.async_call(
        DOMAIN, SERVICE_APPEND, {"device_id": device.id, "note": "new"}, blocking=True
    )

    await hass.services.async_call(
        DOMAIN, SERVICE_DELETE_LAST, {"device_id": device.id}, blocking=True
    )

    key = store.key_for_device_id(device.id)
    assert [e["text"] for e in store.data["devices"][key]["log"]] == ["old"]


async def test_delete_service_removes_a_specific_entry(hass):
    _, device = _add_device(hass)
    store = await _setup(hass)
    await store.async_append(
        device_id=device.id,
        identifiers=device.identifiers,
        name="Demo",
        entry={"ts": "2026-01-01T00:00:01", "source": "agent", "text": "first"},
    )
    await store.async_append(
        device_id=device.id,
        identifiers=device.identifiers,
        name="Demo",
        entry={"ts": "2026-01-01T00:00:02", "source": "agent", "text": "second"},
    )

    await hass.services.async_call(
        DOMAIN,
        SERVICE_DELETE,
        {"device_id": device.id, "ts": "2026-01-01T00:00:01"},
        blocking=True,
    )

    key = store.key_for_device_id(device.id)
    assert [e["text"] for e in store.data["devices"][key]["log"]] == ["second"]
