"""Service handlers — the agent-facing surface.

Each service accepts EITHER ``device_id`` OR any ``entity_id`` on the target
device (resolved to its device). All note/log mechanics live in the pure
``notelog``/``model`` modules; these handlers only resolve the target, stamp the
timestamp/source, and delegate to the Store.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from . import notelog
from .const import (
    ATTR_CATEGORY,
    ATTR_COUNT,
    ATTR_DEVICE_ID,
    ATTR_ENTITY_ID,
    ATTR_ISSUES,
    ATTR_NOTE,
    ATTR_NOTES,
    ATTR_SEVERITY,
    ATTR_SOURCE,
    ATTR_TS,
    DEFAULT_SEVERITY,
    DOMAIN,
    SERVICE_APPEND,
    SERVICE_CLEAR,
    SERVICE_DELETE,
    SERVICE_DELETE_LAST,
    SERVICE_GET,
    SEVERITIES,
    SOURCE_AGENT,
)
from .store import DeviceNotesStore

_LOGGER = logging.getLogger(__name__)

_TARGET_FIELDS = {
    vol.Optional(ATTR_DEVICE_ID): cv.string,
    vol.Optional(ATTR_ENTITY_ID): cv.entity_id,
}
TARGET_SCHEMA = vol.Schema(_TARGET_FIELDS)
APPEND_SCHEMA = vol.Schema(
    {
        **_TARGET_FIELDS,
        vol.Required(ATTR_NOTE): cv.string,
        vol.Optional(ATTR_SOURCE): cv.string,
        vol.Optional(ATTR_CATEGORY): cv.string,
        vol.Optional(ATTR_SEVERITY): vol.In(SEVERITIES),
    }
)
DELETE_SCHEMA = vol.Schema({**_TARGET_FIELDS, vol.Required(ATTR_TS): cv.string})


def _resolve_device_id(hass: HomeAssistant, data: dict) -> str:
    """Resolve a target device_id from a device_id or any entity_id on it."""
    if device_id := data.get(ATTR_DEVICE_ID):
        return device_id
    if entity_id := data.get(ATTR_ENTITY_ID):
        entity = er.async_get(hass).async_get(entity_id)
        if entity is None:
            raise ServiceValidationError(f"Entity {entity_id} not found")
        if entity.device_id is None:
            raise ServiceValidationError(
                f"Entity {entity_id} is not attached to a device"
            )
        return entity.device_id
    raise ServiceValidationError("Provide either device_id or entity_id")


async def async_setup_services(hass: HomeAssistant, store: DeviceNotesStore) -> None:
    """Register the device_notes services, closing over the shared Store."""

    async def _append(call: ServiceCall) -> None:
        device_id = _resolve_device_id(hass, call.data)
        device = dr.async_get(hass).async_get(device_id)
        if device is None:
            raise ServiceValidationError(f"Device {device_id} not found")
        source = call.data.get(ATTR_SOURCE) or SOURCE_AGENT
        severity = call.data.get(ATTR_SEVERITY) or DEFAULT_SEVERITY
        ts = dt_util.now().isoformat(timespec="seconds")
        entry = notelog.make_entry(
            call.data[ATTR_NOTE],
            source=source,
            ts=ts,
            category=call.data.get(ATTR_CATEGORY),
            severity=severity,
        )
        await store.async_append(
            device_id=device_id,
            identifiers=device.identifiers,
            name=device.name_by_user or device.name,
            entry=entry,
        )
        _LOGGER.debug(
            "Service append: device=%s source=%s severity=%s",
            device_id,
            source,
            severity,
        )

    async def _get(call: ServiceCall) -> ServiceResponse:
        """Return a device's notes (newest-first) plus count + issue count.

        Read-only; lets an AI agent pull a device's history in one call instead
        of scraping the sensor's state attributes.
        """
        device_id = _resolve_device_id(hass, call.data)
        key = store.key_for_device_id(device_id)
        if key is None:
            return {ATTR_NOTES: [], ATTR_COUNT: 0, ATTR_ISSUES: 0}
        log = store.data["devices"][key]["log"]
        _LOGGER.debug("Service get: device=%s returned %d note(s)", device_id, len(log))
        return {
            ATTR_NOTES: log,
            ATTR_COUNT: len(log),
            ATTR_ISSUES: notelog.issue_count(log),
        }

    async def _clear(call: ServiceCall) -> None:
        device_id = _resolve_device_id(hass, call.data)
        key = store.key_for_device_id(device_id)
        if key is None:
            _LOGGER.warning(
                "Service clear: device %s has no notes; nothing to clear", device_id
            )
            return
        await store.async_clear(key)

    async def _delete_last(call: ServiceCall) -> None:
        device_id = _resolve_device_id(hass, call.data)
        key = store.key_for_device_id(device_id)
        if key is None:
            _LOGGER.warning("Service delete_last: device %s has no notes", device_id)
            return
        await store.async_delete_last(key)

    async def _delete(call: ServiceCall) -> None:
        device_id = _resolve_device_id(hass, call.data)
        key = store.key_for_device_id(device_id)
        if key is None:
            _LOGGER.warning("Service delete: device %s has no notes", device_id)
            return
        await store.async_delete_at(key, call.data[ATTR_TS])

    hass.services.async_register(DOMAIN, SERVICE_APPEND, _append, schema=APPEND_SCHEMA)
    hass.services.async_register(
        DOMAIN,
        SERVICE_GET,
        _get,
        schema=TARGET_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(DOMAIN, SERVICE_CLEAR, _clear, schema=TARGET_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_LAST, _delete_last, schema=TARGET_SCHEMA
    )
    hass.services.async_register(DOMAIN, SERVICE_DELETE, _delete, schema=DELETE_SCHEMA)
    _LOGGER.debug("Registered device_notes services")


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the device_notes services."""
    for service in (
        SERVICE_APPEND,
        SERVICE_GET,
        SERVICE_CLEAR,
        SERVICE_DELETE_LAST,
        SERVICE_DELETE,
    ):
        hass.services.async_remove(DOMAIN, service)
