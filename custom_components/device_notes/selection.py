"""Resolve the effective opted-in device set from a config entry.

Opt-in is stored as ``{devices: [...], areas: [...]}`` (in options once
configured, else data). The effective set is computed LIVE: the explicitly
chosen devices UNION every device currently in a chosen area — so a device
added to an opted-in area later is picked up on the next reload without
re-editing the selection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr

from .const import CONF_AREAS, CONF_DEVICES

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


def selected(entry: ConfigEntry) -> tuple[list[str], list[str]]:
    """Return (device_ids, area_ids) from options (preferred) or data."""
    src = entry.options or entry.data
    return src.get(CONF_DEVICES, []), src.get(CONF_AREAS, [])


def effective_device_ids(hass: HomeAssistant, entry: ConfigEntry) -> set[str]:
    """Explicit devices plus every device in any selected area."""
    device_ids, area_ids = selected(entry)
    result = set(device_ids)
    if area_ids:
        dev_reg = dr.async_get(hass)
        for area_id in area_ids:
            for device in dr.async_entries_for_area(dev_reg, area_id):
                result.add(device.id)
    return result
