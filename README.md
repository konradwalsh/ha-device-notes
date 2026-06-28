# Device Notes

A Home Assistant custom integration that attaches a free-text, **append-only,
timestamped note log** to any opted-in *device* — rendered inline on the
device's own page alongside its real entities, not buried in a separate card or
dialog.

The primary writer is an AI agent (via service calls); a human can also add a
line straight from the device page.

## How it works

Each opted-in device gets **two entities**, both attached to the existing device
via its registry identifiers (the device-page attach pattern proven by
[HA-Battery-Notes](https://github.com/andrew-codechimp/HA-Battery-Notes) /
[PowerCalc](https://github.com/bramstroker/homeassistant-powercalc)):

- `sensor.<device>_notes` (diagnostic) — state is a preview of the latest entry;
  `attributes.log` holds the full newest-first list of `{ts, source, text}`.
  The `log` attribute is excluded from the recorder.
- `text.<device>_note_entry` (config) — a one-line input box. Setting it
  timestamps the text, appends it to the log, then clears itself.

## Services

| Service | Targets | Purpose |
| --- | --- | --- |
| `device_notes.append` | `device_id` or `entity_id` + `note` (+ optional `source`) | Append a line (source defaults to `agent`). |
| `device_notes.clear` | `device_id` or `entity_id` | Wipe the whole log. |
| `device_notes.delete_last` | `device_id` or `entity_id` | Undo the last entry. |

## Status

Early build. Step 1 (scaffold + config entry that loads) is in place; entities,
services, persistence, config flow device selection, and the Lovelace card land
in subsequent steps.

## Install (HACS)

Add this repository as a custom HACS integration repository, install, then add
the **Device Notes** integration from Settings → Devices & Services.
