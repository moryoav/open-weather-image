"""Data models for the Weather Image renderer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class SideMetric:
    """Secondary metric displayed in the lower-right details area."""

    text: str
    icon_glyph: str | None = None


@dataclass(slots=True, frozen=True)
class ForecastItem:
    """A single forecast card in the bottom rail."""

    label: str
    condition: str
    description: str
    temperature_high: str
    temperature_low: str | None = None
    is_daytime: bool = True


@dataclass(slots=True, frozen=True)
class WeatherImagePayload:
    """Normalized weather data ready for the Pillow renderer."""

    title: str
    subtitle: str
    current_temperature: str
    feels_like: str | None
    range_text: str | None
    condition: str
    condition_text: str
    is_daytime: bool
    detail_lines: tuple[str, ...]
    side_metrics: tuple[SideMetric, ...]
    forecast_items: tuple[ForecastItem, ...]
