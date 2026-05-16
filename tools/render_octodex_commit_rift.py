#!/usr/bin/env python3
"""Render a cinematic Octodex/GitHub animation preview.

Outputs a 1080p MP4 built from generated sprite sheets in this repo.
"""
from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SPRITES = ROOT / "assets" / "spritesheets"
OUT = ROOT / "previews" / "videos" / "octodex_commit_rift_cinematic.mp4"
OUT.parent.mkdir(parents=True, exist_ok=True)

W, H = 1920, 1080
FPS = 30
DURATION = 13.5
N = int(FPS * DURATION)

BG = (5, 9, 18)
GREEN = (63, 185, 80)
CYAN = (88, 166, 255)
PURPLE = (163, 113, 247)
PINK = (255, 123, 206)
TEXT = (240, 246, 252)
MUTED = (139, 148, 158)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out_cubic(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def pulse(t, start, end):
    return ease_in_out((t - start) / (end - start))


def font(size: int, bold=False):
    paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
    ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size=size)
        except Exception:
            pass
    return ImageFont.load_default()

FONT_BIG = font(96, True)
FONT_MED = font(46, True)
FONT_SMALL = font(24, False)
FONT_MONO = font(22, False)


def load_sheet(name: str) -> List[Image.Image]:
    im = Image.open(SPRITES / name).convert("RGBA")
    fw, fh = im.width // 8, im.height // 2
    return [im.crop((i * fw, 0, (i + 1) * fw, fh)) for i in range(8)]

characters: Dict[str, List[Image.Image]] = {
    "mona": load_sheet("mona_classic_clean_laptop_right_left_spriteforge_v7.png"),
    "rivet": load_sheet("mona_walk_right_left_spriteforge.png"),
    "robot": load_sheet("robotocat_walk_right_left_spriteforge_v2.png"),
    "security": load_sheet("securitocat_walk_right_left_spriteforge_v2.png"),
    "liberty": load_sheet("octoliberty_walk_right_left_spriteforge_v2.png"),
    "jetpack": load_sheet("jetpacktocat_walk_right_left_spriteforge_v2.png"),
    "coder": load_sheet("codercat_right_left_spriteforge_v1.png"),
    "lab": load_sheet("labtocat_right_left_spriteforge_v1.png"),
    "python": load_sheet("pythocat_right_left_spriteforge_v1.png"),
    "obiwan": load_sheet("octobiwan_right_left_spriteforge_v1.png"),
    "dino": load_sheet("dinotocat_walk_right_left_spriteforge_v2.png"),
}

# Trim transparent padding for better placement.
def trim(im: Image.Image) -> Image.Image:
    bb = im.getbbox()
    return im.crop(bb) if bb else im

characters = {k: [trim(f) for f in frames] for k, frames in characters.items()}

rnd = random.Random(42)
stars = [(rnd.randrange(W), rnd.randrange(H), rnd.random() * 1.8 + 0.4, rnd.random() * 6.28) for _ in range(360)]
particles = []
for i in range(260):
    particles.append({
        "a": rnd.random() * math.tau,
        "r": rnd.uniform(80, 620),
        "s": rnd.uniform(.5, 1.9),
        "phase": rnd.random() * math.tau,
        "color": rnd.choice([GREEN, CYAN, PURPLE, PINK]),
    })

commit_nodes = []
for branch in range(7):
    x0 = 180 + branch * 260
    y0 = 160 + rnd.randrange(0, 120)
    nodes = []
    for j in range(9):
        nodes.append((x0 + j * 92 + rnd.randrange(-20, 20), y0 + math.sin(j * .9 + branch) * 55 + branch * 78))
    commit_nodes.append(nodes)

lineup = [
    ("robot", -160, 650, .40, 1.2),
    ("dino", -260, 690, .38, 1.7),
    ("security", -340, 635, .39, 2.0),
    ("liberty", -430, 650, .36, 2.5),
    ("jetpack", -520, 610, .36, 3.1),
    ("coder", -630, 680, .36, 3.5),
    ("lab", -720, 690, .36, 4.0),
    ("python", -820, 670, .35, 4.4),
    ("obiwan", -900, 660, .35, 4.8),
    ("rivet", -1030, 685, .32, 5.0),
]


def gradient_bg(t: float) -> Image.Image:
    img = Image.new("RGB", (W, H), BG)
    pix = img.load()
    for y in range(H):
        f = y / H
        r = int(5 + 9 * f + 10 * math.sin(t * .18 + f * 3))
        g = int(9 + 18 * f)
        b = int(18 + 38 * f + 20 * math.sin(t * .23 + f * 5))
        for x in range(W):
            pix[x, y] = (r, g, b)
    return img.convert("RGBA")


def glow_line(layer, pts, fill, width=3, blur=9):
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(pts, fill=(*fill, 140), width=width * 4, joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(blur))
    layer.alpha_composite(glow)
    d = ImageDraw.Draw(layer)
    d.line(pts, fill=(*fill, 220), width=width, joint="curve")


def draw_background(img: Image.Image, t: float):
    d = ImageDraw.Draw(img, "RGBA")
    # Stars
    for x, y, r, ph in stars:
        tw = .45 + .55 * math.sin(t * 1.7 + ph)
        alpha = int(35 + 130 * tw)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(190, 220, 255, alpha))

    # Contribution grid wall / floor
    grid_alpha = int(85 + 65 * pulse(t, .3, 2.8))
    cell = 22
    start_x, start_y = 190, 775
    for gy in range(10):
        for gx in range(56):
            wave = math.sin(gx * .28 + gy * .65 - t * 3.4)
            diag = math.sin((gx + gy) * .18 - t * 2.0)
            v = clamp((wave + diag + 2) / 4)
            if rnd.random() < -1:  # deterministic no-op; avoids lint-y mood
                pass
            alpha = int(grid_alpha * (0.15 + v * .85))
            col = GREEN if v > .58 else (35, 134, 54)
            x = start_x + gx * (cell + 3)
            y = start_y + gy * (cell + 3) + int(gy * gy * 2.2)
            if x > W - 160 or y > H - 30:
                continue
            d.rounded_rectangle((x, y, x + cell, y + cell), radius=5, fill=(*col, alpha))

    # Branch graph in sky
    graph_on = pulse(t, 1.0, 4.0)
    for bi, nodes in enumerate(commit_nodes):
        pts = []
        for j, (x, y) in enumerate(nodes):
            xx = x + math.sin(t * .45 + j) * 18
            yy = y + math.cos(t * .3 + bi) * 12
            pts.append((xx, yy))
        color = [GREEN, CYAN, PURPLE, PINK][bi % 4]
        glow_line(img, pts, color, width=2, blur=7)
        for j, (x, y) in enumerate(pts):
            appear = pulse(t, 1.1 + j * .05, 2.4 + j * .05)
            rr = 5 + 3 * math.sin(t * 3 + j)
            d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=(*color, int(180 * graph_on * appear)))


def draw_portal(img: Image.Image, t: float):
    d = ImageDraw.Draw(img, "RGBA")
    c = (1285, 470)
    power = pulse(t, 4.3, 7.4) * (1 - .25 * pulse(t, 11.4, 13.2))
    if power <= 0:
        return
    portal = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(portal, "RGBA")
    for k in range(9):
        r = (70 + k * 28 + 18 * math.sin(t * 2.7 + k)) * power
        col = [GREEN, CYAN, PURPLE][k % 3]
        a = int((85 - k * 5) * power)
        pd.ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=(*col, a), width=max(2, int(5 * power)))
    # GitHub-ish commit burst squares
    for p in particles:
        a = p["a"] + t * .9 * p["s"]
        r = p["r"] * (.22 + .78 * power) * (0.55 + .45 * math.sin(t * .9 + p["phase"]) ** 2)
        x = c[0] + math.cos(a) * r * .9
        y = c[1] + math.sin(a) * r * .52
        size = 2 + 5 * (1 - r / 650) * power
        alpha = int(30 + 170 * power * (1 - clamp(r / 760)))
        pd.rounded_rectangle((x - size, y - size, x + size, y + size), radius=2, fill=(*p["color"], alpha))
    portal = portal.filter(ImageFilter.GaussianBlur(1.2))
    img.alpha_composite(portal)
    # Core
    rr = 18 + 28 * math.sin(t * 6) ** 2
    d.ellipse((c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr), fill=(255, 255, 255, int(120 * power)))


def draw_title(img: Image.Image, t: float):
    d = ImageDraw.Draw(img, "RGBA")
    # Opening title
    a = int(255 * (1 - pulse(t, 3.1, 4.2)))
    if a > 0:
        txt = "OCTODEX"
        sub = "COMMIT RIFT"
        # Letter stagger
        x0 = 120
        for i, ch in enumerate(txt):
            p = pulse(t, .25 + i * .06, 1.25 + i * .06)
            y = 108 - int((1 - p) * 55)
            d.text((x0 + i * 74, y), ch, font=FONT_BIG, fill=(*TEXT, int(a * p)))
        p2 = pulse(t, 1.2, 2.4)
        d.text((126, 205), sub, font=FONT_MED, fill=(*GREEN, int(a * p2)))
        d.text((128, 260), "A tiny cinematic built from generated Octodex sprites", font=FONT_SMALL, fill=(*MUTED, int(a * p2)))
    # Final card
    fa = int(255 * pulse(t, 10.4, 12.8))
    if fa:
        d.rounded_rectangle((505, 74, 1415, 202), radius=28, fill=(1, 4, 9, int(150 * fa / 255)), outline=(*GREEN, int(160 * fa / 255)), width=2)
        d.text((545, 98), "github-brand-animations", font=FONT_MED, fill=(*TEXT, fa))
        d.text((548, 152), "Generated Octodex animation lab", font=FONT_SMALL, fill=(*GREEN, fa))


def paste_sprite(img: Image.Image, frames: List[Image.Image], frame_idx: int, x: float, y: float, scale: float, alpha=255, bob=0.0):
    fr = frames[frame_idx % len(frames)]
    sw, sh = max(1, int(fr.width * scale)), max(1, int(fr.height * scale))
    spr = fr.resize((sw, sh), Image.Resampling.LANCZOS)
    if alpha < 255:
        a = spr.getchannel("A").point(lambda p: int(p * alpha / 255))
        spr.putalpha(a)
    # Shadow
    shadow = Image.new("RGBA", (sw, max(10, int(sh * .12))), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    sd.ellipse((sw * .18, 0, sw * .82, shadow.height * .72), fill=(0, 0, 0, int(80 * alpha / 255)))
    shadow = shadow.filter(ImageFilter.GaussianBlur(12))
    img.alpha_composite(shadow, (int(x - sw / 2), int(y - shadow.height * .2)))
    img.alpha_composite(spr, (int(x - sw / 2), int(y - sh + bob)))


def draw_characters(img: Image.Image, t: float, f: int):
    # Parade walkers
    for name, x0, y, sc, start in lineup:
        p = pulse(t, start, start + 4.0)
        x = x0 + p * (W + 1200)
        if -250 < x < W + 250 and t < 9.7:
            speed_frame = int((t * 11 + start * 3)) % 8
            paste_sprite(img, characters[name], speed_frame, x, y + math.sin(t * 7 + start) * 5, sc, alpha=255)

    # Mona center action, more present during portal sequence and final.
    mona_alpha = int(255 * pulse(t, 3.8, 5.2))
    if t > 10.8:
        mona_alpha = 255
    if mona_alpha:
        mona_x = 610 + 28 * math.sin(t * .8)
        mona_y = 730 + 7 * math.sin(t * 5.5)
        paste_sprite(img, characters["mona"], int(t * 10), mona_x, mona_y, .58, alpha=mona_alpha)
        # laptop-to-portal data ribbon: particles, not a projectile/weapon shot, more like commits being pushed
        if 5.0 < t < 9.8:
            d = ImageDraw.Draw(img, "RGBA")
            q = pulse(t, 5.0, 6.5) * (1 - .3 * pulse(t, 8.8, 10.2))
            for i in range(60):
                u = (i / 59 + t * .22) % 1
                sx, sy = mona_x + 135, mona_y - 305
                ex, ey = 1285, 470
                # Bezier arc
                cx, cy = 945, 255 + 38 * math.sin(t * 2 + i)
                x = (1-u)**2 * sx + 2*(1-u)*u*cx + u**2 * ex
                y = (1-u)**2 * sy + 2*(1-u)*u*cy + u**2 * ey
                size = 3 + 3 * math.sin(i + t * 5) ** 2
                col = [GREEN, CYAN, PURPLE][i % 3]
                a = int(150 * q * (0.25 + 0.75 * math.sin(u * math.pi)))
                d.rounded_rectangle((x-size, y-size, x+size, y+size), radius=2, fill=(*col, a))

    # Final hero lineup, fixed and crisp.
    final = pulse(t, 10.0, 12.2)
    if final > 0:
        names = ["robot", "security", "liberty", "jetpack", "coder", "lab", "python", "obiwan", "dino"]
        for i, name in enumerate(names):
            x = 260 + i * 172
            y = 920 - 40 * math.sin((i / max(1, len(names)-1)) * math.pi)
            sc = .27 + .04 * math.sin(i)
            alpha = int(255 * final)
            paste_sprite(img, characters[name], int(t * 9 + i), x, y, sc, alpha=alpha)


def draw_hud(img: Image.Image, t: float):
    d = ImageDraw.Draw(img, "RGBA")
    # Small floating GitHub UI cards
    if 2.5 < t < 9.5:
        a = int(180 * pulse(t, 2.5, 3.5) * (1 - .5 * pulse(t, 8.7, 10.0)))
        cards = [
            (1180, 780, "pull request opened", "+128 animated frames", GREEN),
            (135, 420, "workflow: render", "anime-inspired motion", CYAN),
            (1420, 260, "branch: octodex/rift", "11 mascots online", PURPLE),
        ]
        for idx, (x, y, title, body, col) in enumerate(cards):
            yy = y + 10 * math.sin(t * 1.4 + idx)
            d.rounded_rectangle((x, yy, x + 340, yy + 98), radius=16, fill=(13, 17, 23, a), outline=(*col, int(a * .9)), width=2)
            d.text((x + 22, yy + 18), title, font=FONT_SMALL, fill=(*TEXT, a))
            d.text((x + 22, yy + 54), body, font=FONT_MONO, fill=(*col, a))


def render_frame(i: int) -> Image.Image:
    t = i / FPS
    img = gradient_bg(t)
    draw_background(img, t)
    draw_portal(img, t)
    draw_characters(img, t, i)
    draw_hud(img, t)
    draw_title(img, t)
    # Vignette
    vig = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vig, "RGBA")
    for k in range(12):
        a = int(7 + k * 5)
        vd.rectangle((k * 8, k * 8, W - k * 8, H - k * 8), outline=(0, 0, 0, a), width=12)
    img.alpha_composite(vig)
    return img.convert("RGB")


def main():
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-vcodec", "rawvideo",
        "-s", f"{W}x{H}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-an",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "medium",
        "-movflags", "+faststart",
        str(OUT),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for i in range(N):
        frame = render_frame(i)
        proc.stdin.write(frame.tobytes())
        if i % 30 == 0:
            print(f"frame {i}/{N}", flush=True)
    proc.stdin.close()
    proc.wait()
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)
    print(OUT)

if __name__ == "__main__":
    main()
