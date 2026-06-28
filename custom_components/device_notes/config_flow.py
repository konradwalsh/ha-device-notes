"""Config + options flow for Device Notes.

The config step just creates the single entry. Device/area opt-in lives in the
options flow (Configure), so it can be edited any time; saving it reloads the
entry, which re-runs the platforms and adds/removes entities accordingly.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    AreaSelector,
    AreaSelectorConfig,
    DeviceSelector,
    DeviceSelectorConfig,
)

from .const import CONF_AREAS, CONF_DEVICES, DOMAIN


class DeviceNotesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Device Notes config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single Device Notes entry; opt-in happens in options."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Device Notes", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: Any) -> OptionsFlow:
        return DeviceNotesOptionsFlow()


class DeviceNotesOptionsFlow(OptionsFlow):
    """Pick which devices / areas get a note log."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data={
                    CONF_DEVICES: user_input.get(CONF_DEVICES, []),
                    CONF_AREAS: user_input.get(CONF_AREAS, []),
                },
            )

        current = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DEVICES, default=current.get(CONF_DEVICES, [])
                ): DeviceSelector(DeviceSelectorConfig(multiple=True)),
                vol.Optional(
                    CONF_AREAS, default=current.get(CONF_AREAS, [])
                ): AreaSelector(AreaSelectorConfig(multiple=True)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
