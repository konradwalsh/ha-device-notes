"""Config flow + per-scope subentry flows for Device Notes.

The config step creates the single entry. Opt-in is then done by adding
*subentries* — one per device or per area — via the entry's "+ Add" menu. HA
manages each subentry's entity lifecycle, so removing a subentry removes its
entities automatically.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    AreaSelector,
    AreaSelectorConfig,
    DeviceSelector,
    DeviceSelectorConfig,
)

from .const import ATTR_DEVICE_ID, CONF_AREA_ID, DOMAIN, SUBENTRY_AREA, SUBENTRY_DEVICE


class DeviceNotesConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the Device Notes config flow (single entry)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer a quick walkthrough or go straight to setup."""
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_show_menu(step_id="user", menu_options=["setup", "tutorial"])

    async def async_step_setup(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the single Device Notes entry; opt-in is via subentries."""
        return self.async_create_entry(title="Device Notes", data={})

    async def async_step_tutorial(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Walkthrough 1/2."""
        if user_input is not None:
            return await self.async_step_tutorial2()
        return self.async_show_form(step_id="tutorial", data_schema=vol.Schema({}))

    async def async_step_tutorial2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Walkthrough 2/2, then back to the menu."""
        if user_input is not None:
            return await self.async_step_user()
        return self.async_show_form(step_id="tutorial2", data_schema=vol.Schema({}))

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: Any
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUBENTRY_DEVICE: DeviceSubentryFlowHandler,
            SUBENTRY_AREA: AreaSubentryFlowHandler,
        }


class DeviceSubentryFlowHandler(ConfigSubentryFlow):
    """Attach a note log to a single device."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            device_id = user_input[ATTR_DEVICE_ID]
            device = dr.async_get(self.hass).async_get(device_id)
            title = (device.name_by_user or device.name) if device else device_id
            return self.async_create_entry(
                title=title or device_id, data={ATTR_DEVICE_ID: device_id}
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(ATTR_DEVICE_ID): DeviceSelector(DeviceSelectorConfig())}
            ),
        )


class AreaSubentryFlowHandler(ConfigSubentryFlow):
    """Attach note logs to every device in an area."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        if user_input is not None:
            area_id = user_input[CONF_AREA_ID]
            area = ar.async_get(self.hass).async_get_area(area_id)
            title = f"{area.name} (area)" if area else area_id
            return self.async_create_entry(title=title, data={CONF_AREA_ID: area_id})
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_AREA_ID): AreaSelector(AreaSelectorConfig())}
            ),
        )
