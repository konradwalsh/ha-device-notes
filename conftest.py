"""Pytest bootstrap.

Put the repo root on sys.path so tests can import
``custom_components.device_notes.*`` without installing the integration or a
Home Assistant runtime. The pure note-log core is deliberately HA-free, so
these tests run on plain ``pytest``.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# HA-coupled tests live in tests/ha/ and need Home Assistant + the
# pytest-homeassistant-custom-component harness (run in WSL). When HA isn't
# importable (native Windows pure-logic runs), skip that suite automatically so
# plain `pytest` stays green.
collect_ignore = []
try:
    import homeassistant  # noqa: F401
except ImportError:
    collect_ignore.append("tests/ha")
