"""Service handlers for the Weather Image integration."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, State
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTITY_ID,
    ATTR_FORECAST_TYPE,
    ATTR_OUTPUT_FILE,
    ATTR_TITLE,
    ATTR_TYPE,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FORECAST_TYPE,
    DEFAULT_OUTPUT_FILE,
    FORECAST_BOX_COUNT,
    SUPPORTED_FORECAST_TYPES,
    WEATHER_DOMAIN,
    WEATHER_GET_FORECASTS_SERVICE,
)
from .models import ForecastItem, SideMetric, WeatherImagePayload

SUNRISE_GLYPH = "\uf051"
SUNSET_GLYPH = "\uf052"

GENERATE_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Optional(ATTR_FORECAST_TYPE, default=DEFAULT_FORECAST_TYPE): vol.In(
            SUPPORTED_FORECAST_TYPES
        ),
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_OUTPUT_FILE, default=DEFAULT_OUTPUT_FILE): cv.string,
    }
)

_WEATHER_STATES_UNAVAILABLE = {"unknown", "unavailable"}

_HUMANIZED_CONDITIONS = {
    "clear-night": "Clear sky",
    "cloudy": "Cloudy",
    "exceptional": "Exceptional",
    "fog": "Fog",
    "hail": "Hail",
    "lightning": "Thunderstorm",
    "lightning-rainy": "Thunderstorm",
    "partlycloudy": "Broken clouds",
    "pouring": "Heavy rain",
    "rainy": "Rain",
    "snowy": "Snow",
    "snowy-rainy": "Sleet",
    "sunny": "Clear sky",
    "windy": "Windy",
    "windy-variant": "Windy clouds",
}


@dataclass(slots=True, frozen=True)
class _PreparedForecast:
    local_datetime: datetime
    raw: dict[str, Any]


async def async_handle_generate(
    hass: HomeAssistant,
    call: ServiceCall,
):
    """Generate the weather image and save it under /config/www."""
    from .renderer import save_weather_image

    entity_id = call.data[ATTR_ENTITY_ID]
    forecast_type = call.data[ATTR_FORECAST_TYPE]
    output_path = _resolve_output_path(hass, call.data[ATTR_OUTPUT_FILE])

    state = hass.states.get(entity_id)
    if state is None:
        raise ServiceValidationError(f"Weather entity '{entity_id}' was not found.")

    if not entity_id.startswith(f"{WEATHER_DOMAIN}."):
        raise ServiceValidationError(
            f"Entity '{entity_id}' is not a weather entity and cannot be rendered."
        )

    if state.state in _WEATHER_STATES_UNAVAILABLE:
        raise ServiceValidationError(
            f"Weather entity '{entity_id}' is currently {state.state}."
        )

    forecast_response = await hass.services.async_call(
        WEATHER_DOMAIN,
        WEATHER_GET_FORECASTS_SERVICE,
        {
            ATTR_ENTITY_ID: entity_id,
            ATTR_TYPE: forecast_type,
        },
        blocking=True,
        return_response=True,
    )

    if not isinstance(forecast_response, dict):
        raise ServiceValidationError(
            f"{WEATHER_DOMAIN}.{WEATHER_GET_FORECASTS_SERVICE} did not return forecast data."
        )

    entity_response = forecast_response.get(entity_id)
    if not isinstance(entity_response, dict):
        raise ServiceValidationError(
            f"No forecast payload was returned for weather entity '{entity_id}'."
        )

    raw_forecast = entity_response.get("forecast")
    if not isinstance(raw_forecast, list) or not raw_forecast:
        raise ServiceValidationError(
            f"Weather entity '{entity_id}' did not return any {forecast_type} forecast entries."
        )

    payload = _build_payload(
        state,
        raw_forecast,
        forecast_type,
        call.data.get(ATTR_TITLE),
    )

    await hass.async_add_executor_job(save_weather_image, payload, output_path)

    response = {
        "path": output_path.as_posix(),
        "url": _public_url(output_path, hass),
        "width": CANVAS_WIDTH,
        "height": CANVAS_HEIGHT,
    }
    if call.return_response:
        return response
    return None


def _build_payload(
    state: State,
    raw_forecast: list[dict[str, Any]],
    forecast_type: str,
    title_override: str | None,
) -> WeatherImagePayload:
    attributes = state.attributes
    now_local = dt_util.as_local(state.last_updated)
    prepared = _prepare_forecast(raw_forecast)
    if not prepared:
        raise ServiceValidationError("No forecast entries had a valid datetime value.")

    selected = _select_forecast_items(prepared, forecast_type, now_local)
    forecast_items = tuple(
        _build_forecast_item(entry, forecast_type, attributes) for entry in selected
    )
    if not forecast_items:
        raise ServiceValidationError("No usable forecast items were available to render.")

    title = title_override or state.name or state.entity_id
    subtitle = _format_header_datetime(now_local)

    temperature_unit = _coalesce(attributes, "temperature_unit") or "°C"
    current_temperature = _format_temperature(_coalesce(attributes, "temperature"), temperature_unit)

    feels_like_value = _coalesce(attributes, "apparent_temperature", "feels_like_temperature")
    feels_like = None
    if feels_like_value is not None:
        feels_like = f"Feels Like: {_format_temperature(feels_like_value, temperature_unit)}"

    condition = str(state.state or "cloudy")
    summary_source = prepared[0].raw if forecast_type == "daily" else selected[0].raw

    return WeatherImagePayload(
        title=title,
        subtitle=subtitle,
        current_temperature=current_temperature,
        feels_like=feels_like,
        range_text=_range_text(prepared, forecast_type, temperature_unit),
        condition=condition,
        condition_text=_humanize_condition(condition),
        is_daytime=_is_daytime(condition, now_local),
        detail_lines=tuple(_detail_lines(attributes, summary_source, temperature_unit)),
        side_metrics=tuple(_side_metrics(attributes, summary_source)),
        forecast_items=forecast_items,
    )


def _prepare_forecast(raw_forecast: Iterable[dict[str, Any]]) -> list[_PreparedForecast]:
    prepared: list[_PreparedForecast] = []
    for row in raw_forecast:
        if not isinstance(row, dict):
            continue

        timestamp = row.get("datetime")
        if not isinstance(timestamp, str):
            continue

        parsed = dt_util.parse_datetime(timestamp)
        if parsed is None:
            continue

        prepared.append(
            _PreparedForecast(
                local_datetime=dt_util.as_local(parsed),
                raw=row,
            )
        )

    prepared.sort(key=lambda entry: entry.local_datetime)
    return prepared


def _select_forecast_items(
    prepared: list[_PreparedForecast],
    forecast_type: str,
    now_local: datetime,
) -> list[_PreparedForecast]:
    if forecast_type == "daily":
        future = [
            entry for entry in prepared if entry.local_datetime.date() > now_local.date()
        ]
        if len(future) >= FORECAST_BOX_COUNT:
            return future[:FORECAST_BOX_COUNT]

        seen_dates = {entry.local_datetime.date() for entry in future}
        for entry in prepared:
            date_key = entry.local_datetime.date()
            if date_key in seen_dates:
                continue
            future.append(entry)
            seen_dates.add(date_key)
            if len(future) >= FORECAST_BOX_COUNT:
                break
        return future[:FORECAST_BOX_COUNT]

    future = [entry for entry in prepared if entry.local_datetime >= now_local]
    if len(future) < FORECAST_BOX_COUNT:
        future = prepared
    return future[:FORECAST_BOX_COUNT]


def _build_forecast_item(
    entry: _PreparedForecast,
    forecast_type: str,
    current_attributes: dict[str, Any],
) -> ForecastItem:
    raw = entry.raw
    condition = str(raw.get("condition") or "cloudy")
    temperature_unit = _coalesce(current_attributes, "temperature_unit") or "°C"

    temperature_high = _format_temperature(raw.get("temperature"), temperature_unit)
    temperature_low_value = raw.get("templow")
    temperature_low = (
        _format_temperature(temperature_low_value, temperature_unit)
        if temperature_low_value is not None
        else None
    )

    label = (
        _format_daily_label(entry.local_datetime)
        if forecast_type == "daily"
        else _format_hourly_label(entry.local_datetime)
    )

    return ForecastItem(
        label=label,
        condition=condition,
        description=_humanize_condition(condition),
        temperature_high=temperature_high,
        temperature_low=temperature_low,
        is_daytime=_is_daytime(condition, entry.local_datetime),
    )


def _detail_lines(
    attributes: dict[str, Any],
    summary_source: dict[str, Any],
    temperature_unit: str,
) -> list[str]:
    lines: list[str] = []

    wind_speed = _coalesce(attributes, "wind_speed")
    wind_speed_unit = _coalesce(attributes, "wind_speed_unit")
    wind_bearing = _format_bearing(_coalesce(attributes, "wind_bearing"))
    if wind_speed is not None and wind_speed_unit:
        text = f"Wind: {_format_number(wind_speed)}{wind_speed_unit}"
        if wind_bearing:
            text += f" ({wind_bearing})"
        lines.append(text)

    humidity = _coalesce(attributes, "humidity")
    if humidity is not None:
        lines.append(f"Humidity: {_format_number(humidity)}%")

    uv_index = _coalesce(attributes, "uv_index")
    if uv_index is not None:
        lines.append(f"UV Index: {_format_number(uv_index)}")

    precipitation_probability = summary_source.get("precipitation_probability")
    if precipitation_probability is not None:
        lines.append(f"Chance of Rain: {_format_number(precipitation_probability)}%")

    precipitation = summary_source.get("precipitation")
    precipitation_unit = _coalesce(attributes, "precipitation_unit") or "mm"
    if precipitation is not None:
        lines.append(
            f"Forecast Precip.: {_format_number(precipitation)}{precipitation_unit}"
        )

    if len(lines) < 5:
        cloud_coverage = _coalesce(attributes, "cloud_coverage")
        if cloud_coverage is not None:
            lines.append(f"Cloud Cover: {_format_number(cloud_coverage)}%")

    if len(lines) < 5:
        dew_point = _coalesce(attributes, "dew_point")
        if dew_point is not None:
            lines.append(f"Dew Point: {_format_temperature(dew_point, temperature_unit)}")

    return lines[:5]


def _side_metrics(
    attributes: dict[str, Any],
    summary_source: dict[str, Any],
) -> list[SideMetric]:
    metrics: list[SideMetric] = []

    sunrise = summary_source.get("sunrise")
    if isinstance(sunrise, str):
        sunrise_dt = dt_util.parse_datetime(sunrise)
        if sunrise_dt is not None:
            metrics.append(
                SideMetric(
                    text=_format_time_only(dt_util.as_local(sunrise_dt)),
                    icon_glyph=SUNRISE_GLYPH,
                )
            )

    sunset = summary_source.get("sunset")
    if isinstance(sunset, str):
        sunset_dt = dt_util.parse_datetime(sunset)
        if sunset_dt is not None:
            metrics.append(
                SideMetric(
                    text=_format_time_only(dt_util.as_local(sunset_dt)),
                    icon_glyph=SUNSET_GLYPH,
                )
            )

    if len(metrics) < 2:
        pressure = _coalesce(attributes, "pressure")
        pressure_unit = _coalesce(attributes, "pressure_unit")
        if pressure is not None and pressure_unit:
            metrics.append(
                SideMetric(text=f"Pressure: {_format_number(pressure)} {pressure_unit}")
            )

    if len(metrics) < 2:
        visibility = _coalesce(attributes, "visibility")
        visibility_unit = _coalesce(attributes, "visibility_unit")
        if visibility is not None and visibility_unit:
            metrics.append(
                SideMetric(
                    text=f"Visibility: {_format_number(visibility)} {visibility_unit}"
                )
            )

    return metrics[:2]


def _range_text(
    prepared: list[_PreparedForecast],
    forecast_type: str,
    temperature_unit: str,
) -> str | None:
    if forecast_type == "daily":
        first = prepared[0].raw
        if first.get("temperature") is not None and first.get("templow") is not None:
            return (
                f"{_format_temperature(first['temperature'], temperature_unit)} / "
                f"{_format_temperature(first['templow'], temperature_unit)}"
            )
        return None

    temperatures = [
        float(entry.raw["temperature"])
        for entry in prepared[:24]
        if isinstance(entry.raw.get("temperature"), (int, float))
    ]
    if not temperatures:
        return None
    return (
        f"{_format_temperature(max(temperatures), temperature_unit)} / "
        f"{_format_temperature(min(temperatures), temperature_unit)}"
    )


def _resolve_output_path(hass: HomeAssistant, requested_path: str) -> Path:
    www_root = Path(hass.config.path("www")).resolve()
    normalized = requested_path.replace("\\", "/")

    if normalized.startswith("/config/"):
        relative = PurePosixPath(normalized.removeprefix("/config/"))
        candidate = Path(hass.config.path(*relative.parts))
    else:
        path = Path(requested_path)
        if path.is_absolute():
            candidate = path
        else:
            relative = PurePosixPath(normalized)
            if relative.parts and relative.parts[0] == "www":
                candidate = Path(hass.config.path(*relative.parts))
            else:
                candidate = www_root / relative

    candidate = candidate.resolve()
    try:
        candidate.relative_to(www_root)
    except ValueError as err:
        raise ServiceValidationError(
            "output_file must stay inside /config/www so Home Assistant can serve it."
        ) from err

    if candidate.suffix.lower() != ".png":
        raise ServiceValidationError("output_file must point to a .png file.")

    return candidate


def _public_url(output_path: Path, hass: HomeAssistant) -> str:
    www_root = Path(hass.config.path("www")).resolve()
    relative = output_path.resolve().relative_to(www_root)
    return f"/local/{relative.as_posix()}"


def _format_header_datetime(value: datetime) -> str:
    return f"{value.strftime('%a')} {value.day} {value.strftime('%B')} // {_format_time_only(value)}"


def _format_daily_label(value: datetime) -> str:
    return f"{value.strftime('%a')} {value.day} {value.strftime('%B')}"


def _format_hourly_label(value: datetime) -> str:
    return f"{value.strftime('%a')} {_format_time_only(value)}"


def _format_time_only(value: datetime) -> str:
    hour = value.hour % 12 or 12
    suffix = "am" if value.hour < 12 else "pm"
    return f"{hour}:{value.minute:02d} {suffix}"


def _format_temperature(value: Any, unit: str) -> str:
    if value is None:
        return f"--{unit}"
    return f"{int(round(float(value)))}{unit}"


def _format_number(value: Any) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return f"{number:.1f}".rstrip("0").rstrip(".")


def _humanize_condition(condition: str) -> str:
    return _HUMANIZED_CONDITIONS.get(
        condition,
        condition.replace("-", " ").replace("_", " ").title(),
    )


def _is_daytime(condition: str, value: datetime) -> bool:
    if condition == "clear-night":
        return False
    if condition == "sunny":
        return True
    return 6 <= value.hour < 18


def _format_bearing(value: Any) -> str | None:
    if isinstance(value, str):
        return value.upper()
    if not isinstance(value, (int, float)):
        return None

    directions = ("N", "NE", "E", "SE", "S", "SW", "W", "NW")
    index = round(float(value) / 45) % len(directions)
    return directions[index]


def _coalesce(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = mapping.get(key)
        if value is not None:
            return value
    return None
