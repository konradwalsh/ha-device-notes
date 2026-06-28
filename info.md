# Device Notes

Attach a free-text, append-only, timestamped **note log** to any device, shown
inline on the device's own page.

- Written primarily by an AI agent via `device_notes.append`, or by a human from
  the device page.
- Two entities per opted-in device: a `sensor` (the log + latest preview) and a
  `text` input box (add a line).
- Opt in per device or by area; the note log survives restarts and re-links if a
  device's id rotates.
- The full log attribute is kept out of the recorder database.
