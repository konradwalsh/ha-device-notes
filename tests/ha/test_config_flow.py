"""HA-coupled tests for the config flow and the device/area subentry flows."""

from homeassistant.config_entries import SOURCE_USER
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import DOMAIN, SUBENTRY_DEVICE


async def test_config_flow_menu_walkthrough_and_setup(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] == "menu"

    # take the walkthrough: tutorial -> tutorial2 -> back to the menu
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "tutorial"}
    )
    assert result["type"] == "form" and result["step_id"] == "tutorial"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "tutorial2"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] == "menu"

    # then set up
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "setup"}
    )
    assert result["type"] == "create_entry"
    assert result["title"] == "Device Notes"


async def test_device_subentry_flow_adds_subentry_and_entities(hass):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={("demo", "z")}, name="Z Device"
    )

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_DEVICE), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {"device_id": device.id}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert any(
        s.subentry_type == SUBENTRY_DEVICE and s.data["device_id"] == device.id
        for s in entry.subentries.values()
    )
    ours = [
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device.id, include_disabled_entities=True
        )
        if e.platform == DOMAIN
    ]
    assert {e.domain for e in ours} == {"sensor", "text", "button"}
