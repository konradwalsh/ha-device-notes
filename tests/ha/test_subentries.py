"""HA-coupled tests for the subentry-based opt-in (per device / per area)."""

from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import DOMAIN, SUBENTRY_AREA, SUBENTRY_DEVICE


def _foreign_device(hass, ident=("demo", "z"), name="Z Device", area_id=None):
    cfg = MockConfigEntry(domain="demo")
    cfg.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=cfg.entry_id, identifiers={ident}, name=name
    )
    if area_id is not None:
        dr.async_get(hass).async_update_device(device.id, area_id=area_id)
    return device


def _device_subentry(device_id, title="Z Device"):
    return {
        "subentry_type": SUBENTRY_DEVICE,
        "data": {"device_id": device_id},
        "title": title,
        "unique_id": None,
    }


def _area_subentry(area_id, title="Area"):
    return {
        "subentry_type": SUBENTRY_AREA,
        "data": {"area_id": area_id},
        "title": title,
        "unique_id": None,
    }


def _ours(hass, device_id):
    return [
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device_id, include_disabled_entities=True
        )
        if e.platform == DOMAIN
    ]


async def test_device_subentry_creates_entities_on_the_device(hass):
    device = _foreign_device(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, subentries_data=[_device_subentry(device.id)]
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert {e.domain for e in _ours(hass, device.id)} == {"sensor", "text", "button"}


async def test_removing_a_subentry_removes_its_entities(hass):
    device = _foreign_device(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, subentries_data=[_device_subentry(device.id)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert _ours(hass, device.id)

    subentry_id = next(iter(entry.subentries))
    hass.config_entries.async_remove_subentry(entry, subentry_id)
    await hass.async_block_till_done()

    assert not _ours(hass, device.id)


async def test_effective_set_unions_device_and_area_subentries(hass):
    area = ar.async_get(hass).async_get_or_create("Union Area")
    in_area = _foreign_device(hass, ident=("demo", "ua"), name="UA", area_id=area.id)
    explicit = _foreign_device(hass, ident=("demo", "ue"), name="UE")
    entry = MockConfigEntry(
        domain=DOMAIN,
        subentries_data=[_device_subentry(explicit.id), _area_subentry(area.id)],
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert {e.domain for e in _ours(hass, in_area.id)} == {"sensor", "text", "button"}
    assert {e.domain for e in _ours(hass, explicit.id)} == {"sensor", "text", "button"}


async def test_action_buttons_appear_and_work(hass):
    device = _foreign_device(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, subentries_data=[_device_subentry(device.id)]
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    buttons = [
        e
        for e in er.async_entries_for_device(
            er.async_get(hass), device.id, include_disabled_entities=True
        )
        if e.platform == DOMAIN and e.domain == "button"
    ]
    assert len(buttons) == 2  # delete last + clear

    store = hass.data[DOMAIN]["store"]
    key = store.key_for_device_id(device.id)
    await store.async_append(
        device_id=device.id,
        identifiers=device.identifiers,
        name="Z",
        entry={"ts": "t1", "source": "agent", "text": "a"},
    )

    delete_btn = next(b for b in buttons if b.unique_id.endswith("_delete_last"))
    await hass.services.async_call(
        "button", "press", {"entity_id": delete_btn.entity_id}, blocking=True
    )
    await hass.async_block_till_done()

    assert store.data["devices"][key]["log"] == []


async def test_area_subentry_creates_entities_for_devices_in_area(hass):
    area = ar.async_get(hass).async_get_or_create("Test Area")
    device = _foreign_device(hass, ident=("demo", "a"), name="A", area_id=area.id)
    entry = MockConfigEntry(domain=DOMAIN, subentries_data=[_area_subentry(area.id)])
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert {e.domain for e in _ours(hass, device.id)} == {"sensor", "text", "button"}
