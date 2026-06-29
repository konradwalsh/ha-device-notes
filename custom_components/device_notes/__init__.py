"""The Device Notes integration.

Attaches a free-text, append-only, timestamped note log to opted-in devices,
rendered inline on each device's own page via two entities (a note sensor and
a one-line input box).

Step 1 scaffold: this only stands up the config entry so the integration loads.
Store, services, and entity platforms are wired in later build steps.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

CARD_URL = f"/{DOMAIN}/device-notes-card.js"
_CARD_REGISTERED = f"{DOMAIN}_card_registered"

PLATFORMS: list[str] = ["sensor", "text", "button"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Device Notes from a config entry."""
    # Imported here, not at module top, so the package stays importable without
    # Home Assistant for the pure-logic unit tests.
    from homeassistant.helpers import device_registry as dr

    from .services import async_setup_services
    from .store import DeviceNotesStore

    store = DeviceNotesStore(hass)
    await store.async_load()

    # Re-link any records whose device_id rotated (e.g. integration re-add) by
    # their stored identifiers, so existing notes stay attached to the device.
    dev_reg = dr.async_get(hass)

    def _current_device_id(identifiers: list) -> str | None:
        device = dev_reg.async_get_device(identifiers={tuple(i) for i in identifiers})
        return device.id if device else None

    await store.async_relink(_current_device_id)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["store"] = store

    await async_setup_services(hass, store)
    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Remove entities/device links for devices that are no longer opted in.
    _async_reconcile_entities(hass, entry)

    # Reload when the opt-in selection changes so entities are added/removed.
    entry.async_on_unload(entry.add_update_listener(_async_reload_on_update))

    _LOGGER.info(
        "Device Notes set up (%d tracked device(s))", len(store.data["devices"])
    )
    return True


async def _async_reload_on_update(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when its options (opted-in devices/areas) change."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_reconcile_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Drop entities + device links for devices no longer opted in.

    Notes are intentionally left in the Store, so re-adding a device restores
    its log (re-linked by identifiers).
    """
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    from .selection import effective_device_ids

    keep = effective_device_ids(hass, entry)

    ent_reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if ent.device_id not in keep:
            ent_reg.async_remove(ent.entity_id)
            _LOGGER.debug("Removed de-opted entity %s", ent.entity_id)

    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if device.id not in keep:
            dev_reg.async_update_device(
                device.id, remove_config_entry_id=entry.entry_id
            )
            _LOGGER.debug("Detached from de-opted device %s", device.id)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve and auto-load the bundled Lovelace card (best-effort, once)."""
    if hass.data.get(_CARD_REGISTERED):
        return
    try:
        from pathlib import Path

        from homeassistant.components import frontend
        from homeassistant.components.http import StaticPathConfig

        card_path = str(Path(__file__).parent / "device-notes-card.js")
        await hass.http.async_register_static_paths(
            [StaticPathConfig(CARD_URL, card_path, False)]
        )
        frontend.add_extra_js_url(hass, CARD_URL)
        hass.data[_CARD_REGISTERED] = True
        _LOGGER.debug("Registered Device Notes Lovelace card at %s", CARD_URL)
    except Exception as err:  # best-effort; a card failure must not block setup
        _LOGGER.warning("Could not register Device Notes Lovelace card: %s", err)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    from .services import async_unload_services

    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_unload_services(hass)
        hass.data.pop(DOMAIN, None)
    return unloaded
