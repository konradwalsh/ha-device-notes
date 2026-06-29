"""HA-coupled tests for the Assist/LLM intents (add + read device notes).

Registered intents are what the Assist LLM API turns into callable tools, so an
assistant can add or read notes by voice/chat. These tests drive the handlers
directly via ``intent.async_handle``.
"""

from homeassistant.core import Context
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import intent, llm
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.device_notes.const import DOMAIN, SUBENTRY_DEVICE
from custom_components.device_notes.intent import INTENT_ADD_NOTE, INTENT_GET_NOTES


def _add_foreign_device(
    hass, *, name="Living Room TRV", identifiers=(("demo", "trv"),)
):
    entry = MockConfigEntry(domain="demo")
    entry.add_to_hass(hass)
    return dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={tuple(i) for i in identifiers},
        name=name,
    )


async def _setup(hass, device_ids):
    subentries = [
        {
            "subentry_type": SUBENTRY_DEVICE,
            "data": {"device_id": d},
            "title": "Device",
            "unique_id": None,
        }
        for d in device_ids
    ]
    entry = MockConfigEntry(domain=DOMAIN, subentries_data=subentries)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _speech(response):
    return response.speech["plain"]["speech"]


async def test_add_note_intent_records_a_note(hass):
    device = _add_foreign_device(hass)
    await _setup(hass, [device.id])

    response = await intent.async_handle(
        hass,
        DOMAIN,
        INTENT_ADD_NOTE,
        {
            "name": {"value": "Living Room TRV"},
            "note": {"value": "valve sticking"},
            "severity": {"value": "warning"},
        },
    )

    store = hass.data[DOMAIN]["store"]
    key = store.key_for_device_id(device.id)
    entry = store.data["devices"][key]["log"][0]
    assert entry["text"] == "valve sticking"
    assert entry["severity"] == "warning"
    assert entry["source"] == "agent"
    assert "Living Room TRV" in _speech(response)


async def test_add_note_intent_unknown_device_speaks_and_stores_nothing(hass):
    device = _add_foreign_device(hass)
    await _setup(hass, [device.id])

    response = await intent.async_handle(
        hass,
        DOMAIN,
        INTENT_ADD_NOTE,
        {"name": {"value": "Nonexistent Gadget"}, "note": {"value": "hi"}},
    )

    store = hass.data[DOMAIN]["store"]
    key = store.key_for_device_id(device.id)
    assert key is None or store.data["devices"][key]["log"] == []
    assert "couldn't find" in _speech(response).lower()


async def test_get_notes_intent_reads_back_latest(hass):
    device = _add_foreign_device(hass)
    await _setup(hass, [device.id])
    await intent.async_handle(
        hass,
        DOMAIN,
        INTENT_ADD_NOTE,
        {"name": {"value": "Living Room TRV"}, "note": {"value": "boiler serviced"}},
    )

    response = await intent.async_handle(
        hass,
        DOMAIN,
        INTENT_GET_NOTES,
        {"name": {"value": "Living Room TRV"}},
    )

    assert "boiler serviced" in _speech(response)


async def test_intents_are_exposed_as_assist_llm_tools(hass):
    # AssistAPI reads the homeassistant component's exposed-entities store.
    await async_setup_component(hass, "homeassistant", {})
    device = _add_foreign_device(hass)
    await _setup(hass, [device.id])

    llm_context = llm.LLMContext(
        platform="test",
        context=Context(),
        user_prompt=None,
        language="en",
        assistant="conversation",
        device_id=None,
    )
    api = await llm.async_get_api(hass, llm.LLM_API_ASSIST, llm_context)
    tool_names = {tool.name for tool in api.tools}

    assert INTENT_ADD_NOTE in tool_names
    assert INTENT_GET_NOTES in tool_names


async def test_get_notes_intent_with_no_notes(hass):
    device = _add_foreign_device(hass)
    await _setup(hass, [device.id])

    response = await intent.async_handle(
        hass,
        DOMAIN,
        INTENT_GET_NOTES,
        {"name": {"value": "Living Room TRV"}},
    )

    assert "no notes" in _speech(response).lower()
