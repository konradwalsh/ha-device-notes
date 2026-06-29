"""Action buttons on the device page: delete last note, clear notes.

No-input actions (the text box handles adding). Each button calls the matching
Store action for its device; attached to the device via copied identifiers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.button import ENTITY_ID_FORMAT, ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id

from .const import DOMAIN
from .selection import devices_for_subentry

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
    """Create the action buttons for each opted-in device."""
    store: DeviceNotesStore = hass.data[DOMAIN]["store"]
    dev_reg = dr.async_get(hass)

    for subentry_id, subentry in entry.subentries.items():
        entities: list[_DeviceNotesButton] = []
        for device_id in devices_for_subentry(hass, subentry):
            device = dev_reg.async_get(device_id)
            if device is None:
                continue
            name = device.name_by_user or device.name
            key = await store.async_ensure(
                device_id=device_id, identifiers=device.identifiers, name=name
            )
            for cls, label in (
                (DeleteLastNoteButton, "Delete last note"),
                (ClearNotesButton, "Clear notes"),
            ):
                button = cls(store, key, device.identifiers, device.connections)
                button.entity_id = async_generate_entity_id(
                    ENTITY_ID_FORMAT, f"{name or device_id} {label}", hass=hass
                )
                entities.append(button)
        if entities:
            async_add_entities(entities, config_subentry_id=subentry_id)


class _DeviceNotesButton(ButtonEntity):
    """Base for Device Notes action buttons."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, store: DeviceNotesStore, key: str, identifiers: set, connections: set
    ) -> None:
        self._store = store
        self._key = key
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers, connections=connections
        )


class DeleteLastNoteButton(_DeviceNotesButton):
    """Remove the most recent note."""

    _attr_name = "Delete last note"
    _attr_icon = "mdi:undo-variant"

    def __init__(self, store, key, identifiers, connections) -> None:
        super().__init__(store, key, identifiers, connections)
        self._attr_unique_id = f"{key}_delete_last"

    async def async_press(self) -> None:
        await self._store.async_delete_last(self._key)


class ClearNotesButton(_DeviceNotesButton):
    """Wipe the whole log."""

    _attr_name = "Clear notes"
    _attr_icon = "mdi:notification-clear-all"

    def __init__(self, store, key, identifiers, connections) -> None:
        super().__init__(store, key, identifiers, connections)
        self._attr_unique_id = f"{key}_clear"

    async def async_press(self) -> None:
        await self._store.async_clear(self._key)
