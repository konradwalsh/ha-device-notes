"""HA-coupled tests for the config + options flow (device/area opt-in)."""

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import CONF_AREAS, CONF_DEVICES, DOMAIN


async def test_config_flow_creates_single_entry(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == "create_entry"
    assert result["title"] == "Device Notes"


async def test_options_flow_opts_in_device_and_creates_entities(hass):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={("demo", "z")}, name="Z Device"
    )

    entry = MockConfigEntry(domain=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flow = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        flow["flow_id"], {CONF_DEVICES: [device.id], CONF_AREAS: []}
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.options[CONF_DEVICES] == [device.id]
    # the entry reloaded and our entities landed on the device
    ours = [
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device.id, include_disabled_entities=True
        )
        if e.platform == DOMAIN
    ]
    assert {e.domain for e in ours} == {"sensor", "text"}


async def test_de_opting_a_device_removes_its_entities(hass):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={("demo", "z")}, name="Z Device"
    )
    entry = MockConfigEntry(
        domain=DOMAIN, options={CONF_DEVICES: [device.id], CONF_AREAS: []}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    def _ours():
        return [
            e
            for e in er.async_entries_for_device(
                ent_reg, device.id, include_disabled_entities=True
            )
            if e.platform == DOMAIN
        ]

    assert _ours()  # entities created while opted in

    # remove the device from the opt-in -> update listener reloads the entry
    hass.config_entries.async_update_entry(
        entry, options={CONF_DEVICES: [], CONF_AREAS: []}
    )
    await hass.async_block_till_done()

    assert not _ours()  # stale entities reconciled away
