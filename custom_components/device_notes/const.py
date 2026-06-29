"""Constants for the Device Notes integration."""

from __future__ import annotations

DOMAIN = "device_notes"

# --- Config / options keys ------------------------------------------------
CONF_DEVICES = "devices"
CONF_AREAS = "areas"
CONF_AREA_ID = "area_id"

# Subentry types (per-device / per-area opt-in)
SUBENTRY_DEVICE = "device"
SUBENTRY_AREA = "area"

# --- Storage --------------------------------------------------------------
STORAGE_VERSION = 1
STORAGE_KEY = "device_notes"

# --- Log entry shape ------------------------------------------------------
# {"ts": <iso8601>, "source": <str>, "text": <str>,
#  "category": <str|None>, "severity": <"info"|"warning"|"error">}
ATTR_TS = "ts"
ATTR_SOURCE = "source"
ATTR_TEXT = "text"
ATTR_LOG = "log"
ATTR_CATEGORY = "category"
ATTR_SEVERITY = "severity"

# --- Sources --------------------------------------------------------------
SOURCE_USER = "user"
SOURCE_AGENT = "agent"

# --- Severity (signal level; the issues sensor counts warning+error) ------
SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_ERROR = "error"
SEVERITIES = (SEVERITY_INFO, SEVERITY_WARNING, SEVERITY_ERROR)
DEFAULT_SEVERITY = SEVERITY_INFO
ISSUE_SEVERITIES = frozenset({SEVERITY_WARNING, SEVERITY_ERROR})

# --- Service names --------------------------------------------------------
SERVICE_APPEND = "append"
SERVICE_GET = "get"
SERVICE_CLEAR = "clear"
SERVICE_DELETE_LAST = "delete_last"
SERVICE_DELETE = "delete"

# --- get response keys ----------------------------------------------------
ATTR_NOTES = "notes"
ATTR_COUNT = "count"
ATTR_ISSUES = "issues"

# --- Service fields -------------------------------------------------------
ATTR_DEVICE_ID = "device_id"
ATTR_ENTITY_ID = "entity_id"
ATTR_NOTE = "note"

# --- Guardrails -----------------------------------------------------------
MAX_ENTRIES = 50  # keep the newest N entries
MAX_LOG_BYTES = 8 * 1024  # prune oldest beyond ~8 KB total
MAX_ENTRY_CHARS = 255  # HA text entity hard limit, one line per entry
MAX_STATE_CHARS = 255  # HA state-string hard ceiling
MAX_PREVIEW_CHARS = 80  # sensor state preview: short, fits the device-page cell

# --- Dispatcher signals ---------------------------------------------------
# Fired with the record key whenever a device's log changes, so its entities
# can refresh their state.
SIGNAL_NOTES_UPDATED = f"{DOMAIN}_notes_updated"

# --- Bus event ------------------------------------------------------------
# Fired on the HA event bus whenever a note is appended (any path: service,
# device-page text box, or card), so automations can react. Event data:
# {device_id, key, ts, source, text, category, severity}.
EVENT_NOTE_ADDED = f"{DOMAIN}_added"
