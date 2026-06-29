"""HA-coupled tests for the note-entry text input (append-on-set + self-clear)."""

from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import DOMAIN, SUBENTRY_DEVICE


def _add_foreign_device(hass, *, identifiers=(("demo", "xyz"),), name="Demo Device"):
    entry = MockConfigEntry(domain="demo")
    entry.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={tuple(i) for i in identifiers},
        name=name,
    )


async def _setup_device_notes(hass, device_ids):
    subentries = [
        {
            "subentry_type": SUBENTRY_DEVICE,
            "data": {"device_id": d},
            "title": "Device",
            "unique_id": None,
        }
        for d in device_ids
    ]
    entry = MockConfigEntry(domain=DOMAIN, subentries_data=subentries)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _entry_for(hass, device_id, domain):
    return next(
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device_id, include_disabled_entities=True
        )
        if e.platform == DOMAIN and e.domain == domain
    )


async def test_text_entry_attaches_as_diagnostic(hass):
    device = _add_foreign_device(hass)
    await _setup_device_notes(hass, [device.id])

    text_entry = _entry_for(hass, device.id, "text")
    assert text_entry.entity_category == EntityCategory.DIAGNOSTIC


async def test_setting_text_appends_user_note_and_clears(hass):
    device = _add_foreign_device(hass)
    await _setup_device_notes(hass, [device.id])
    text_entry = _entry_for(hass, device.id, "text")

    await hass.services.async_call(
        "text",
        "set_value",
        {"entity_id": text_entry.entity_id, "value": "leaking valve"},
        blocking=True,
    )
    await hass.async_block_till_done()

    store = hass.data[DOMAIN]["store"]
    key = store.key_for_device_id(device.id)
    log = store.data["devices"][key]["log"]
    assert log[0]["text"] == "leaking valve"
    assert log[0]["source"] == "user"
    # the input box clears itself after recording the line
    assert hass.states.get(text_entry.entity_id).state == ""


async def test_setting_blank_text_is_ignored(hass):
    device = _add_foreign_device(hass)
    await _setup_device_notes(hass, [device.id])
    text_entry = _entry_for(hass, device.id, "text")

    await hass.services.async_call(
        "text",
        "set_value",
        {"entity_id": text_entry.entity_id, "value": "   "},
        blocking=True,
    )
    await hass.async_block_till_done()

    store = hass.data[DOMAIN]["store"]
    key = store.key_for_device_id(device.id)
    assert store.data["devices"][key]["log"] == []
