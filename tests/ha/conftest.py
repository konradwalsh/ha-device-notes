"""Fixtures for HA-coupled tests.

These run under pytest-homeassistant-custom-component (WSL venv). The autouse
fixture lets Home Assistant load our ``custom_components/`` during tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    yield
