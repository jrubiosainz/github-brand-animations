#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from collections import deque
import json, shutil, subprocess
import numpy as np
from PIL import Image, ImageOps, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'work' / 'new_octodex_raw'
OUT = ROOT / 'work' / 'new_octodex_processed'
ASSETS = ROOT / 'assets' / 'spritesheets'
CONTACTS = ROOT / 'previews' / 'contact-sheets'
VIDEOS = ROOT / 'previews' / 'videos'
FRAMES = ROOT / 'previews' / 'frames' / 'octodex_web8_2026_05_18_v2'
for p in (OUT, ASSETS, CONTACTS, VIDEOS, FRAMES):
    p.mkdir(parents=True, exist_ok=True)

CHARS = [
    ('bombacat', 'Bombacat'),
    ('universetocat', 'Universetocat'),
    ('sponsortocat', 'Sponsortocat'),
    ('manufacturetocat', 'Manufacturetocat'),
    ('fintechtocat', 'Fintechtocat'),
    ('brennatocat', 'Brennatocat'),
    ('sentrytocat', 'Sentrytocat'),
    ('umbrellatocat', 'Umbrellatocat'),
]
COLS, ROWS = 4, 2

# Some generated sheets may face left even if prompted right-facing.
# Normalize those so preview motion matches the character gaze.
RAW_FACES_LEFT = {'umbrellatocat'}

def font(size=24, bold=False):
    candidates = [
        '/System/Library/Fonts/Supplemental/Arial Bold.ttf' if bold else '/System/Library/Fonts/Supplemental/Arial.ttf',
        '/System/Library/Fonts/Supplemental/Helvetica.ttf',
        '/System/Library/Fonts/SFNS.ttf',
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

FONT = font(24, True)
SMALL = font(17, False)


def keep_components(img: Image.Image, min_area: int = 900) -> Image.Image:
    img = img.convert('RGBA')
    arr = np.array(img)
    alpha = arr[..., 3] > 10
    h, w = alpha.shape
    seen = np.zeros((h, w), dtype=bool)
    comps = []
    for yy in range(h):
        xs = np.where(alpha[yy] & ~seen[yy])[0]
        for sx in xs:
            if seen[yy, sx] or not alpha[yy, sx]:
                continue
            q = deque([(yy, int(sx))])
            pts = []
            seen[yy, sx] = True
            while q:
                y, x = q.popleft(); pts.append((y, x))
                for ny, nx in ((y-1,x), (y+1,x), (y,x-1), (y,x+1)):
                    if 0 <= ny < h and 0 <= nx < w and alpha[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; q.append((ny, nx))
            ys, xs2 = zip(*pts)
            comps.append({'pts': pts, 'area': len(pts), 'bbox': (min(xs2), min(ys), max(xs2)+1, max(ys)+1)})
    if not comps:
        return img
    largest = max(c['area'] for c in comps)
    keep = np.zeros((h, w), dtype=bool)
    for c in comps:
        x0, y0, x1, y1 = c['bbox']
        bw, bh = x1 - x0, y1 - y0
        # Keep main body and substantial detached props (balloon, umbrella, tools),
        # but drop thin/small generation slivers between frames.
        substantial = c['area'] >= max(min_area, int(largest * 0.025)) and bw >= 20 and bh >= 20
        if c['area'] == largest or substantial:
            yy, xx = zip(*c['pts']); keep[yy, xx] = True
    arr[..., 3] = np.where(keep, arr[..., 3], 0)
    return Image.fromarray(arr.astype(np.uint8), 'RGBA')


def remove_bg(cell: Image.Image) -> Image.Image:
    cell = cell.convert('RGBA')
    arr = np.array(cell)
    rgb = arr[..., :3].astype(np.int16)
    h, w = rgb.shape[:2]
    e = max(12, min(h, w) // 20)
    samples = np.concatenate([
        rgb[:e, :].reshape(-1, 3), rgb[h-e:, :].reshape(-1, 3),
        rgb[:, :e].reshape(-1, 3), rgb[:, w-e:].reshape(-1, 3),
    ])
    bg = np.median(samples, axis=0)
    dist = np.sqrt(((rgb - bg) ** 2).sum(axis=2))
    mask = dist < 42
    bgmask = np.zeros((h, w), dtype=bool)
    q = deque()
    for x in range(w):
        if mask[0, x]: q.append((0, x))
        if mask[h-1, x]: q.append((h-1, x))
    for y in range(h):
        if mask[y, 0]: q.append((y, 0))
        if mask[y, w-1]: q.append((y, w-1))
    while q:
        y, x = q.popleft()
        if bgmask[y, x] or not mask[y, x]: continue
        bgmask[y, x] = True
        if y > 0: q.append((y-1, x))
        if y < h - 1: q.append((y+1, x))
        if x > 0: q.append((y, x-1))
        if x < w - 1: q.append((y, x+1))
    # Eat antialias/background fringe but do not cut interior gray costume pieces.
    m = bgmask.copy()
    for _ in range(2):
        n = m.copy()
        n[:-1, :] |= m[1:, :]; n[1:, :] |= m[:-1, :]
        n[:, :-1] |= m[:, 1:]; n[:, 1:] |= m[:, :-1]
        m = n & (dist < 76)
    arr[..., 3] = np.where(m, 0, arr[..., 3])
    return keep_components(Image.fromarray(arr.astype(np.uint8), 'RGBA'))


def process_char(name: str):
    raw_path = RAW / f'{name}_walk_raw.png'
    raw = Image.open(raw_path).convert('RGBA')
    W, H = raw.size
    cw, ch = W // COLS, H // ROWS
    sprites = []
    for idx in range(COLS * ROWS):
        cell = raw.crop(((idx % COLS) * cw, (idx // COLS) * ch, (idx % COLS + 1) * cw, (idx // COLS + 1) * ch))
        clean = remove_bg(cell)
        bbox = clean.getbbox()
        if not bbox:
            print('WARN empty frame', name, idx)
            continue
        sprites.append((idx, clean.crop(bbox)))
    if len(sprites) != 8:
        print('WARN', name, 'frames', len(sprites))
    maxw = max(s.width for _, s in sprites)
    maxh = max(s.height for _, s in sprites)
    fw = max(512, maxw + 120)
    fh = max(640, maxh + 120)
    rights = []
    cdir = OUT / f'{name}_web8_v2'
    cdir.mkdir(parents=True, exist_ok=True)
    for p in cdir.glob('*.png'):
        p.unlink()
    for idx, spr in sprites:
        canvas = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
        px = (fw - spr.width) // 2
        py = fh - spr.height - 46
        canvas.alpha_composite(spr, (px, py))
        rights.append(canvas)
    if name in RAW_FACES_LEFT:
        lefts = rights
        rights = [ImageOps.mirror(f) for f in lefts]
    else:
        lefts = [ImageOps.mirror(f) for f in rights]
    for i, f in enumerate(rights): f.save(cdir / f'right_{i:02d}.png')
    for i, f in enumerate(lefts): f.save(cdir / f'left_{i:02d}.png')
    sheet = Image.new('RGBA', (fw * 8, fh * 2), (0, 0, 0, 0))
    for i, f in enumerate(rights): sheet.alpha_composite(f, (i * fw, 0))
    for i, f in enumerate(lefts): sheet.alpha_composite(f, (i * fw, fh))
    sheet_path = OUT / f'{name}_right_left_spriteforge_web8_v2.png'
    sheet.save(sheet_path)
    shutil.copy2(sheet_path, ASSETS / sheet_path.name)

    check = Image.new('RGB', (fw * 4, fh * 2), (232, 232, 232))
    d = ImageDraw.Draw(check)
    for yy in range(0, fh * 2, 32):
        for xx in range(0, fw * 4, 32):
            if (xx // 32 + yy // 32) % 2:
                d.rectangle((xx, yy, xx + 31, yy + 31), fill=(206, 206, 206))
    contact = check.convert('RGBA')
    for i, f in enumerate(rights):
        contact.alpha_composite(f, ((i % 4) * fw, (i // 4) * fh))
    contact_path = OUT / f'{name}_contact_web8_v2.jpg'
    contact.convert('RGB').save(contact_path, quality=92)
    shutil.copy2(contact_path, CONTACTS / contact_path.name)
    print(name, 'canvas', fw, fh, 'sprite sizes', [(i, s.size) for i, s in sprites])
    return rights, lefts, fw, fh


def panel_bg(w, h, label, accent):
    im = Image.new('RGB', (w, h), (17, 21, 31))
    d = ImageDraw.Draw(im, 'RGBA')
    d.rectangle((0, int(h * .76), w, h), fill=(42, 51, 60, 255))
    for x in range(-h, w, 42):
        d.line((x, int(h * .76), x + int(h * .25), h), fill=(56, 66, 78, 180), width=1)
    d.rounded_rectangle((16, 14, min(w - 16, 32 + len(label) * 12), 48), radius=10, fill=(7, 10, 18, 230), outline=accent + (185,), width=1)
    d.text((28, 21), label, font=SMALL, fill=(242, 246, 252))
    return im.convert('RGBA')

frames = {name: process_char(name) for name, _ in CHARS}

# 4x2 motion preview.
for p in FRAMES.glob('*.png'):
    p.unlink()
W, H = 1920, 1080
panelW, panelH = W // 4, H // 2
positions = [(i * panelW, j * panelH) for j in range(2) for i in range(4)]
colors = [(255,171,112), (163,113,247), (63,185,80), (88,166,255), (121,192,255), (255,123,206), (248,81,73), (210,168,255)]
N = 96
for n in range(N):
    canvas = Image.new('RGB', (W, H), (5, 9, 18)).convert('RGBA')
    bgd = ImageDraw.Draw(canvas, 'RGBA')
    for gy in range(0, H, 34):
        for gx in range(0, W, 34):
            if ((gx // 34 + gy // 34 + n // 6) % 7) == 0:
                bgd.rounded_rectangle((gx, gy, gx + 16, gy + 16), radius=4, fill=(35, 134, 54, 35))
    for idx, (name, label) in enumerate(CHARS):
        x0, y0 = positions[idx]
        panel = panel_bg(panelW, panelH, label, colors[idx])
        rights, lefts, fw, fh = frames[name]
        if n < N // 2:
            f = rights[n % len(rights)]
            x = 42 + int(n * (panelW - 180) / (N // 2 - 1))
        else:
            f = lefts[n % len(lefts)]
            x = panelW - 122 - int((n - N // 2) * (panelW - 180) / (N // 2 - 1))
        scale = min(0.48, 300 / f.height, 310 / f.width)
        spr = f.resize((int(f.width * scale), int(f.height * scale)), Image.Resampling.LANCZOS)
        y = int(panelH * .78) - spr.height
        panel.alpha_composite(spr, (x, y))
        canvas.alpha_composite(panel, (x0, y0))
    d = ImageDraw.Draw(canvas, 'RGBA')
    d.rounded_rectangle((38, 28, 562, 88), radius=16, fill=(2, 6, 14, 190), outline=(63, 185, 80, 140), width=1)
    d.text((62, 42), 'Octodex web 8 — walk cycles v2', font=FONT, fill=(240, 246, 252))
    canvas.convert('RGB').save(FRAMES / f'{n:04d}.png')

video = VIDEOS / 'octodex_web8_2026_05_18_walk_cycles_v2.mp4'
subprocess.run([
    'ffmpeg', '-y', '-framerate', '12', '-i', str(FRAMES / '%04d.png'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(video)
], check=True)

# Combined QA contact sheet.
contactW, contactH = 512 * 4, 660 * 2
mont = Image.new('RGB', (contactW, contactH), (20, 20, 25))
d = ImageDraw.Draw(mont)
for idx, (name, label) in enumerate(CHARS):
    im = Image.open(CONTACTS / f'{name}_contact_web8_v2.jpg').convert('RGB').resize((512, 620), Image.Resampling.LANCZOS)
    x = (idx % 4) * 512
    y = (idx // 4) * 660 + 40
    mont.paste(im, (x, y))
    d.text((x + 18, y - 28), label, font=FONT, fill=(255, 255, 255))
combined_contact = CONTACTS / 'octodex_web8_2026_05_18_contacts_v2.jpg'
mont.save(combined_contact, quality=90)
print('VIDEO', video)
print('CONTACT', combined_contact)
