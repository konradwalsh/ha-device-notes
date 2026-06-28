"""HA-coupled tests for resolving the effective opted-in device set."""

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import CONF_AREAS, CONF_DEVICES, DOMAIN
from custom_components.device_notes.selection import effective_device_ids


def _device(hass, ident, name, *, area_id=None):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={ident}, name=name
    )
    if area_id is not None:
        dr.async_get(hass).async_update_device(device.id, area_id=area_id)
    return device


async def test_effective_devices_includes_explicit_devices(hass):
    dev = _device(hass, ("demo", "a"), "A")
    entry = MockConfigEntry(
        domain=DOMAIN, options={CONF_DEVICES: [dev.id], CONF_AREAS: []}
    )
    entry.add_to_hass(hass)

    assert effective_device_ids(hass, entry) == {dev.id}


async def test_effective_devices_expands_selected_areas(hass):
    area = ar.async_get(hass).async_get_or_create("Test Area")
    dev = _device(hass, ("demo", "b"), "B", area_id=area.id)
    entry = MockConfigEntry(
        domain=DOMAIN, options={CONF_DEVICES: [], CONF_AREAS: [area.id]}
    )
    entry.add_to_hass(hass)

    assert dev.id in effective_device_ids(hass, entry)


async def test_effective_devices_unions_devices_and_areas(hass):
    area = ar.async_get(hass).async_get_or_create("Area 2")
    in_area = _device(hass, ("demo", "c"), "C", area_id=area.id)
    explicit = _device(hass, ("demo", "d"), "D")
    entry = MockConfigEntry(
        domain=DOMAIN, options={CONF_DEVICES: [explicit.id], CONF_AREAS: [area.id]}
    )
    entry.add_to_hass(hass)

    assert effective_device_ids(hass, entry) == {in_area.id, explicit.id}
