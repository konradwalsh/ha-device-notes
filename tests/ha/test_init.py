"""HA-coupled tests for integration setup/unload wiring."""

from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import (
    DOMAIN,
    SERVICE_APPEND,
    SERVICE_CLEAR,
    SERVICE_DELETE_LAST,
)
from custom_components.device_notes.store import DeviceNotesStore


async def test_setup_entry_registers_services(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, SERVICE_APPEND)
    assert hass.services.has_service(DOMAIN, SERVICE_CLEAR)
    assert hass.services.has_service(DOMAIN, SERVICE_DELETE_LAST)


async def test_unload_entry_removes_services(hass):
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, SERVICE_APPEND)


async def test_setup_relinks_stale_device_id_by_identifiers(hass):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={("demo", "relink")}, name="R"
    )

    # Persist a record whose device_id is stale but whose identifiers still
    # match the live device (the device_id-rotation failure mode).
    seed = DeviceNotesStore(hass)
    await seed.async_load()
    key = await seed.async_ensure(
        device_id="STALE", identifiers={("demo", "relink")}, name="R"
    )
    await hass.async_block_till_done()

    # On setup, the integration should re-link STALE -> the current device_id.
    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    store = hass.data[DOMAIN]["store"]
    assert store.data["devices"][key]["device_id"] == device.id
