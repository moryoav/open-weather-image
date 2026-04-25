# Weather Image

`weather_image` is a Home Assistant custom integration that renders a weather PNG in the visual style of the original `open-weather-image` package.

It exposes a single service, `weather_image.generate`, which:

- reads current conditions from a Home Assistant weather entity such as `weather.openweathermap`
- fetches forecast data through `weather.get_forecasts`
- renders a PNG using Python + Pillow and the bundled weather icon font
- saves the result under `/config/www/...` so it is immediately available through `/local/...`

The renderer keeps the legacy layout as closely as possible:

- `520px` wide card
- split two-tone day/night header
- oversized right-hand weather glyph
- large temperature block on the left
- four forecast boxes across the bottom rail

## HACS Installation

1. In HACS, add this repository as a custom repository with type `Integration`.
2. Download `Weather Image` from HACS.
3. Restart Home Assistant.
4. Go to `Settings > Devices & services`.
5. Click `Add Integration`.
6. Search for `Weather Image` and add it.

No `configuration.yaml` entry is required.

## Important For Maintainers

This repository now includes a root `hacs.json`, which is required for HACS branch/default-branch installs to work correctly.

If you want HACS to show a real version like `1.0.0` instead of a commit SHA, publish a GitHub release after pushing your changes. HACS uses the latest GitHub release as the repository version when one exists; tags alone are not enough.

## Service

Service: `weather_image.generate`

Fields:

- `entity_id`: Weather entity to render, typically `weather.openweathermap`
- `forecast_type`: `daily` or `hourly`
- `title`: Optional title override
- `output_file`: Optional output path inside `/config/www`, defaults to `/config/www/weather/latest.png`

Example:

```yaml
action: weather_image.generate
data:
  entity_id: weather.openweathermap
  forecast_type: daily
  title: Home Forecast
  output_file: /config/www/weather/latest.png
```

After the service runs, the default image is available at:

```text
/local/weather/latest.png
```

## Notes

- The service always writes PNG files and only allows output paths under `/config/www`.
- Daily mode renders the next four forecast days.
- Hourly mode renders the next four upcoming forecast points.
- The current weather panel uses the selected weather entity's live state attributes.
- The lower-right detail area prefers sunrise and sunset values when the forecast payload includes them, and otherwise falls back to pressure and visibility.

## Repository Layout

- `custom_components/weather_image/__init__.py`: integration setup and service registration
- `custom_components/weather_image/config_flow.py`: UI setup flow
- `custom_components/weather_image/service.py`: Home Assistant data collection and normalization
- `custom_components/weather_image/renderer.py`: Pillow renderer
- `custom_components/weather_image/weathericons-font.ttf`: bundled icon font used for the card glyphs
- `hacs.json`: HACS repository metadata

## License

This repository remains under the MIT license. See `LICENSE.md`.
