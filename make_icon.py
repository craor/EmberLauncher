#!/usr/bin/env python3
"""Рисует icon.png и icon.ico для лаунчера. Не входит в рантайм игры."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent


def _mix(a: tuple[int, ...], b: tuple[int, ...], t: float) -> tuple[int, ...]:
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def render(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    plate = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(plate)
    margin = max(1, int(size * 0.055))
    draw.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=max(2, int(size * 0.23)),
        fill=(14, 16, 15, 255),
    )

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx = size * 0.50
    cy = size * 0.58
    max_r = size * 0.40
    steps = max(10, size // 6)
    for step in range(steps, 0, -1):
        t = step / steps
        radius = max_r * t
        alpha = int(78 * (1.0 - t) ** 1.6)
        color = _mix((255, 122, 32), (255, 214, 140), 1.0 - t)
        glow_draw.ellipse(
            [cx - radius, cy - radius * 0.85, cx + radius, cy + radius * 0.85],
            fill=(*color, alpha),
        )
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1, size // 48)))

    img = Image.alpha_composite(img, plate)
    img = Image.alpha_composite(img, glow)

    mark = ImageDraw.Draw(img)
    s = float(size)
    cx = s * 0.50
    cy = s * 0.53
    top = (cx, cy - s * 0.25)
    right = (cx + s * 0.205, cy - s * 0.015)
    left = (cx - s * 0.205, cy - s * 0.015)
    bottom = (cx, cy + s * 0.27)
    mid = (cx, cy - s * 0.015)
    mark.polygon([top, right, mid], fill=(255, 220, 164, 255))
    mark.polygon([top, mid, left], fill=(255, 164, 64, 255))
    mark.polygon([left, mid, bottom], fill=(176, 62, 18, 255))
    mark.polygon([mid, right, bottom], fill=(226, 112, 32, 255))

    spark = max(1, int(s * 0.028))
    sx, sy = cx, cy - s * 0.09
    mark.ellipse([sx - spark, sy - spark, sx + spark, sy + spark], fill=(255, 250, 240, 235))
    return img


def main() -> None:
    image = render(256)
    image.save(ROOT / "icon.png", "PNG")
    image.save(
        ROOT / "icon.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"wrote {ROOT / 'icon.png'}")
    print(f"wrote {ROOT / 'icon.ico'}")


if __name__ == "__main__":
    main()
