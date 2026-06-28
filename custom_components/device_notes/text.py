"""Note-entry text input — the 'add a line' box on the device page.

This is NOT the note itself; it's an action box. Setting a value timestamps the
text, appends it to the device's log as a ``user`` entry, then clears itself.
Attaches to the existing device via copied identifiers, same as the sensor.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.text import ENTITY_ID_FORMAT, TextEntity, TextMode
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id
from homeassistant.util import dt as dt_util

from . import notelog
from .const import DOMAIN, MAX_ENTRY_CHARS, SOURCE_USER
from .selection import effective_device_ids

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .store import DeviceNotesStore

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a note-entry text box for each opted-in device."""
    store: DeviceNotesStore = hass.data[DOMAIN]["store"]
    dev_reg = dr.async_get(hass)

    entities: list[DeviceNotesEntryText] = []
    for device_id in effective_device_ids(hass, entry):
        device = dev_reg.async_get(device_id)
        if device is None:
            continue
        name = device.name_by_user or device.name
        key = await store.async_ensure(
            device_id=device_id, identifiers=device.identifiers, name=name
        )
        text_entity = DeviceNotesEntryText(
            store, key, device_id, device.identifiers, device.connections, name
        )
        # Force a clean entity_id; newer HA otherwise folds the area name in.
        text_entity.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, f"{name or device_id} Note entry", hass=hass
        )
        entities.append(text_entity)

    async_add_entities(entities)


class DeviceNotesEntryText(TextEntity):
    """An input box that appends a user line to the device's note log."""

    _attr_has_entity_name = True
    _attr_name = "Note entry"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:note-plus-outline"
    _attr_mode = TextMode.TEXT
    _attr_native_min = 0
    _attr_native_max = MAX_ENTRY_CHARS
    _attr_native_value = ""

    def __init__(
        self,
        store: DeviceNotesStore,
        key: str,
        device_id: str,
        identifiers: set,
        connections: set,
        name: str | None,
    ) -> None:
        self._store = store
        self._key = key
        self._device_id = device_id
        self._device_name = name
        self._attr_unique_id = f"{key}_note_entry"
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers, connections=connections
        )
        self._identifiers = identifiers

    async def async_set_value(self, value: str) -> None:
        """Record a non-empty line as a user note, then clear the box."""
        text = value.strip()
        if text:
            ts = dt_util.now().isoformat(timespec="seconds")
            entry = notelog.make_entry(text, source=SOURCE_USER, ts=ts)
            await self._store.async_append(
                device_id=self._device_id,
                identifiers=self._identifiers,
                name=self._device_name,
                entry=entry,
            )
            _LOGGER.debug("User note added via text box for device %s", self._device_id)
        self._attr_native_value = ""
        self.async_write_ha_state()
