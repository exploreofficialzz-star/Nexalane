#!/usr/bin/env python3
"""Generates the NEXALANE app icon from the cartoon runner (assets/icon/*.png).

The runner is rendered from a high-resolution build of the same procedural model (tools/assetgen/toon.py, tessellation 1.0
instead of the mobile budget), in a mid-stride pose of toon_gait.gd, then composed on a sunset city-track scene.
Writes: nexalane_icon_master.png (1254), _1024, _512, _192, nexalane_adaptive_fg_432.png (runner only, RGBA, inside the 66 %
safe zone) and nexalane_adaptive_bg_432.png (scene only).

    python tools/make_icon.py            (about a minute; the software rasteriser is not fast)
"""
from __future__ import annotations
import math
import random
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from assetgen import toon, toon_preview as tp   # noqa: E402
import preview_toon_poses as pp                  # noqa: E402

OUT = ROOT / 'assets' / 'icon'
HOODIE = (85, 214, 255)                          # sRGB: the default runner colour (#55d6ff)


def srgb_to_lin(rgb):
    return tuple(((c / 255.0 + 0.055) / 1.055) ** 2.4 if c / 255.0 > 0.04045 else c / 255.0 / 12.92 for c in rgb)


# ------------------------------------------------------------------------------------------------ the runner
def render_runner(size=(1000, 1160), ssaa=2):
    toon.Q_SEG = 1.0; toon.Q_STEP = 1.0; toon.Q_ELLIP = 1.0                      # hero tessellation
    tmp = Path('/tmp/nexalane_hero_runner.glb')
    toon.build_runner().write(str(tmp))
    sk = tp.load(str(tmp))
    gd = pp.load_gait()
    spd = 25.0
    u, over = gd['intensity'](spd), gd['overdrive'](spd)
    cad = gd['cadence'](u, over)
    ph = 0.585                                                                    # right leg driving up, left foot pushing off
    c = gd['run_pose'](ph, u, over, 0.16, 0.35, 0.0)
    y = gd['run_pelvis_y'](ph, u, over, 0.16, 0.35, cad) + 0.05
    wr, wp = pp.pose_world(c, y)
    prims = tp.posed(sk, wr, wp)
    return tp.render(prims, size=size, yaw=24, pitch=5, center=(0.0, 0.98, 0.0), fit=1.12, ssaa=ssaa, cam_dist=6.0, bg=None,
                     tint=srgb_to_lin(HOODIE), exposure=1.08)


# ------------------------------------------------------------------------------------------------ the scene
def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


def gradient(w, h, stops):
    arr = np.zeros((h, w, 3), float)
    ys = np.linspace(0, 1, h)
    for i in range(h):
        t = ys[i]
        for k in range(len(stops) - 1):
            if stops[k][0] <= t <= stops[k + 1][0]:
                f = (t - stops[k][0]) / max(stops[k + 1][0] - stops[k][0], 1e-6)
                arr[i] = lerp(stops[k][1], stops[k + 1][1], f)
                break
    return Image.fromarray(arr.astype(np.uint8), 'RGB')


def glow(img, center, radius, color, strength=1.0):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2) / radius
    a = np.clip(1.0 - d, 0, 1) ** 2 * strength
    layer = Image.new('RGB', img.size, color)
    mask = Image.fromarray((a * 255).astype(np.uint8), 'L')
    return Image.composite(layer, img, mask)


def scene(S=1024, seed=7):
    rnd = random.Random(seed)
    horizon = int(S * 0.58)
    img = gradient(S, S, [(0.0, (30, 18, 96)), (0.30, (92, 36, 160)), (0.50, (236, 84, 140)), (0.58, (255, 168, 76)), (0.585, (42, 26, 96)), (1.0, (22, 14, 66))])
    img = glow(img, (S * 0.5, horizon - S * 0.02), S * 0.62, (255, 196, 96), 0.95)
    d = ImageDraw.Draw(img, 'RGBA')
    # sun disc
    r = int(S * 0.20)
    d.ellipse((S // 2 - r, horizon - int(r * 1.5), S // 2 + r, horizon + int(r * 0.5)), fill=(255, 226, 150, 120))
    # skyline: three depth layers
    for layer, (col, hmax, wmin, wmax) in enumerate([((74, 34, 124), 0.20, 0.03, 0.07), ((44, 22, 92), 0.14, 0.03, 0.06), ((26, 14, 66), 0.09, 0.02, 0.05)]):
        x = -20
        while x < S + 20:
            bw = int(S * rnd.uniform(wmin, wmax)); bh = int(S * rnd.uniform(0.35, 1.0) * hmax)
            d.rectangle((x, horizon - bh, x + bw, horizon + 4), fill=col + (255,))
            if layer >= 1:
                for wy in range(horizon - bh + 8, horizon - 4, 14):
                    for wx in range(x + 5, x + bw - 6, 11):
                        if rnd.random() < 0.28:
                            d.rectangle((wx, wy, wx + 4, wy + 6), fill=rnd.choice([(255, 214, 120, 235), (120, 226, 255, 235), (255, 120, 190, 235)]))
            x += bw + rnd.randint(0, 6)
    # track
    vp = (S // 2, horizon - 2)
    d.polygon([(S * 0.44, horizon), (S * 0.56, horizon), (S * 1.30, S), (-S * 0.30, S)], fill=(38, 24, 92, 255))
    for k, col in ((-1.0, (60, 232, 255)), (1.0, (255, 80, 190))):                                # neon rails
        for wd, al in ((26, 40), (14, 90), (5, 255)):
            d.line([(vp[0] + k * S * 0.06, horizon), (vp[0] + k * S * 0.86, S)], fill=col + (al,), width=wd)
    for k in (-0.34, 0.0, 0.34):                                                                   # lane dashes
        for i in range(7):
            t0 = (i / 7.0) ** 1.7; t1 = ((i + 0.5) / 7.0) ** 1.7
            x0 = vp[0] + k * S * 1.1 * t0; x1 = vp[0] + k * S * 1.1 * t1
            y0 = horizon + (S - horizon) * t0; y1 = horizon + (S - horizon) * t1
            d.line([(x0, y0), (x1, y1)], fill=(255, 255, 255, 190), width=max(2, int(2 + 12 * t1)))
    # light streaks from the vanishing point
    for i in range(26):
        ang = rnd.uniform(math.radians(205), math.radians(335)); ln = S * rnd.uniform(0.25, 0.7)
        x1 = vp[0] + math.cos(ang) * ln; y1 = vp[1] + math.sin(ang) * ln * 0.9
        d.line([vp, (x1, y1)], fill=(255, 236, 190, rnd.randint(14, 40)), width=rnd.randint(2, 6))
    return img


def coin(d, cx, cy, r, tilt=1.0):
    rx, ry = r * tilt, r
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(184, 112, 14, 255))
    d.ellipse((cx - rx * 0.92, cy - ry * 0.92, cx + rx * 0.92, cy + ry * 0.92), fill=(255, 205, 52, 255))
    d.ellipse((cx - rx * 0.66, cy - ry * 0.66, cx + rx * 0.66, cy + ry * 0.66), outline=(214, 140, 20, 255), width=max(2, int(r * 0.09)))
    d.arc((cx - rx * 0.80, cy - ry * 0.80, cx + rx * 0.80, cy + ry * 0.80), 200, 280, fill=(255, 246, 190, 255), width=max(2, int(r * 0.10)))


def sparkle(d, cx, cy, r, col=(255, 255, 255, 240)):
    d.polygon([(cx, cy - r), (cx + r * 0.18, cy - r * 0.18), (cx + r, cy), (cx + r * 0.18, cy + r * 0.18), (cx, cy + r),
               (cx - r * 0.18, cy + r * 0.18), (cx - r, cy), (cx - r * 0.18, cy - r * 0.18)], fill=col)


def compose(runner, S=1024, with_scene=True, scale=1.0, dy=0.0):
    base = scene(S) if with_scene else Image.new('RGBA', (S, S), (0, 0, 0, 0))
    base = base.convert('RGBA')
    k = S / 1024.0
    # coins and sparkles behind the runner
    dd = ImageDraw.Draw(base, 'RGBA')
    if with_scene:
        for (x, y, r, t) in ((150, 640, 46, 0.78), (232, 520, 34, 0.5), (868, 560, 50, 0.85), (806, 700, 36, 0.55), (120, 420, 26, 0.62), (902, 380, 28, 0.7)):
            coin(dd, x * k, y * k, r * k, t)
        for (x, y, r) in ((180, 250, 30), (840, 220, 38), (300, 130, 20), (720, 120, 24), (500, 80, 18)):
            sparkle(dd, x * k, y * k, r * k)
    # runner: fit into the canvas, feet near the lower quarter
    rw, rh = runner.size
    target_h = int(S * 0.92 * scale)
    r2 = runner.resize((int(rw * target_h / rh), target_h), Image.LANCZOS)
    px = (S - r2.width) // 2
    py = int(S * 0.055 + dy * S)
    # shadow on the track
    sh = Image.new('RGBA', (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((S * 0.28, py + target_h - S * 0.07, S * 0.72, py + target_h + S * 0.035), fill=(8, 4, 30, 170))
    base = Image.alpha_composite(base, sh.filter(ImageFilter.GaussianBlur(S * 0.018)))
    # warm halo so the runner separates from the busy background
    alpha = Image.new('L', (S, S), 0); alpha.paste(r2.split()[3], (px, py))
    halo = Image.new('RGBA', (S, S), (255, 232, 170, 0)); halo.putalpha(alpha.filter(ImageFilter.GaussianBlur(S * 0.022)).point(lambda v: min(255, int(v * 0.85))))
    base = Image.alpha_composite(base, halo)
    layer = Image.new('RGBA', (S, S), (0, 0, 0, 0)); layer.paste(r2, (px, py), r2)
    base = Image.alpha_composite(base, layer)
    # foreground coins in front of the track
    if with_scene:
        dd = ImageDraw.Draw(base, 'RGBA')
        for (x, y, r, t) in ((250, 900, 40, 0.7), (790, 880, 44, 0.75)):
            coin(dd, x * k, y * k, r * k, t)
    return base


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    runner = render_runner()
    runner.save('/tmp/nexalane_runner_hero.png')
    full = compose(runner, 1254).convert('RGB')
    full.save(OUT / 'nexalane_icon_master.png', optimize=True)
    full.resize((1024, 1024), Image.LANCZOS).save(OUT / 'nexalane_icon_1024.png', optimize=True)
    full.resize((512, 512), Image.LANCZOS).save(OUT / 'nexalane_icon_512.png', optimize=True)
    full.resize((192, 192), Image.LANCZOS).save(OUT / 'nexalane_icon_192.png', optimize=True)
    # adaptive icon: background = scene only, foreground = runner only inside the 66 % safe zone
    scene(432).convert('RGB').save(OUT / 'nexalane_adaptive_bg_432.png', optimize=True)
    fg = compose(runner, 432, with_scene=False, scale=0.64, dy=0.17)
    fg.save(OUT / 'nexalane_adaptive_fg_432.png', optimize=True)
    print('icons written to', OUT)


if __name__ == '__main__':
    main()
