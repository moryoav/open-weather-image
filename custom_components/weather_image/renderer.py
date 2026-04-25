"""Pillow renderer for the Weather Image infographic."""

from __future__ import annotations

from pathlib import Path
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont

from .const import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    CURRENT_HEIGHT,
    DAY_LEFT_COLOR,
    DAY_RIGHT_COLOR,
    DAY_TEXT_COLOR,
    FORECAST_BG_COLOR,
    FORECAST_BOX_COLOR,
    FORECAST_BOX_COUNT,
    FORECAST_TEXT_COLOR,
    NIGHT_LEFT_COLOR,
    NIGHT_RIGHT_COLOR,
    NIGHT_TEXT_COLOR,
)
from .models import ForecastItem, WeatherImagePayload


_ICON_MAP: dict[str, dict[str, str] | str] = {
    "sunny": "\uf00d",
    "clear-night": "\uf02e",
    "partlycloudy": {"day": "\uf002", "night": "\uf086"},
    "cloudy": "\uf041",
    "fog": {"day": "\uf003", "night": "\uf04a"},
    "hail": "\uf015",
    "lightning": "\uf01e",
    "lightning-rainy": "\uf01e",
    "pouring": "\uf019",
    "rainy": "\uf019",
    "snowy": "\uf01b",
    "snowy-rainy": "\uf017",
    "windy": "\uf050",
    "windy-variant": "\uf011",
    "exceptional": "\uf07b",
}

SUNRISE_GLYPH = "\uf051"
SUNSET_GLYPH = "\uf052"


def save_weather_image(payload: WeatherImagePayload, output_path: Path) -> None:
    """Render and atomically save the weather image to disk."""
    image = render_weather_image(payload)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=output_path.parent,
            suffix=".png",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

        image.save(temp_path, format="PNG", optimize=True)
        os.replace(temp_path, output_path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def render_weather_image(payload: WeatherImagePayload) -> Image.Image:
    """Render a weather infographic using the legacy package layout."""
    image = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), FORECAST_BG_COLOR)
    draw = ImageDraw.Draw(image)

    left_color, right_color, text_color = _theme_colors(payload.is_daytime)
    line_color = _with_alpha(text_color, 110)

    left_width = int(CANVAS_WIDTH * (2 / 3)) + 1
    draw.rectangle((0, 0, left_width, CURRENT_HEIGHT), fill=left_color)
    draw.rectangle((left_width - 1, 0, CANVAS_WIDTH, CURRENT_HEIGHT), fill=right_color)

    _draw_current_panel(draw, payload, left_width, text_color, line_color)
    _draw_forecast_panel(draw, payload)

    return image


def _draw_current_panel(
    draw: ImageDraw.ImageDraw,
    payload: WeatherImagePayload,
    left_width: int,
    text_color: str,
    line_color: tuple[int, int, int, int],
) -> None:
    left_pos = 22
    right_panel_center = left_width + (CANVAS_WIDTH - left_width) / 2

    eyebrow_font = _load_text_font(13)
    location_font = _fit_text_font(
        draw,
        payload.location_text,
        left_width - left_pos - 22,
        38 if payload.header_title is None else 32,
        minimum=20,
        bold=True,
    )
    subtitle_font = _load_text_font(16)
    temp_font = _load_text_font(44, bold=True)
    body_font = _load_text_font(16)
    small_font = _load_text_font(12)
    icon_font = _load_icon_font(20)
    large_icon_font = _load_icon_font(82)

    divider_y = 100
    if payload.header_title:
        eyebrow_color = _with_alpha(text_color, 190)
        draw.text(
            (left_pos, 30),
            payload.header_title,
            font=eyebrow_font,
            fill=eyebrow_color,
            anchor="ls",
        )
        location_y = 62
        subtitle_y = 88
    else:
        location_y = 62
        subtitle_y = 88

    draw.text(
        (left_pos, location_y),
        payload.location_text,
        font=location_font,
        fill=text_color,
        anchor="ls",
    )
    draw.text(
        (left_pos, subtitle_y),
        payload.subtitle,
        font=subtitle_font,
        fill=text_color,
        anchor="ls",
    )

    draw.line((15, divider_y, 304, divider_y), fill=line_color, width=1)
    draw.line((15, 200, 304, 200), fill=line_color, width=1)

    draw.text(
        (right_panel_center, 165),
        _condition_icon(payload.condition, payload.is_daytime),
        font=large_icon_font,
        fill=text_color,
        anchor="mm",
    )

    draw.text(
        (left_pos, 145),
        payload.current_temperature,
        font=temp_font,
        fill=text_color,
        anchor="ls",
    )

    if payload.feels_like:
        temp_bbox = draw.textbbox(
            (left_pos, 145),
            payload.current_temperature,
            font=temp_font,
            anchor="ls",
        )
        draw.text(
            (temp_bbox[2] + 8, 145),
            payload.feels_like,
            font=body_font,
            fill=text_color,
            anchor="ls",
        )

    if payload.range_text:
        draw.text(
            (left_pos, 168),
            payload.range_text,
            font=body_font,
            fill=text_color,
            anchor="ls",
        )

    draw.text(
        (left_pos, 191),
        _condition_icon(payload.condition, payload.is_daytime),
        font=icon_font,
        fill=text_color,
        anchor="ls",
    )
    draw.text(
        (56, 191),
        payload.condition_text,
        font=body_font,
        fill=text_color,
        anchor="ls",
    )

    for y_pos, line in zip((218, 233, 248, 263, 278), payload.detail_lines):
        draw.text((left_pos, y_pos), line, font=small_font, fill=text_color, anchor="ls")

    side_icon_font = _load_icon_font(24)
    side_positions = ((199, 228, 235, 221), (199, 258, 235, 251))
    for metric, positions in zip(payload.side_metrics[:2], side_positions):
        icon_x, icon_y, text_x, text_y = positions
        if metric.icon_glyph:
            draw.text(
                (icon_x, icon_y),
                metric.icon_glyph,
                font=side_icon_font,
                fill=text_color,
                anchor="ls",
            )
        draw.text((text_x, text_y), metric.text, font=small_font, fill=text_color, anchor="ls")


def _draw_forecast_panel(draw: ImageDraw.ImageDraw, payload: WeatherImagePayload) -> None:
    top_padding = 15
    side_padding = 12
    box_width = CANVAS_WIDTH / FORECAST_BOX_COUNT
    box_top = CURRENT_HEIGHT + top_padding
    box_bottom = CANVAS_HEIGHT - top_padding

    for index in range(FORECAST_BOX_COUNT):
        box_left = box_width * index + side_padding
        center = box_width * index + (box_width / 2)

        if index != 0:
            draw.line(
                (box_width * index, box_top, box_width * index, box_bottom),
                fill=(0, 0, 0, 120),
                width=1,
            )

        draw.rectangle(
            (
                box_left,
                box_top,
                box_width * (index + 1) - side_padding,
                box_bottom,
            ),
            fill=FORECAST_BOX_COLOR,
        )

        if index >= len(payload.forecast_items):
            continue

        _draw_forecast_box(draw, payload.forecast_items[index], center, box_width - 24)


def _draw_forecast_box(
    draw: ImageDraw.ImageDraw,
    item: ForecastItem,
    center: float,
    content_width: float,
) -> None:
    label_font = _fit_text_font(draw, item.label, content_width, 12, minimum=10)
    icon_font = _load_icon_font(38)
    description_font = _load_text_font(10)
    temp_font = _load_text_font(10)

    description = _trim_text(draw, item.description, description_font, content_width)
    temp_line = item.temperature_high
    if item.temperature_low:
        temp_line = f"{item.temperature_high} / {item.temperature_low}"
    temp_line = _trim_text(draw, temp_line, temp_font, content_width)

    draw.text((center, 347), item.label, font=label_font, fill=FORECAST_TEXT_COLOR, anchor="ms")
    draw.text(
        (center, 389),
        _condition_icon(item.condition, item.is_daytime),
        font=icon_font,
        fill=FORECAST_TEXT_COLOR,
        anchor="mm",
    )
    draw.text(
        (center, 421),
        description,
        font=description_font,
        fill=FORECAST_TEXT_COLOR,
        anchor="ms",
    )
    draw.text((center, 439), temp_line, font=temp_font, fill=FORECAST_TEXT_COLOR, anchor="ms")


def _theme_colors(is_daytime: bool) -> tuple[str, str, str]:
    if is_daytime:
        return DAY_LEFT_COLOR, DAY_RIGHT_COLOR, DAY_TEXT_COLOR
    return NIGHT_LEFT_COLOR, NIGHT_RIGHT_COLOR, NIGHT_TEXT_COLOR


def _condition_icon(condition: str, is_daytime: bool) -> str:
    icon = _ICON_MAP.get(condition)
    if isinstance(icon, dict):
        return icon["day" if is_daytime else "night"]
    if isinstance(icon, str):
        return icon
    return "\uf07b"


def _fit_text_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: float,
    start_size: int,
    minimum: int = 12,
    bold: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    font_size = start_size
    while font_size >= minimum:
        font = _load_text_font(font_size, bold=bold)
        if _text_width(draw, text, font) <= max_width:
            return font
        font_size -= 2
    return _load_text_font(minimum, bold=bold)


def _trim_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: float,
) -> str:
    if _text_width(draw, text, font) <= max_width:
        return text

    ellipsis = "..."
    trimmed = text
    while trimmed and _text_width(draw, f"{trimmed}{ellipsis}", font) > max_width:
        trimmed = trimmed[:-1]
    return f"{trimmed}{ellipsis}" if trimmed else ellipsis


def _text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _load_text_font(
    size: int,
    bold: bool = False,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "DejaVuSans-Bold.ttf",
            "Arial Bold.ttf",
            "arialbd.ttf",
        )
        if bold
        else (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "DejaVuSans.ttf",
            "Arial.ttf",
            "arial.ttf",
        )
    )
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _load_icon_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    icon_path = Path(__file__).with_name("weathericons-font.ttf")
    try:
        return ImageFont.truetype(str(icon_path), size)
    except OSError:
        return _load_text_font(size)


def _with_alpha(hex_color: str, alpha: int) -> tuple[int, int, int, int]:
    value = hex_color.lstrip("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )
