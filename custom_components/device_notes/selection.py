"""Resolve which devices a Device Notes opt-in (subentry) covers.

A ``device`` subentry covers exactly its device; an ``area`` subentry covers every
device currently in that area (resolved live, so devices added to the area later
are picked up on the next reload).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr

from .const import ATTR_DEVICE_ID, CONF_AREA_ID, SUBENTRY_AREA, SUBENTRY_DEVICE

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry, ConfigSubentry
    from homeassistant.core import HomeAssistant


def devices_for_subentry(hass: HomeAssistant, subentry: ConfigSubentry) -> set[str]:
    """Return the device ids covered by a single subentry."""
    if subentry.subentry_type == SUBENTRY_DEVICE:
        device_id = subentry.data.get(ATTR_DEVICE_ID)
        return {device_id} if device_id else set()
    if subentry.subentry_type == SUBENTRY_AREA:
        area_id = subentry.data.get(CONF_AREA_ID)
        if not area_id:
            return set()
        dev_reg = dr.async_get(hass)
        return {device.id for device in dr.async_entries_for_area(dev_reg, area_id)}
    return set()


def effective_device_ids(hass: HomeAssistant, entry: ConfigEntry) -> set[str]:
    """Union of devices covered across all of the entry's subentries."""
    result: set[str] = set()
    for subentry in entry.subentries.values():
        result |= devices_for_subentry(hass, subentry)
    return result
