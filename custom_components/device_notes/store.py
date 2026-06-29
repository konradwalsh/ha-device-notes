"""Async persistence wrapper around ``helpers.storage.Store``.

Thin, logged adapter: all note/device-link logic lives in the pure ``model``
module; this class only loads/saves the persisted dict and applies those pure
ops. Keyed by a stable internal uuid (see ``model``), never by ``device_id``.
Mutations fire ``SIGNAL_NOTES_UPDATED(key)`` so entities can refresh.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterable
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.storage import Store

from . import model
from .const import (
    ATTR_DEVICE_ID,
    EVENT_NOTE_ADDED,
    SIGNAL_NOTES_UPDATED,
    STORAGE_KEY,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)


class DeviceNotesStore:
    """Loads/persists device-note records and applies pure model operations."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._data: dict = {"devices": {}}

    @property
    def data(self) -> dict:
        return self._data

    async def async_load(self) -> dict:
        stored = await self._store.async_load()
        if stored is not None:
            self._data = stored
        _LOGGER.debug("Loaded %d device-note record(s)", len(self._data["devices"]))
        return self._data

    async def _async_save(self) -> None:
        await self._store.async_save(self._data)

    async def async_ensure(
        self, *, device_id: str, identifiers: Iterable, name: str | None
    ) -> str:
        """Ensure a record exists for the device (mint/relink); persist; return key."""
        self._data, key = model.ensure_device(
            self._data,
            device_id=device_id,
            identifiers=identifiers,
            name=name,
            key_factory=lambda: uuid4().hex,
        )
        await self._async_save()
        return key

    async def async_append(
        self,
        *,
        device_id: str,
        identifiers: Iterable,
        name: str | None,
        entry: dict,
    ) -> str:
        """Ensure a record for the device (mint/relink), append, persist."""
        self._data, key = model.ensure_device(
            self._data,
            device_id=device_id,
            identifiers=identifiers,
            name=name,
            key_factory=lambda: uuid4().hex,
        )
        self._data = model.append_note(self._data, key, entry)
        await self._async_save()
        _LOGGER.debug(
            "Appended note for device %s (key %s); log now %d entries",
            device_id,
            key,
            len(self._data["devices"][key]["log"]),
        )
        async_dispatcher_send(self._hass, SIGNAL_NOTES_UPDATED, key)
        # Surface on the event bus so automations can react to new notes. Covers
        # every append path (service, device-page text box, card) since they all
        # funnel through here.
        self._hass.bus.async_fire(
            EVENT_NOTE_ADDED, {ATTR_DEVICE_ID: device_id, "key": key, **entry}
        )
        return key

    def key_for_device_id(self, device_id: str) -> str | None:
        """Return the record key for a device_id, or None if not tracked."""
        return model.find_key_by_device_id(self._data, device_id)

    async def async_clear(self, key: str) -> None:
        """Wipe a record's whole log and persist."""
        self._data = model.clear_notes(self._data, key)
        await self._async_save()
        _LOGGER.debug("Cleared notes for key %s", key)
        async_dispatcher_send(self._hass, SIGNAL_NOTES_UPDATED, key)

    async def async_delete_last(self, key: str) -> None:
        """Remove a record's newest entry (undo) and persist."""
        self._data = model.delete_last_note(self._data, key)
        await self._async_save()
        _LOGGER.debug("Deleted last note for key %s", key)
        async_dispatcher_send(self._hass, SIGNAL_NOTES_UPDATED, key)

    async def async_delete_at(self, key: str, ts: str) -> None:
        """Remove a specific entry (by ts) from a record and persist."""
        self._data = model.delete_note_at(self._data, key, ts)
        await self._async_save()
        _LOGGER.debug("Deleted note %s for key %s", ts, key)
        async_dispatcher_send(self._hass, SIGNAL_NOTES_UPDATED, key)

    async def async_relink(
        self, current_device_id_for: Callable[[Iterable], str | None]
    ) -> None:
        """Refresh stale device_ids from identifiers on startup, then persist."""
        before = {k: v["device_id"] for k, v in self._data["devices"].items()}
        self._data = model.relink_all(self._data, current_device_id_for)
        for k, rec in self._data["devices"].items():
            if before.get(k) != rec["device_id"]:
                _LOGGER.warning(
                    "Re-linked notes %s: device_id %s -> %s",
                    k,
                    before.get(k),
                    rec["device_id"],
                )
        await self._async_save()
