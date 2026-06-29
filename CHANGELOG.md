# Changelog

All notable changes to Device Notes are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses Home Assistant **calendar versioning** (`YYYY.M.PATCH`).

## [Unreleased]

## [2026.6.4] — 2026-06-29

### Added
- The card now surfaces note **severity** — `warning`/`error` rows get a colored
  badge and a left-edge accent — and shows a **category** chip when set.
- The card’s add-a-note box gained a **severity** selector and an optional
  **category** field, so a human records the same structure an agent does.
- The built-in card tutorial now demonstrates severity and category.

## [2026.6.3] — 2026-06-29

### Changed
- Device Notes Card title now defaults to **“Device Notes for {device name}”**
  when no title is set (was the generic “Notes”). A blank/whitespace title
  falls back to the device-based default.

## [2026.6.2] — 2026-06-29

### Added
- **Visual config editor** for the card — an entity picker (filtered to Device
  Notes sensors) plus an optional title, instead of YAML only; the card picker
  shows a live preview.
- Newly added cards **auto-fill** an existing `sensor.<device>_notes` so they
  render immediately instead of erroring on an empty entity.

## [2026.6.1] — 2026-06-29

### Added
- **Structured notes** — optional `category` (free-form) and `severity`
  (`info`/`warning`/`error`) on the `append` service.
- **`device_notes.get`** — read-only service returning a device’s notes
  (newest-first) plus `count` and `issues` as response data.
- **Assist/LLM intents** `DeviceNotesAddNote` / `DeviceNotesGetNotes`,
  auto-exposed to Home Assistant’s Assist LLM API (no extra setup).
- Per-device **`sensor.<device>_note_issues`** counting `warning`/`error` notes.
- **`device_notes_added`** event fired on every append (service, device-page
  box, or card).

### Changed
- All device-page entities share a **`Notes:`** name prefix so they cluster
  together in the Diagnostic section.

### Fixed
- The notes sensor state is now a short single-line preview (≤80 chars) so a
  long latest note no longer sprawls down the device page. Full text remains in
  the `log` attribute and the card.

### Internal
- CI: hassfest + HACS validation + a pinned full pytest suite (68 tests).

## [2026.6.0] — 2026-06-28

### Added
- Initial public release: an append-only, timestamped **note log** attached to
  opted-in devices and shown inline on each device’s page.
- Opt-in via config **subentries** (per device, per area).
- Entities per device: notes sensor, note-entry text box, **delete last** /
  **clear** buttons.
- Services: `append`, `clear`, `delete_last`, `delete`.
- Lovelace card with an add-a-note box, per-row delete, and a built-in
  walkthrough; config-flow “How it works” tutorial.
- Brand icon shipped in-repo (served locally on HA 2026.3+).
- Stable internal keying so notes survive entity/integration re-adds (re-link
  by device identifiers); log capped to 50 entries / 8 KB; note attribute
  excluded from the recorder.
- Adopted Home Assistant calendar versioning.

[Unreleased]: https://github.com/konradwalsh/ha-device-notes/compare/2026.6.4...HEAD
[2026.6.4]: https://github.com/konradwalsh/ha-device-notes/compare/2026.6.3...2026.6.4
[2026.6.3]: https://github.com/konradwalsh/ha-device-notes/compare/2026.6.2...2026.6.3
[2026.6.2]: https://github.com/konradwalsh/ha-device-notes/compare/2026.6.1...2026.6.2
[2026.6.1]: https://github.com/konradwalsh/ha-device-notes/compare/2026.6.0...2026.6.1
[2026.6.0]: https://github.com/konradwalsh/ha-device-notes/releases/tag/2026.6.0
