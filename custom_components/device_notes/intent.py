"""Assist / LLM intents: add and read device notes by voice or chat.

Home Assistant's Assist LLM API automatically turns every registered intent
into a callable tool (one ``IntentTool`` per intent), so simply registering
these makes them available to a voice/chat assistant with no extra setup —
"add a note to the living room TRV: valve sticking" just works. ``platforms``
is left ``None`` so the tools are always offered regardless of which entities
are exposed.

Intent names are CamelCase (like the built-in ``HassTurnOn``) because the LLM
tool name is ``slugify(intent_type, lowercase=False)`` and must round-trip back
to the registered handler.
"""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import intent
from homeassistant.util import dt as dt_util

from . import notelog
from .const import DEFAULT_SEVERITY, DOMAIN, SEVERITIES, SOURCE_AGENT

_LOGGER = logging.getLogger(__name__)

INTENT_ADD_NOTE = "DeviceNotesAddNote"
INTENT_GET_NOTES = "DeviceNotesGetNotes"


def _resolve_device_id(hass: HomeAssistant, name: str) -> str | None:
    """Resolve a device_id from a spoken/typed device name.

    Exact (case-insensitive) match on the device's name first; falls back to an
    entity with that friendly name and uses its device. Returns None if nothing
    matches.
    """
    target = name.strip().casefold()
    if not target:
        return None

    dev_reg = dr.async_get(hass)
    for device in dev_reg.devices.values():
        for candidate in (device.name_by_user, device.name):
            if candidate and candidate.casefold() == target:
                return device.id

    ent_reg = er.async_get(hass)
    for ent in ent_reg.entities.values():
        candidate = ent.name or ent.original_name
        if candidate and candidate.casefold() == target and ent.device_id:
            return ent.device_id

    return None


def _device_name(hass: HomeAssistant, device_id: str) -> str:
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        return "the device"
    return device.name_by_user or device.name or "the device"


class _DeviceNotesIntent(intent.IntentHandler):
    """Base: shared device-name slot + store access."""

    platforms = None  # always exposed to the LLM, regardless of entity exposure

    def _store(self, hass: HomeAssistant):
        return (hass.data.get(DOMAIN) or {}).get("store")


class AddNoteIntentHandler(_DeviceNotesIntent):
    """Append a note to a device's log."""

    intent_type = INTENT_ADD_NOTE
    description = (
        "Add a note to a device's append-only note log. Use when the user wants "
        "to record, log, or remember an observation, issue, or maintenance action "
        "about a specific device."
    )

    @property
    def slot_schema(self) -> dict:
        return {
            vol.Required(
                "name", description="Name of the device to add the note to"
            ): intent.non_empty_string,
            vol.Required(
                "note", description="The note text to record"
            ): intent.non_empty_string,
            vol.Optional(
                "severity",
                description="Signal level: info, warning, or error",
            ): vol.In(SEVERITIES),
            vol.Optional(
                "category", description="Optional grouping label, e.g. maintenance"
            ): cv.string,
        }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        name = slots["name"]["value"]
        note = slots["note"]["value"]
        severity = slots.get("severity", {}).get("value") or DEFAULT_SEVERITY
        category = slots.get("category", {}).get("value")

        response = intent_obj.create_response()
        store = self._store(hass)
        device_id = _resolve_device_id(hass, name)
        if store is None or device_id is None:
            response.async_set_speech(f"I couldn't find a device called {name}.")
            return response

        device = dr.async_get(hass).async_get(device_id)
        ts = dt_util.now().isoformat(timespec="seconds")
        entry = notelog.make_entry(
            note, source=SOURCE_AGENT, ts=ts, category=category, severity=severity
        )
        await store.async_append(
            device_id=device_id,
            identifiers=device.identifiers,
            name=device.name_by_user or device.name,
            entry=entry,
        )
        _LOGGER.debug(
            "Intent added note to device %s (severity %s)", device_id, severity
        )
        response.async_set_speech(f"Added a note to {_device_name(hass, device_id)}.")
        return response


class GetNotesIntentHandler(_DeviceNotesIntent):
    """Read back a device's notes."""

    intent_type = INTENT_GET_NOTES
    description = (
        "Read back the notes recorded on a device. Use when the user asks what "
        "notes, history, or issues exist for a specific device."
    )

    @property
    def slot_schema(self) -> dict:
        return {
            vol.Required(
                "name", description="Name of the device to read notes from"
            ): intent.non_empty_string,
        }

    async def async_handle(self, intent_obj: intent.Intent) -> intent.IntentResponse:
        hass = intent_obj.hass
        slots = self.async_validate_slots(intent_obj.slots)
        name = slots["name"]["value"]

        response = intent_obj.create_response()
        response.response_type = intent.IntentResponseType.QUERY_ANSWER
        store = self._store(hass)
        device_id = _resolve_device_id(hass, name)
        if store is None or device_id is None:
            response.async_set_speech(f"I couldn't find a device called {name}.")
            return response

        key = store.key_for_device_id(device_id)
        log = store.data["devices"][key]["log"] if key else []
        device_name = _device_name(hass, device_id)
        if not log:
            response.async_set_speech(f"There are no notes for {device_name}.")
            return response

        latest = log[0]
        issues = notelog.issue_count(log)
        count = len(log)
        plural = "note" if count == 1 else "notes"
        speech = f"{device_name} has {count} {plural}. The latest is: {latest['text']}."
        if issues:
            speech += f" {issues} flagged as an issue." if issues == 1 else (
                f" {issues} flagged as issues."
            )
        response.async_set_speech(speech)
        return response


@callback
def async_setup_intents(hass: HomeAssistant) -> None:
    """Register the Device Notes intents (auto-exposed to the Assist LLM)."""
    intent.async_register(hass, AddNoteIntentHandler())
    intent.async_register(hass, GetNotesIntentHandler())
    _LOGGER.debug("Registered Device Notes intents")


@callback
def async_remove_intents(hass: HomeAssistant) -> None:
    """Remove the Device Notes intents."""
    intent.async_remove(hass, INTENT_ADD_NOTE)
    intent.async_remove(hass, INTENT_GET_NOTES)
