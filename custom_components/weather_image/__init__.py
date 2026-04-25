"""Home Assistant service integration for rendering weather PNGs."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from .const import DOMAIN, SERVICE_GENERATE


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Set up the Weather Image integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up Weather Image from a config entry."""
    await _async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a Weather Image config entry."""
    return True


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_GENERATE):
        return

    register_kwargs = {}
    try:
        from homeassistant.core import SupportsResponse

        register_kwargs["supports_response"] = SupportsResponse.OPTIONAL
    except ImportError:
        pass

    async def handle_generate(call):
        from .service import async_handle_generate

        return await async_handle_generate(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE,
        handle_generate,
        **register_kwargs,
    )
