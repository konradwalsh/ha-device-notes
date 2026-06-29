"""HA-coupled tests for the notes sensor and its device-page attach."""

from homeassistant.const import EntityCategory
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import DOMAIN, SERVICE_APPEND, SUBENTRY_DEVICE


def _add_foreign_device(hass, *, identifiers=(("demo", "xyz"),), name="Demo Device"):
    """A device owned by some *other* integration, like a real Z2M device."""
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


def _our_sensor_entry(hass, device_id):
    ent_reg = er.async_get(hass)
    return next(
        e
        for e in er.async_entries_for_device(
            ent_reg, device_id, include_disabled_entities=True
        )
        if e.platform == DOMAIN and e.domain == "sensor"
    )


async def test_sensor_attaches_to_the_opted_in_device(hass):
    device = _add_foreign_device(hass)

    await _setup_device_notes(hass, [device.id])

    ours = [
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device.id, include_disabled_entities=True
        )
        if e.platform == DOMAIN and e.domain == "sensor"
    ]
    assert len(ours) == 1  # our notes sensor landed on the existing device
    assert ours[0].entity_category == EntityCategory.DIAGNOSTIC
    assert hass.states.get(ours[0].entity_id) is not None


async def test_sensor_reflects_appended_notes(hass):
    device = _add_foreign_device(hass)
    await _setup_device_notes(hass, [device.id])
    sensor_entry = _our_sensor_entry(hass, device.id)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_APPEND,
        {"device_id": device.id, "note": "boiler serviced"},
        blocking=True,
    )
    await hass.async_block_till_done()

    state = hass.states.get(sensor_entry.entity_id)
    assert "boiler serviced" in state.state
    assert state.attributes["log"][0]["text"] == "boiler serviced"


async def test_sensor_log_attribute_is_excluded_from_recorder(hass):
    from custom_components.device_notes.sensor import DeviceNotesSensor

    assert "log" in DeviceNotesSensor._unrecorded_attributes


async def test_sensor_entity_id_is_clean_when_device_named_after_area(hass):
    area = ar.async_get(hass).async_get_or_create("Living Room")
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id,
        identifiers={("demo", "trv")},
        name="Living Room TRV",
    )
    dr.async_get(hass).async_update_device(device.id, area_id=area.id)

    await _setup_device_notes(hass, [device.id])

    sensor_entry = _our_sensor_entry(hass, device.id)
    assert sensor_entry.entity_id == "sensor.living_room_trv_notes"
