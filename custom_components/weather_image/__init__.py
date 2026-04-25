"""Home Assistant service integration for rendering weather PNGs."""

from __future__ import annotations

from homeassistant.core import HomeAssistant, SupportsResponse
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN, SERVICE_GENERATE
from .service import GENERATE_SERVICE_SCHEMA, async_handle_generate


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Weather Image integration."""
    if hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        return True

    async def handle_generate(call):
        return await async_handle_generate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE,
        handle_generate,
        schema=GENERATE_SERVICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    return True
