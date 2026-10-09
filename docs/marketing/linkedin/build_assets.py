"""Build DataForge AI LinkedIn marketing assets.

Outputs (into this directory):
  * linkedin-post-1200x627.png     -- link/share card image
  * linkedin-square-1080x1080.png  -- square feed post image
  * linkedin-cover-1584x396.png    -- profile / company page banner
  * dataforge-linkedin-promo.mp4   -- 1080x1080 promo video (H.264, silent)

The visual language mirrors apps/web/app/globals.css: near-black canvas, a
single warm gold accent, editorial serif display type, faint grid + radial glow.

Run:  python docs/marketing/linkedin/build_assets.py
"""

from __future__ import annotations

import math
import os
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SHOTS = ROOT / "docs" / "user-guide" / "screenshots"

# --- palette (mirrors the web app design tokens) -------------------------------
CANVAS = (9, 9, 11)
SURFACE = (18, 18, 22)
SURFACE_2 = (26, 26, 32)
LINE = (44, 44, 53)
INK_900 = (244, 241, 234)
INK_700 = (198, 194, 184)
INK_500 = (138, 134, 126)
GOLD_500 = (224, 163, 60)
GOLD_400 = (233, 189, 110)
GOLD_300 = (242, 206, 142)
GOLD_INK = (26, 18, 6)
GOLD_DEEP = (36, 27, 12)

FONTS = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
_SERO = str(FONTS / "georgia.ttf")
_SERO_B = str(FONTS / "georgiab.ttf")
_SERO_I = str(FONTS / "georgiai.ttf")
_SANS = str(FONTS / "segoeui.ttf")
_SANS_SB = str(FONTS / "seguisb.ttf")
_SANS_L = str(FONTS / "segoeuil.ttf")
_SANS_B = str(FONTS / "segoeuib.ttf")

_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, size)
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, size)
    return _font_cache[key]


# --- math helpers -------------------------------------------------------------
def clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1 else x)


def ease_out(x: float) -> float:
    x = clamp01(x)
    return 1.0 - (1.0 - x) ** 3


def ease_io(x: float) -> float:
    x = clamp01(x)
    return x * x * (3.0 - 2.0 * x)


def win(t: float, start: float, dur: float, fade_in: float = 0.7,
        fade_out: float = 0.6) -> float:
    """Alpha for an element visible over [start, start+dur]."""
    if t < start or t > start + dur:
        return 0.0
    return min(ease_out((t - start) / fade_in),
               ease_out((start + dur - t) / fade_out))


def progress(t: float, start: float, dur: float) -> float:
    return ease_out(clamp01((t - start) / dur))


# --- drawing primitives -------------------------------------------------------
def tracked(draw: ImageDraw.ImageDraw, center_x: float, y: float, text: str,
            fnt: ImageFont.FreeTypeFont, fill, tracking: float = 0.0) -> None:
    """Draw letter-spaced (tracked) text centred horizontally on center_x."""
    widths = [draw.textlength(c, font=fnt) for c in text]
    total = sum(widths) + tracking * max(0, len(text) - 1)
    x = center_x - total / 2.0
    for ch, w in zip(text, widths):
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="ls")
        x += w + tracking


def tracked_left(draw: ImageDraw.ImageDraw, x: float, y: float, text: str,
                 fnt: ImageFont.FreeTypeFont, fill, tracking: float = 0.0) -> None:
    """Letter-spaced text with its baseline starting at (x, y)."""
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor="ls")
        x += draw.textlength(ch, font=fnt) + tracking


def pill_left(draw: ImageDraw.ImageDraw, x: float, cy: float, text: str,
              size: int) -> float:
    """Left-aligned gold CTA pill; returns its width."""
    f = font(_SANS_B, size)
    tw = draw.textlength(text, font=f)
    px = size * 1.15
    h = size * 2.45
    w = tw + px * 2
    draw.rounded_rectangle([x, cy - h / 2, x + w, cy + h / 2], radius=h / 2,
                           fill=GOLD_500)
    draw.text((x + w / 2, cy), text, font=f, fill=GOLD_INK, anchor="mm")
    return w


def center(draw: ImageDraw.ImageDraw, cx: float, y: float, text: str,
           fnt: ImageFont.FreeTypeFont, fill) -> None:
    draw.text((cx, y), text, font=fnt, fill=fill, anchor="ms")


def radial_glow(size: tuple[int, int], center_xy: tuple[float, float],
                radius: float, color, strength: float) -> Image.Image:
    """A soft radial wash of `color`, returning an RGBA layer."""
    w, h = size
    n = 96
    mask = Image.new("L", (n, n), 0)
    px = mask.load()
    cx, cy = center_xy[0] / w * n, center_xy[1] / h * n
    r = max(1.0, radius / w * n)
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - cx, y - cy) / r
            v = 0.0 if d >= 1.0 else (1.0 - d) ** 2
            px[x, y] = int(255 * v * strength)
    mask = mask.resize(size, Image.BILINEAR)
    layer = Image.new("RGBA", size, color + (0,))
    layer.putalpha(mask)
    return layer


def backdrop(size: tuple[int, int], glow_xy=(0.5, -0.05), strength: float = 1.0,
             grid: bool = True) -> Image.Image:
    """Canvas + gold glow + faint grid + vignette."""
    w, h = size
    img = Image.new("RGBA", size, CANVAS + (255,))
    img.alpha_composite(radial_glow(size, (glow_xy[0] * w, glow_xy[1] * h),
                                    w * 0.75, GOLD_500, 0.13 * strength))
    img.alpha_composite(radial_glow(size, (w * 1.02, h * 0.02),
                                    w * 0.5, GOLD_500, 0.07 * strength))
    if grid:
        g = Image.new("RGBA", size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(g)
        step = max(48, w // 22)
        for x in range(0, w + step, step):
            gd.line([(x, 0), (x, h)], fill=(255, 255, 255, 7), width=1)
        for y in range(0, h + step, step):
            gd.line([(0, y), (w, y)], fill=(255, 255, 255, 7), width=1)
        img.alpha_composite(g)
    # Vignette: soft darkening at the edges.
    vig = Image.new("L", size, 0)
    vd = ImageDraw.Draw(vig)
    vd.ellipse([-w * 0.35, -h * 0.35, w * 1.35, h * 1.35], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w * 0.07))
    dark = Image.new("RGBA", size, (0, 0, 0, 200))
    dark.putalpha(Image.eval(vig, lambda v: int((255 - v) * 0.9)))
    img.alpha_composite(dark)
    return img


def logo_mark(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float) -> None:
    """The DataForge gold hexagon mark, drawn to match components/Logo.tsx."""
    half = size / 2.0
    draw.rounded_rectangle([cx - half, cy - half, cx + half, cy + half],
                           radius=size * 0.28, fill=GOLD_500)
    r_out = size * 0.40
    pts = [(cx + r_out * math.cos(math.radians(-90 + k * 60)),
            cy + r_out * math.sin(math.radians(-90 + k * 60))) for k in range(6)]
    draw.line(pts + [pts[0]], fill=GOLD_INK, width=max(2, int(size * 0.055)),
              joint="curve")
    r_in = size * 0.20
    draw.polygon([(cx + r_in * math.cos(math.radians(-90 + k * 60)),
                   cy + r_in * math.sin(math.radians(-90 + k * 60))) for k in range(6)],
                 fill=GOLD_INK)


def pill(draw: ImageDraw.ImageDraw, cx: float, cy: float, text: str, size: int,
         pad_x: float | None = None) -> None:
    f = font(_SANS_B, size)
    tw = draw.textlength(text, font=f)
    px = pad_x if pad_x is not None else size * 1.15
    h = size * 2.45
    draw.rounded_rectangle([cx - tw / 2 - px, cy - h / 2, cx + tw / 2 + px, cy + h / 2],
                           radius=h / 2, fill=GOLD_500)
    draw.text((cx, cy), text, font=f, fill=GOLD_INK, anchor="mm")


_card_cache: dict[tuple[str, int], Image.Image] = {}


def card(shot: Path, target_w: int, radius: int = 20, pad: int = 46) -> Image.Image:
    """A screenshot framed as a floating card (rounded, hairline border, shadow)."""
    key = (str(shot), target_w, radius)
    if key in _card_cache:
        return _card_cache[key]
    src = Image.open(shot).convert("RGB")
    scale = target_w / src.width
    src = src.resize((target_w, max(1, int(src.height * scale))), Image.LANCZOS)
    w, h = src.size
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], radius=radius, fill=255)
    # Shadow
    sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    sh.paste(Image.new("RGBA", (w, h), (0, 0, 0, 235)), (pad, pad + 16), mask)
    sh = sh.filter(ImageFilter.GaussianBlur(pad * 0.55))
    canvas.alpha_composite(sh)
    # Body + hairline border
    canvas.paste(src, (pad, pad), mask)
    bd = ImageDraw.Draw(canvas)
    bd.rounded_rectangle([pad, pad, pad + w - 1, pad + h - 1], radius=radius,
                         outline=(70, 62, 44, 255), width=max(1, w // 700))
    _card_cache[key] = canvas
    return canvas


def paste_card(base: Image.Image, framed: Image.Image, cx: float, cy: float,
               scale: float, alpha: float) -> None:
    if alpha <= 0.001:
        return
    c = framed
    if abs(scale - 1.0) > 0.002:
        c = framed.resize((max(2, int(framed.width * scale)),
                           max(2, int(framed.height * scale))), Image.LANCZOS)
    if alpha < 0.999:
        c = c.copy()
        c.putalpha(c.getchannel("A").point(lambda v: int(v * alpha)))
    base.alpha_composite(c, (int(cx - c.width / 2), int(cy - c.height / 2)))


# --- banner layouts -----------------------------------------------------------
def build_post_card(w: int, h: int, path: Path) -> None:
    img = backdrop((w, h), glow_xy=(0.22, -0.12), strength=1.15)
    d = ImageDraw.Draw(img)
    m = int(w * 0.062)

    # Brand row, top-left.
    logo_mark(d, m + 27, m + 27, 54)
    d.text((m + 78, m + 8), "DataForge AI", font=font(_SANS_B, 32), fill=INK_900)
    d.text((m + 78, m + 48), "Business data intelligence", font=font(_SANS, 21),
           fill=INK_500)

    # Product peek, right.
    c = card(SHOTS / "03-analyst.png", 500, radius=16, pad=42)
    paste_card(img, c, w - 296, h * 0.5 + 34, 1.0, 1.0)

    # Headline column, left.
    tracked_left(d, m, 268, "EVERY ORGANIZATION SITS ON ANSWERS",
                 font(_SANS_SB, 18), GOLD_400, tracking=3.4)
    head = font(_SERO, 64)
    d.text((m, 352), "Most never", font=head, fill=INK_900, anchor="ls")
    d.text((m, 424), "find them.", font=head, fill=GOLD_500, anchor="ls")
    sub = font(_SANS, 20)
    for i, line in enumerate(["Plain-language questions become",
                              "read-only SQL — grounded in your",
                              "documents and cited every time."]):
        d.text((m, 494 + i * 28), line, font=sub, fill=INK_700, anchor="ls")
    bw = pill_left(d, m, 590, "Request a conversation", 20)
    d.text((m + bw + 24, 598), "data-forge.ai", font=font(_SANS, 20),
           fill=INK_500, anchor="ls")
    img.convert("RGB").save(path, "PNG", optimize=True)


def build_square(w: int, h: int, path: Path) -> None:
    img = backdrop((w, h), glow_xy=(0.5, -0.08), strength=1.25)
    d = ImageDraw.Draw(img)
    cx = w / 2

    logo_mark(d, cx, h * 0.175, 132)
    d.text((cx, h * 0.265), "DataForge AI", font=font(_SERO_B, 62), fill=INK_900,
           anchor="ms")
    tracked(d, cx, h * 0.315, "BUSINESS DATA INTELLIGENCE", font(_SANS_SB, 22),
            GOLD_400, tracking=6.5)

    tracked(d, cx, h * 0.425, "READ-ONLY SQL · CITED SOURCES · FULL AUDIT TRAIL",
            font(_SANS_SB, 19), GOLD_400, tracking=3.4)

    head = font(_SERO, 76)
    d.text((cx, h * 0.485), "Ask your business data", font=head, fill=INK_900,
           anchor="ms")
    d.text((cx, h * 0.555), "anything.", font=head, fill=GOLD_500, anchor="ms")

    d.text((cx, h * 0.63),
           "Every answer is grounded in your connected databases and documents,",
           font=font(_SANS, 25), fill=INK_700, anchor="ms")
    d.text((cx, h * 0.63 + 36),
           "scoped to your role, and recorded in a tamper-evident audit log.",
           font=font(_SANS, 25), fill=INK_700, anchor="ms")

    d.line([(cx - 250, h * 0.735), (cx + 250, h * 0.735)], fill=(70, 62, 44), width=2)
    pill(d, cx, h * 0.80, "Request a conversation", 26)
    d.text((cx, h * 0.885), "data-forge.ai", font=font(_SANS, 25), fill=INK_500,
           anchor="ms")
    img.convert("RGB").save(path, "PNG", optimize=True)


def build_cover(w: int, h: int, path: Path) -> None:
    img = backdrop((w, h), glow_xy=(0.12, -0.3), strength=1.0, grid=True)
    d = ImageDraw.Draw(img)
    m = int(h * 0.17)

    logo_mark(d, m + 30, h / 2, 76)
    d.text((m + 84, h / 2 - 30), "DataForge AI", font=font(_SERO_B, 44), fill=INK_900)
    d.text((m + 86, h / 2 + 12), "Business data intelligence", font=font(_SANS, 21),
           fill=INK_500)

    d.line([(m + 400, h * 0.24), (m + 400, h * 0.76)], fill=(70, 62, 44), width=2)

    tracked(d, m + 468, h * 0.38, "EVERY ORGANIZATION SITS ON ANSWERS",
            font(_SANS_SB, 19), GOLD_400, tracking=4.0)
    d.text((m + 460, h * 0.52), "Most never find them.", font=font(_SERO, 46),
           fill=INK_900)
    d.text((m + 460, h * 0.52 + 58),
           "Ask your business data anything — with read-only SQL, cited sources",
           font=font(_SANS, 21), fill=INK_700)
    d.text((m + 460, h * 0.52 + 88), "and a tamper-evident audit trail.",
           font=font(_SANS, 21), fill=INK_700)

    pill(d, w - 250, h / 2, "Request a conversation", 20)
    img.convert("RGB").save(path, "PNG", optimize=True)


# --- video --------------------------------------------------------------------
FPS = 30
SW = SH = 1080
DURATION = 34.0


def _text_block(layer, cx, items, t, start):
    """Staggered fade-up of lines. items: list of (text, font, fill, dy)."""
    d = ImageDraw.Draw(layer)
    for i, (text, fnt, fill, dy) in enumerate(items):
        p = ease_out(clamp01((t - start - i * 0.12) / 0.75))
        if p <= 0:
            continue
        d.text((cx, dy + (1 - p) * 22), text, font=fnt, fill=fill + (int(255 * p),),
               anchor="ms")


def render_frame(t: float) -> Image.Image:
    img = backdrop((SW, SH), glow_xy=(0.5 + 0.06 * math.sin(t * 0.35), -0.05),
                   strength=1.15).convert("RGBA")
    cx = SW / 2

    # --- Scene A: brand intro -------------------------------------------------
    a = win(t, 0.0, 5.4, 0.9, 0.7)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        p = ease_out(clamp01(t / 1.0))
        logo_mark(d, cx, 372 + (1 - p) * 26, 168)
        d.text((cx, 612), "DataForge AI", font=font(_SERO_B, 96),
               fill=INK_900 + (int(255 * a * ease_out(clamp01((t - 0.25) / 0.9))),),
               anchor="ms")
        tracked(d, cx, 706, "BUSINESS DATA INTELLIGENCE", font(_SANS_SB, 26),
                GOLD_400 + (int(255 * a * ease_out(clamp01((t - 0.5) / 0.9))),),
                tracking=8.0)
        _fade(lay, a)
        img.alpha_composite(lay)

    # --- Scene B: the problem -------------------------------------------------
    a = win(t, 4.6, 5.8, 0.7, 0.6)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tracked(d, cx, 400, "THE PROBLEM", font(_SANS_SB, 21), GOLD_400, tracking=6.0)
        head = font(_SERO, 72)
        _text_block(lay, cx, [
            ("Every organization", head, INK_900, 480),
            ("sits on answers.", head, INK_900, 566),
            ("Most never find them.", font(_SERO_I, 68), GOLD_500, 676),
        ], t, 4.6)
        _fade(lay, a)
        img.alpha_composite(lay)

    # --- Scene C: the analyst -------------------------------------------------
    a = win(t, 9.8, 7.6, 0.7, 0.6)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tracked(d, cx, 132, "THE AI ANALYST", font(_SANS_SB, 20), GOLD_400, tracking=5.6)
        _text_block(lay, cx, [
            ("Ask your data anything.", font(_SERO, 62), INK_900, 208),
            ("Plain-language questions become read-only SQL over your connected",
             font(_SANS, 25), INK_700, 274),
            ("databases — grounded in your documents, with the sources cited.",
             font(_SANS, 25), INK_700, 306),
        ], t, 9.8)
        c = card(SHOTS / "03-analyst.png", 880)
        p = progress(t, 10.2, 1.1)
        paste_card(lay, c, cx, 672 + (1 - p) * 60, 0.95 + 0.05 * progress(t, 10.2, 4.0), a)
        # capability chips
        chips = ["Read-only SQL", "Cited sources", "Every run audited"]
        f = font(_SANS_SB, 20)
        widths = [d.textlength(s, font=f) + 52 for s in chips]
        total = sum(widths) + 22 * (len(chips) - 1)
        x = cx - total / 2
        for i, (s, w) in enumerate(zip(chips, widths)):
            ca = ease_out(clamp01((t - 11.6 - i * 0.18) / 0.6))
            if ca <= 0:
                continue
            y = 1014
            d.rounded_rectangle([x, y - 22, x + w, y + 22], radius=22,
                                fill=SURFACE_2 + (int(255 * a * ca),),
                                outline=(70, 62, 44, int(255 * a * ca)), width=1)
            d.text((x + w / 2, y), s, font=f, fill=INK_900 + (int(255 * a * ca),),
                   anchor="mm")
            x += w + 22
        _fade(lay, a)
        img.alpha_composite(lay)

    # --- Scene D: access control ---------------------------------------------
    a = win(t, 17.6, 7.4, 0.7, 0.6)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tracked(d, cx, 132, "ACCESS CONTROL", font(_SANS_SB, 20), GOLD_400, tracking=5.6)
        _text_block(lay, cx, [
            ("Scoped to the person asking.", font(_SERO, 62), INK_900, 208),
            ("Role-based permissions decide which databases and documents each",
             font(_SANS, 25), INK_700, 274),
            ("teammate can reach — and what the analyst may query on their behalf.",
             font(_SANS, 25), INK_700, 306),
        ], t, 17.6)
        c = card(SHOTS / "10-settings.png", 900)
        p = progress(t, 18.0, 1.1)
        paste_card(lay, c, cx, 700 + (1 - p) * 60, 0.95 + 0.05 * progress(t, 18.0, 4.0), a)
        _fade(lay, a)
        img.alpha_composite(lay)

    # --- Scene E: audit -------------------------------------------------------
    a = win(t, 25.2, 5.2, 0.7, 0.6)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        tracked(d, cx, 132, "AUDIT & GOVERNANCE", font(_SANS_SB, 20), GOLD_400,
                tracking=5.6)
        _text_block(lay, cx, [
            ("Answers you can defend.", font(_SERO, 62), INK_900, 208),
            ("Append-only audit logs record every security-relevant action.",
             font(_SANS, 25), INK_700, 274),
            ("Entries are never edited or deleted.",             font(_SANS, 25), INK_700, 306),
        ], t, 25.2)
        c = card(SHOTS / "09-audit.png", 900)
        p = progress(t, 25.6, 1.1)
        paste_card(lay, c, cx, 700 + (1 - p) * 60, 0.95 + 0.05 * progress(t, 25.6, 3.4), a)
        _fade(lay, a)
        img.alpha_composite(lay)

    # --- Scene F: CTA ---------------------------------------------------------
    a = win(t, 30.2, 4.0, 0.8, 0.55)
    if a > 0:
        lay = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        logo_mark(d, cx, 280, 116)
        d.text((cx, 424), "DataForge AI", font=font(_SERO_B, 72), fill=INK_900,
               anchor="ms")
        d.text((cx, 516), "See your data answer back.", font=font(_SERO, 54),
               fill=GOLD_500, anchor="ms")
        pill(d, cx, 652, "Request a conversation", 26)
        d.text((cx, 742), "data-forge.ai", font=font(_SANS, 25), fill=INK_500,
               anchor="ms")
        d.text((cx, 802), "Read-only SQL · Cited sources · Full audit trail",
               font=font(_SANS_SB, 21), fill=INK_500, anchor="ms")
        _fade(lay, a)
        img.alpha_composite(lay)

    return img.convert("RGB")


def _fade(layer: Image.Image, alpha: float) -> None:
    if alpha >= 0.999:
        return
    layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))


def encode(out: Path) -> None:
    import imageio_ffmpeg

    exe = imageio_ffmpeg.get_ffmpeg_exe()
    frames = int(round(DURATION * FPS))
    cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo",
           "-pix_fmt", "rgb24", "-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
           "-movflags", "+faststart", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    t0 = time.time()
    try:
        for i in range(frames):
            proc.stdin.write(render_frame(i / FPS).tobytes())
            if i % 60 == 0:
                print(f"  frame {i}/{frames}  ({time.time() - t0:5.1f}s)", flush=True)
    finally:
        proc.stdin.close()
        rc = proc.wait()
    if rc != 0:
        raise SystemExit(f"ffmpeg failed with exit code {rc}")


def preview_stills() -> None:
    """One still per scene, kept alongside the video as a storyboard."""
    stamps = [(1.6, "intro"), (6.4, "problem"), (12.6, "analyst"),
              (20.6, "access"), (27.0, "audit"), (32.4, "cta")]
    for i, (s, slug) in enumerate(stamps, start=1):
        render_frame(s).save(HERE / f"storyboard-{i}-{s:04.1f}s-{slug}.png", "PNG")


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "banners"):
        print("banners...", flush=True)
        build_post_card(1200, 627, HERE / "linkedin-post-1200x627.png")
        build_square(1080, 1080, HERE / "linkedin-square-1080x1080.png")
        build_cover(1584, 396, HERE / "linkedin-cover-1584x396.png")
    if which in ("all", "stills"):
        print("preview stills...", flush=True)
        preview_stills()
    if which in ("all", "video"):
        print("video...", flush=True)
        encode(HERE / "dataforge-linkedin-promo.mp4")
    print("done: " + str(HERE), flush=True)


if __name__ == "__main__":
    main()
