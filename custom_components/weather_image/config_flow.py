"""Config flow for the Weather Image integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN


class WeatherImageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weather Image."""

    VERSION = 1
    MINOR_VERSION = 0

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Allow setup from the Home Assistant UI."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured(reason="already_configured")

        if user_input is not None:
            return self.async_create_entry(
                title="Weather Image",
                data={},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
        )
