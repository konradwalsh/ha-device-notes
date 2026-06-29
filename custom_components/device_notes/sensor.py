"""Notes sensor — the at-a-glance note log rendered on the device page.

Attaches to an existing device by copying its registry identifiers into
``DeviceInfo`` (the PowerCalc / Battery-Notes pattern), so it renders on that
device's own page. ``state`` is a short preview of the latest entry;
``attributes.log`` holds the full newest-first list and is kept out of the
recorder.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, async_generate_entity_id

from . import notelog
from .const import ATTR_LOG, DOMAIN, SIGNAL_NOTES_UPDATED
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
    """Create a notes sensor for each opted-in device."""
    store: DeviceNotesStore = hass.data[DOMAIN]["store"]
    dev_reg = dr.async_get(hass)

    for subentry_id, subentry in entry.subentries.items():
        entities: list[SensorEntity] = []
        for device_id in devices_for_subentry(hass, subentry):
            device = dev_reg.async_get(device_id)
            if device is None:
                _LOGGER.warning(
                    "Opted-in device %s not in registry; skipping its notes sensor",
                    device_id,
                )
                continue
            name = device.name_by_user or device.name
            key = await store.async_ensure(
                device_id=device_id, identifiers=device.identifiers, name=name
            )
            sensor = DeviceNotesSensor(
                store, key, device.identifiers, device.connections
            )
            # Force a clean entity_id; newer HA otherwise folds the area name in.
            sensor.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, f"{name or device_id} Notes", hass=hass
            )
            issues = DeviceNotesIssuesSensor(
                store, key, device.identifiers, device.connections
            )
            issues.entity_id = async_generate_entity_id(
                ENTITY_ID_FORMAT, f"{name or device_id} Note issues", hass=hass
            )
            entities.extend((sensor, issues))
        if entities:
            async_add_entities(entities, config_subentry_id=subentry_id)


class DeviceNotesSensor(SensorEntity):
    """A diagnostic sensor exposing a device's note log."""

    _attr_has_entity_name = True
    _attr_name = "Notes"
    # All Device Notes entities share DIAGNOSTIC so they group in one device-page
    # section (HA forbids sensors in CONFIG). Recorder exclusion is separate, below.
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:note-text-outline"
    # Keep the (large, frequently-changing) log out of the recorder DB.
    _unrecorded_attributes = frozenset({ATTR_LOG})

    def __init__(
        self,
        store: DeviceNotesStore,
        key: str,
        identifiers: set,
        connections: set,
    ) -> None:
        self._store = store
        self._key = key
        self._attr_unique_id = f"{key}_notes"
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers, connections=connections
        )

    @property
    def _log(self) -> list[dict]:
        record = self._store.data["devices"].get(self._key)
        return record["log"] if record else []

    @property
    def native_value(self) -> str:
        return notelog.preview(self._log) or "No notes yet"

    @property
    def extra_state_attributes(self) -> dict:
        log = self._log
        return {ATTR_LOG: log, "count": len(log)}

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NOTES_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self, key: str) -> None:
        if key == self._key:
            self.async_write_ha_state()


class DeviceNotesIssuesSensor(SensorEntity):
    """Count of open issues (notes with warning/error severity) on a device."""

    _attr_has_entity_name = True
    _attr_name = "Notes: issues"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:alert-circle-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        store: DeviceNotesStore,
        key: str,
        identifiers: set,
        connections: set,
    ) -> None:
        self._store = store
        self._key = key
        self._attr_unique_id = f"{key}_issues"
        self._attr_device_info = DeviceInfo(
            identifiers=identifiers, connections=connections
        )

    @property
    def _log(self) -> list[dict]:
        record = self._store.data["devices"].get(self._key)
        return record["log"] if record else []

    @property
    def native_value(self) -> int:
        return notelog.issue_count(self._log)

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, SIGNAL_NOTES_UPDATED, self._handle_update
            )
        )

    @callback
    def _handle_update(self, key: str) -> None:
        if key == self._key:
            self.async_write_ha_state()
