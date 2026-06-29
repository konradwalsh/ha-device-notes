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

Each opted-in device gets a small set of entities, all attached to the existing
device and sharing a **`Notes`** name prefix so they cluster together in the
device page's Diagnostic section:

| Entity | Shown as | Purpose |
| --- | --- | --- |
| `sensor.<device>_notes` | Notes | State = short preview of the latest note; `attributes.log` holds the full newest-first list of `{ts, source, text, category, severity}`. |
| `sensor.<device>_note_issues` | Notes: issues | Count of notes flagged `warning` or `error` — a signal you can put on a dashboard or trigger automations from. |
| `text.<device>_note_entry` | Notes: new entry | An "add a line" box. Type + Enter → timestamps it, appends as a `user` note, then clears itself. |
| `button.<device>_delete_last_note` | Notes: delete last | Undo the most recent entry. |
| `button.<device>_clear_notes` | Notes: clear all | Wipe the whole log. |

The full `log` attribute is **excluded from the recorder** database. The log is
capped to the newest **50 entries** and **≤8 KB**; each entry is ≤255 chars.

Notes are stored under a **stable internal key**, not the `device_id` — so if a
device's id rotates (e.g. an integration is removed and re-added), the notes
**re-link automatically** by the device's identifiers. Removing a device from the
opt-in keeps its notes in storage, so re-adding restores them.

## Services

| Service | Targets / fields | Purpose |
| --- | --- | --- |
| `device_notes.append` | `device_id`/`entity_id` + `note` (+ `source`, `category`, `severity`) | Append a line. `source` defaults to `agent`; `severity` ∈ `info`/`warning`/`error` feeds the issue count. |
| `device_notes.get` | `device_id`/`entity_id` → **response** | Return the notes (newest-first) plus `count` and `issues`. Read-only — ideal for an AI agent to pull a device's history in one call. |
| `device_notes.clear` | `device_id`/`entity_id` | Wipe the whole log. |
| `device_notes.delete_last` | `device_id`/`entity_id` | Undo the most recent entry. |
| `device_notes.delete` | `device_id`/`entity_id` + `ts` | Remove one specific entry by its timestamp. |

Either a `device_id` or any `entity_id` on the target device works (entity ids are
resolved to their device).

```yaml
# Append a note (automation / AI agent)
action: device_notes.append
data:
  device_id: 3d7c2957fa567d3dd4c1eeb902435cff
  note: Boiler pressure was low (0.8 bar) — topped up to 1.4.
  category: maintenance
  severity: warning
```

```yaml
# Read a device's notes back as response data
action: device_notes.get
data:
  entity_id: sensor.living_room_trv_notes
response_variable: notes
```

## Voice & AI assistants

Two intents are registered and **auto-exposed to Home Assistant's Assist LLM
API** — no extra configuration. An LLM-backed assistant can call them directly:

- **DeviceNotesAddNote** — "add a note to the living room TRV: valve is sticking"
- **DeviceNotesGetNotes** — "what notes are on the boiler?"

## Reacting to notes

Every append (service, device-page box, or card) fires a **`device_notes_added`**
event with `{device_id, key, ts, source, text, category, severity}`, so you can
notify or automate on new notes — e.g. ping yourself whenever an agent logs a
`severity: error` note on any device.

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `konradwalsh/ha-device-notes`,
   category **Integration**.
2. Install **Device Notes**, then restart Home Assistant.
3. **Settings → Devices & Services → + Add Integration → Device Notes**.
4. On the **Device Notes** entry, click **+ Add** → **Add a device** or **Add an
   area**. Each is a removable subentry; removing one cleanly removes its note
   entities. Every device in an added area gets a note log automatically.

## Lovelace card

The integration ships and auto-registers a card — it appears as **Device Notes
Card** in the card picker. Manual YAML:

```yaml
type: custom:device-notes-card
entity: sensor.living_room_trv_notes
title: TRV Notes        # optional
```

It renders the full log newest-first with source badges (agent/user) and
timestamps, an **add-a-note** box, a per-row delete, and a **"?"** button with a
built-in walkthrough — all themed to your dashboard.

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
