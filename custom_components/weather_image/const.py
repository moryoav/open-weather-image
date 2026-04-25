"""Constants for the Weather Image integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "weather_image"
SERVICE_GENERATE: Final = "generate"

ATTR_ENTITY_ID: Final = "entity_id"
ATTR_FORECAST_TYPE: Final = "forecast_type"
ATTR_TITLE: Final = "title"
ATTR_OUTPUT_FILE: Final = "output_file"
ATTR_TYPE: Final = "type"

DEFAULT_FORECAST_TYPE: Final = "daily"
DEFAULT_OUTPUT_FILE: Final = "/config/www/weather/latest.png"
SUPPORTED_FORECAST_TYPES: Final = ("daily", "hourly")

WEATHER_DOMAIN: Final = "weather"
WEATHER_GET_FORECASTS_SERVICE: Final = "get_forecasts"

CURRENT_HEIGHT: Final = 320
FORECAST_HEIGHT: Final = 140
CANVAS_WIDTH: Final = 520
CANVAS_HEIGHT: Final = CURRENT_HEIGHT + FORECAST_HEIGHT
FORECAST_BOX_COUNT: Final = 4

DAY_LEFT_COLOR: Final = "#FFD982"
DAY_RIGHT_COLOR: Final = "#5ECEF6"
DAY_TEXT_COLOR: Final = "#000000"

NIGHT_LEFT_COLOR: Final = "#25395C"
NIGHT_RIGHT_COLOR: Final = "#1C2A4F"
NIGHT_TEXT_COLOR: Final = "#FFFFFF"

FORECAST_BG_COLOR: Final = "#DDDDDD"
FORECAST_BOX_COLOR: Final = "#EEEEEE"
FORECAST_TEXT_COLOR: Final = "#000000"
