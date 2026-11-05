#!/usr/bin/env python3
"""Generate the integration's brand assets.

The generated files live in custom_components/lg_netcast_hdcp/brand and are
checked in so HACS and Home Assistant can serve them without extra tooling.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BRAND = ROOT / "custom_components" / "lg_netcast_hdcp" / "brand"

BACKGROUND = "#0B1220"
SCREEN = "#111827"
ACCENT = "#2DD4BF"
TEXT = "#F8FAFC"
MUTED = "#94A3B8"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    """Load a font with a safe fallback."""
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _draw_icon(size: int) -> Image.Image:
    """Draw a square TV/HDCP icon at the requested size."""
    scale = 4
    canvas = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    unit = size * scale

    def px(value: float) -> int:
        return int(unit * value)

    draw.rounded_rectangle(
        (px(0.04), px(0.04), px(0.96), px(0.96)),
        radius=px(0.18),
        fill=BACKGROUND,
    )
    draw.rounded_rectangle(
        (px(0.18), px(0.24), px(0.82), px(0.68)),
        radius=px(0.04),
        fill=SCREEN,
        outline=ACCENT,
        width=px(0.025),
    )
    draw.polygon(
        [
            (px(0.43), px(0.35)),
            (px(0.43), px(0.57)),
            (px(0.62), px(0.46)),
        ],
        fill=TEXT,
    )
    draw.line(
        (px(0.42), px(0.76), px(0.58), px(0.76)),
        fill=MUTED,
        width=px(0.025),
    )
    draw.line(
        (px(0.47), px(0.76), px(0.44), px(0.83)),
        fill=MUTED,
        width=px(0.025),
    )
    draw.line(
        (px(0.53), px(0.76), px(0.56), px(0.83)),
        fill=MUTED,
        width=px(0.025),
    )
    draw.text(
        (px(0.5), px(0.885)),
        "HDCP",
        font=_font(FONT_BOLD, px(0.105)),
        fill=TEXT,
        anchor="mm",
    )

    return canvas.resize((size, size), Image.Resampling.LANCZOS)


def _draw_logo(width: int, height: int, *, dark: bool = False) -> Image.Image:
    """Draw a landscape logo with the icon and integration name."""
    scale = 2
    canvas = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    icon_size = int(height * 0.78)
    icon = _draw_icon(icon_size)
    canvas.alpha_composite(icon, (int(height * 0.08), int(height * 0.11)))

    text_color = TEXT if dark else BACKGROUND
    accent_color = ACCENT if dark else "#0F766E"
    text_x = int(height * 0.95)
    draw.text(
        (text_x, int(height * 0.40)),
        "NetCast",
        font=_font(FONT_BOLD, int(height * 0.22)),
        fill=text_color,
        anchor="lm",
    )
    draw.text(
        (text_x, int(height * 0.64)),
        "HDCP",
        font=_font(FONT_REGULAR, int(height * 0.16)),
        fill=accent_color,
        anchor="lm",
    )

    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def main() -> None:
    """Generate all brand assets."""
    BRAND.mkdir(parents=True, exist_ok=True)

    icon_256 = _draw_icon(256)
    icon_256.save(BRAND / "icon.png", optimize=True)
    icon_256.resize((512, 512), Image.Resampling.LANCZOS).save(
        BRAND / "icon@2x.png", optimize=True
    )

    logo = _draw_logo(512, 256)
    logo.save(BRAND / "logo.png", optimize=True)
    logo.resize((1024, 512), Image.Resampling.LANCZOS).save(
        BRAND / "logo@2x.png", optimize=True
    )

    dark_logo = _draw_logo(512, 256, dark=True)
    dark_logo.save(BRAND / "dark_logo.png", optimize=True)
    dark_logo.resize((1024, 512), Image.Resampling.LANCZOS).save(
        BRAND / "dark_logo@2x.png", optimize=True
    )

    for path in sorted(BRAND.glob("*.png")):
        with Image.open(path) as image:
            print(f"{path.relative_to(ROOT)}: {image.size} {image.mode}")


if __name__ == "__main__":
    main()
