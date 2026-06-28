# Device Notes

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A Home Assistant custom integration that attaches a free-text, **append-only,
timestamped note log** to any device — rendered **inline on the device's own
page**, alongside its real entities, not buried in a separate dialog.

The primary writer is an **AI agent** (via service calls); a human can also add a
line straight from the device page.

> Why it exists: entity-level note add-ons attach to *entities* via the more-info
> dialog. Device Notes attaches to the **device**, using the registry
> identifier-copy technique proven by
> [HA-Battery-Notes](https://github.com/andrew-codechimp/HA-Battery-Notes) /
> [PowerCalc](https://github.com/bramstroker/homeassistant-powercalc).

## How it works

Each opted-in device gets **two entities**, both attached to the existing device:

| Entity | Category | Purpose |
| --- | --- | --- |
| `sensor.<device>_notes` | Diagnostic | State = preview of the latest entry; `attributes.log` holds the full newest-first list of `{ts, source, text}`. |
| `text.<device>_note_entry` | Config | An "add a line" box. Type + Enter → timestamps it, appends to the log as a `user` note, then clears itself. |

The full `log` attribute is **excluded from the recorder** database. The log is
capped to the newest **50 entries** and **≤8 KB**; each entry is ≤255 chars.

Notes are stored under a **stable internal key**, not the `device_id` — so if a
device's id rotates (e.g. an integration is removed and re-added), the notes
**re-link automatically** by the device's identifiers. Removing a device from the
opt-in keeps its notes in storage, so re-adding restores them.

## Services

| Service | Targets | Purpose |
| --- | --- | --- |
| `device_notes.append` | `device_id` **or** `entity_id` + `note` (+ optional `source`) | Append a line. `source` defaults to `agent`. |
| `device_notes.clear` | `device_id` **or** `entity_id` | Wipe the whole log. |
| `device_notes.delete_last` | `device_id` **or** `entity_id` | Undo the most recent entry. |

Either a `device_id` or any `entity_id` on the target device works (entity ids are
resolved to their device).

```yaml
# Example: an automation / AI agent appends a note
action: device_notes.append
data:
  device_id: 3d7c2957fa567d3dd4c1eeb902435cff
  note: Boiler pressure was low (0.8 bar) — topped up to 1.4.
```

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `konradwalsh/ha-device-notes`,
   category **Integration**.
2. Install **Device Notes**, then restart Home Assistant.
3. **Settings → Devices & Services → + Add Integration → Device Notes**.
4. On the entry, click **Configure** and choose the devices and/or areas to attach
   a note log to. Every device in a selected area gets one automatically.

## Lovelace card

The integration ships and auto-registers a card — it appears as **Device Notes
Card** in the card picker. Manual YAML:

```yaml
type: custom:device-notes-card
entity: sensor.living_room_trv_notes
title: TRV Notes        # optional
```

It renders the full log newest-first with source badges (agent/user) and
timestamps, themed to your dashboard.

## Development

- Pure logic (note-log + device-link) is Home-Assistant-free and tested with plain
  `pytest`. HA-coupled code is tested under
  [`pytest-homeassistant-custom-component`](https://github.com/MatthewFlamm/pytest-homeassistant-custom-component).
- Lint/format with [ruff](https://docs.astral.sh/ruff/).

## Credits

Device-attach mechanism adapted from HA-Battery-Notes (andrew-codechimp) and
PowerCalc (bramstroker).

## License

MIT
