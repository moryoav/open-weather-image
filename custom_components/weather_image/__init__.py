"""Home Assistant service integration for rendering weather PNGs."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_GENERATE
from .service import GENERATE_SERVICE_SCHEMA, async_handle_generate


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Weather Image integration."""
    await _async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weather Image from a config entry."""
    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Weather Image config entry."""
    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        return

    async def handle_generate(call):
        return await async_handle_generate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE,
        handle_generate,
        schema=GENERATE_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
