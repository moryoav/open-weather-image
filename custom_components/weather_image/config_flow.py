"""Config flow for the Weather Image integration."""

from __future__ import annotations

from homeassistant import config_entries

from .const import DOMAIN


class WeatherImageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weather Image."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        """Set up the integration from the Home Assistant UI."""
        return self.async_create_entry(
            title="Weather Image",
            data={},
        )
