"""Environment textures: PBR road sets, facades, concrete, brushed metal, holo grid, skyline silhouettes."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from .noise import fbm, blur, smoothstep, to_srgb, to_u8, normal_map

# ------------------------------------------------------------------ road (18 m x 9 m tile)
ROAD_W, ROAD_H = 1024, 512          # px  -> 56.9 px / metre
ROAD_M_X, ROAD_M_Z = 18.0, 9.0


def _poly_noise_mask(h, w, seed, n, length=(60, 170), width=1.3, bounds=None):
    """Random-walk cracks, wrapped vertically so the tile stays seamless."""
    rng = np.random.default_rng(seed)
    S = 2
    img = Image.new('L', (w * S, h * S), 0)
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x = rng.uniform(*(bounds or (0, w))); y = rng.uniform(0, h); a = rng.uniform(0, 2 * math.pi)
        steps = int(rng.integers(*length))
        pts = [(x, y)]
        for _s in range(steps):
            a += rng.normal(0, 0.35); L = rng.uniform(2.0, 6.0)
            x += math.cos(a) * L; y += math.sin(a) * L; pts.append((x, y))
        for off in (-h, 0, h):
            d.line([(px * S, (py + off) * S) for px, py in pts], fill=255, width=int(width * S))
    img = img.resize((w, h), Image.LANCZOS)
    return np.asarray(img, float) / 255.0


def _rect_mask(h, w, rects):
    img = Image.new('L', (w, h), 0); d = ImageDraw.Draw(img)
    for (x0, y0, x1, y1) in rects:
        for off in (-h, 0, h):
            d.rectangle([x0, y0 + off, x1, y1 + off], fill=255)
    return np.asarray(img, float) / 255.0


def road_set(wet: bool, seed=11):
    H, W = ROAD_H, ROAD_W
    rng = np.random.default_rng(seed + (100 if wet else 0))
    xs = (np.arange(W) + 0.5) / W * ROAD_M_X - ROAD_M_X / 2
    zs = (np.arange(H) + 0.5) / H * ROAD_M_Z
    X, Z = np.meshgrid(xs, zs)
    ax = np.abs(X)
    road = (ax < 5.75).astype(float)
    curb = ((ax >= 5.75) & (ax < 6.05)).astype(float)
    side = (ax >= 6.05).astype(float)

    grain = rng.random((H, W)); f1 = fbm((H, W), 1.1, seed + 1); f2 = fbm((H, W), 2.6, seed + 2); f3 = fbm((H, W), 3.6, seed + 3)
    stones = (rng.random((H, W)) > 0.9965).astype(float); stones = blur(stones, 0.7) * 6.0
    asph = (0.052 if wet else 0.078) + 0.030 * (f2 - 0.5) + 0.030 * (grain - 0.5) + 0.020 * (f1 - 0.5) + 0.035 * np.clip(stones, 0, 1) * (0.5 + f1)
    rough = np.full((H, W), 0.86 if not wet else 0.50) + 0.08 * (f3 - 0.5)
    height = 0.010 * grain + 0.020 * f1 + 0.020 * f2

    # tyre wear bands in each runner lane (lane centres 0, +-3.2 m)
    wear = np.zeros((H, W))
    for cx in (-3.2, 0.0, 3.2):
        for dx in (-0.78, 0.78):
            wear += np.exp(-((X - (cx + dx)) ** 2) / (2 * 0.26 ** 2))
    wear = np.clip(wear, 0, 1) * (0.55 + 0.45 * f3) * road
    asph *= (1.0 - 0.14 * wear); rough -= (0.16 if not wet else 0.10) * wear

    # asphalt patches + cracks
    rects = []
    for _ in range(9):
        cx = rng.uniform(80, W - 80); cy = rng.uniform(0, H)
        rects.append((cx - rng.uniform(50, 130), cy - rng.uniform(30, 90), cx + rng.uniform(50, 130), cy + rng.uniform(30, 90)))
    patch = blur(_rect_mask(H, W, rects), 0.8) * road
    asph *= 1.0 + patch * rng.choice([-0.22, 0.28], size=1)[0] * 0.7; height -= 0.012 * patch
    cracks = _poly_noise_mask(H, W, seed + 5, 7, bounds=(60, W - 60), width=1.2) * (0.6 + 0.4 * road)
    crk = blur(cracks, 0.6)
    asph *= 1.0 - 0.55 * crk; height -= 0.07 * crk

    alb = np.stack([asph * 1.0, asph * 1.0, asph * 1.04], -1)

    # sidewalk pavers (0.75 m) + curb
    gx = (X + 9.0) / 0.75; gz = Z / 0.75 * (H / (ROAD_M_Z / 0.75)) / (H / (ROAD_M_Z / 0.75))
    gz = Z / (ROAD_M_Z / 12.0)                       # exactly 12 pavers vertically => seamless
    fx = gx - np.floor(gx); fz = gz - np.floor(gz)
    grout = ((fx < 0.045) | (fx > 0.955) | (fz < 0.045) | (fz > 0.955)).astype(float)
    grout = blur(grout, 0.7)
    tone_tab = rng.random(4096)
    tone = tone_tab[((np.floor(gx).astype(int) * 131 + np.floor(gz).astype(int) * 71) % 4096)]
    pav = 0.20 + 0.055 * (tone - 0.5) + 0.03 * (f2 - 0.5) + 0.02 * (grain - 0.5)
    pav = pav * (0.55 if wet else 1.0) * (1.0 - 0.45 * grout)
    curb_c = (0.28 if not wet else 0.17) + 0.03 * (f2 - 0.5)
    for c in range(3):
        alb[..., c] = alb[..., c] * road + np.where(side > 0, pav, 0) + np.where(curb > 0, curb_c, 0)
    rough = rough * road + (0.78 if not wet else 0.42) * (side + curb) * (1 - 0.1 * grout) + 0.05 * (f3 - 0.5) * (side + curb)
    height = height * road + side * (0.012 * tone + 0.012 * grain - 0.05 * grout) + curb * 0.10
    # soften the curb ramp so the normal map reads as a step
    height = blur(height, 0.6)

    # lane paint: dashed lane dividers at +-1.6 m, solid edge lines at +-5.45 m
    paint = np.zeros((H, W))
    period = ROAD_M_Z / 2.0
    dash = ((Z % period) < period * 0.54).astype(float)
    for lx in (-1.6, 1.6):
        paint += (np.abs(X - lx) < 0.075).astype(float) * dash
    for lx in (-5.45, 5.45):
        paint += (np.abs(X - lx) < 0.09).astype(float)
    paint = np.clip(paint, 0, 1)
    chip = smoothstep(0.40, 0.62, fbm((H, W), 2.0, seed + 8))
    paint = blur(paint, 0.6) * (0.55 + 0.45 * chip)
    pcol = 0.55 if not wet else 0.42
    for c in range(3):
        alb[..., c] = alb[..., c] * (1 - paint) + pcol * paint * (0.97 if c == 2 else 1.0)
    rough = rough * (1 - paint) + (0.58 if not wet else 0.30) * paint
    height += 0.006 * paint

    # manhole covers
    for (mx, mz) in ((3.2, 2.0), (-3.2, 6.6)):
        rr = np.sqrt((X - mx) ** 2 + (Z - mz) ** 2)
        cover = smoothstep(0.46, 0.43, rr)
        ring = smoothstep(0.50, 0.47, rr) - cover
        pat = 0.5 + 0.5 * np.cos(rr * 2 * math.pi / 0.07)
        for c in range(3): alb[..., c] = alb[..., c] * (1 - cover - ring) + (0.05 + 0.02 * pat) * cover + 0.11 * ring
        rough = rough * (1 - cover) + 0.45 * cover
        height += -0.03 * ring + 0.015 * cover * pat

    # oil stains (dry) / puddles (wet)
    pm = fbm((H, W), 2.4, seed + 9)
    if wet:
        puddle = smoothstep(0.615, 0.690, pm) * road
        puddle = np.clip(puddle + 0.45 * smoothstep(0.66, 0.74, fbm((H, W), 2.0, seed + 10)) * (side + curb), 0, 1)
        for c in range(3): alb[..., c] *= (1.0 - 0.42 * puddle)
        rough = rough * (1 - puddle) + 0.035 * puddle
        height = height * (1 - 0.92 * puddle)
    else:
        stain = smoothstep(0.60, 0.72, pm) * road
        for c in range(3): alb[..., c] *= (1.0 - 0.30 * stain)
        rough = rough * (1 - stain) + 0.62 * stain

    albedo = to_u8(to_srgb(alb))
    rgh = to_u8(np.clip(rough, 0.02, 1.0))
    nrm = normal_map(height, 55.0)
    out = dict(albedo=Image.fromarray(albedo), rough=Image.fromarray(rgh, 'L'), normal=Image.fromarray(nrm))

    if wet:  # neon reflections living inside the puddles: stretched streaks, orange left / cyan right
        streak = fbm((H, W), 1.6, seed + 12)
        streak = blur(streak, 9.0, 1.4)
        streak = smoothstep(0.50, 0.66, (streak - streak.min()) / (streak.max() - streak.min()))
        cx = np.clip((X + 6.0) / 12.0, 0, 1)
        orange = np.array([1.0, 0.36, 0.08]); cyan = np.array([0.10, 0.75, 1.0]); mag = np.array([1.0, 0.18, 0.62])
        col = (orange[None, None, :] * (1 - cx)[..., None] + cyan[None, None, :] * cx[..., None])
        mid = np.exp(-((cx - 0.5) ** 2) / 0.01)[..., None]
        col = col * (1 - 0.5 * mid) + mag * 0.5 * mid
        em = col * (streak * np.clip(puddle * 1.2, 0, 1) * 0.65)[..., None]
        out['emission'] = Image.fromarray(to_u8(to_srgb(em)))
    return out


# ------------------------------------------------------------------ small tileables
def concrete_tile(size=512, seed=21):
    rng = np.random.default_rng(seed)
    f1 = fbm((size, size), 1.4, seed); f2 = fbm((size, size), 3.0, seed + 1); g = rng.random((size, size))
    base = 0.30 + 0.07 * (f2 - 0.5) + 0.05 * (f1 - 0.5) + 0.03 * (g - 0.5)
    yy = np.arange(size)[:, None] * np.ones((1, size))
    xx = np.arange(size)[None, :] * np.ones((size, 1))
    seam = ((yy % 128) < 2) | ((xx % 256) < 2)
    base *= np.where(seam, 0.55, 1.0)
    ties = (((xx % 256) - 128) ** 2 + ((yy % 128) - 64) ** 2 < 12 ** 2)
    base *= np.where(ties, 0.7, 1.0)
    streak = blur(fbm((size, size), 2.4, seed + 3), 30, 2)
    base *= 0.85 + 0.3 * (streak - 0.5)
    rgb = np.stack([base, base * 1.02, base * 1.05], -1)
    return Image.fromarray(to_u8(to_srgb(rgb)))


def brushed_metal(size=512, seed=31):
    rng = np.random.default_rng(seed)
    n = blur(rng.random((size, size)), 0.6, 38) ; n = (n - n.min()) / (n.max() - n.min())
    f = fbm((size, size), 2.4, seed + 1)
    v = 0.34 + 0.22 * (n - 0.5) + 0.07 * (f - 0.5)
    rgb = np.stack([v * 0.98, v * 1.01, v * 1.06], -1)
    return Image.fromarray(to_u8(to_srgb(rgb)))


def holo_grid(size=512, seed=41):
    rng = np.random.default_rng(seed)
    img = np.zeros((size, size, 3))
    yy, xx = np.mgrid[0:size, 0:size]
    for step, w, col, a in ((64, 2, (0.10, 0.85, 1.0), 0.9), (16, 1, (0.10, 0.55, 0.9), 0.35)):
        ln = ((xx % step) < w) | ((yy % step) < w)
        img += ln[..., None] * np.array(col) * a
    scan = 0.5 + 0.5 * np.cos(yy * 2 * math.pi / 4.0)
    img *= (0.75 + 0.25 * scan)[..., None]
    # data glyph blocks
    blocks = rng.random((size // 16, size // 16)) > 0.93
    big = np.kron(blocks, np.ones((16, 16))) [:size, :size]
    img += big[..., None] * np.array((1.0, 0.45, 0.10)) * 0.55
    img = blur(img, 0.8) + img * 0.4
    img += 0.025 * np.array((0.0, 0.05, 0.12))
    return Image.fromarray(to_u8(to_srgb(np.clip(img, 0, 1))))


# ------------------------------------------------------------------ facades (4 bays x 8 floors, 40 px/m)
BAY, FLOOR, NB, NF = 128, 128, 4, 8
FW, FH = BAY * NB, FLOOR * NF


def _grime(shape, seed):
    g = blur(fbm(shape, 2.2, seed), 40, 1.5)
    return 0.80 + 0.35 * (g - g.min()) / (g.max() - g.min() + 1e-9)


def facade(kind: str, seed=51):
    rng = np.random.default_rng(seed)
    alb = np.zeros((FH, FW, 3)); emi = np.zeros((FH, FW, 3)); mr = np.zeros((FH, FW, 3))
    mr[..., 1] = 0.85  # roughness (G)
    yy, xx = np.mgrid[0:FH, 0:FW]
    grain = rng.random((FH, FW)); f1 = fbm((FH, FW), 2.0, seed)
    palette_warm = [(1.0, 0.78, 0.46), (1.0, 0.70, 0.36), (1.0, 0.86, 0.62), (1.0, 0.62, 0.28)]
    palette_cool = [(0.62, 0.86, 1.0), (0.80, 0.93, 1.0), (0.45, 0.80, 0.95)]
    img_a = Image.fromarray(np.zeros((FH, FW, 3), np.uint8)); d_a = None

    def fill(arr, x0, y0, x1, y1, col):
        arr[y0:y1, x0:x1] = col

    if kind == 'a':       # modern concrete + ribbon windows
        base = 0.32 + 0.05 * (f1 - 0.5) + 0.03 * (grain - 0.5)
        base = np.where((yy % FLOOR) < 3, base * 0.55, base); base = np.where((xx % BAY) < 2, base * 0.7, base)
        alb[:] = np.stack([base, base * 1.01, base * 1.04], -1)
        for fl in range(NF):
            for bay in range(NB):
                x0 = bay * BAY + 12; x1 = bay * BAY + BAY - 12; y0 = fl * FLOOR + 30; y1 = fl * FLOOR + 108
                fill(alb, x0 - 4, y0 - 4, x1 + 4, y1 + 4, (0.05, 0.055, 0.06)); fill(mr, x0 - 4, y0 - 4, x1 + 4, y1 + 4, (0, 0.35, 0.7))
                gh = y1 - y0
                grad = np.linspace(0.12, 0.035, gh)[:, None, None]
                alb[y0:y1, x0:x1] = grad * np.array((0.55, 0.85, 1.25)); mr[y0:y1, x0:x1] = (0, 0.12, 0.0)
                fill(alb, (x0 + x1) // 2 - 1, y0, (x0 + x1) // 2 + 1, y1, (0.04, 0.045, 0.05))
                if rng.random() < 0.34:
                    c = np.array(palette_warm[rng.integers(len(palette_warm))] if rng.random() < 0.75 else palette_cool[rng.integers(len(palette_cool))])
                    k = rng.uniform(0.45, 1.0)
                    for half in (0, 1):
                        xa = x0 + half * ((x1 - x0) // 2 + 1); xb = (x0 + (x1 - x0) // 2 - 1) if half == 0 else x1
                        if rng.random() < 0.9: emi[y0:y1, xa:xb] = c * k * (0.7 + 0.5 * np.linspace(1, 0.5, gh)[:, None, None])
    elif kind == 'b':     # glass curtain wall
        alb[:] = np.array((0.015, 0.035, 0.05)) + 0.01 * (f1[..., None] - 0.5)
        mr[..., 1] = 0.10; mr[..., 2] = 0.05
        for fl in range(NF):
            y = fl * FLOOR
            alb[y + 100:y + 128] = (0.045, 0.05, 0.055); mr[y + 100:y + 128] = (0, 0.5, 0.8)
        vm = (xx % 64) < 3
        alb[vm] = (0.05, 0.055, 0.06); mr[vm] = (0, 0.4, 0.8)
        sky = np.linspace(0.8, 0.25, FH)[:, None, None]
        alb += sky * np.array((0.015, 0.05, 0.085)) * (0.6 + 0.8 * f1[..., None])
        for fl in range(NF):
            for col in range(NB * 2):
                if rng.random() < 0.38:
                    c = np.array(palette_cool[rng.integers(len(palette_cool))] if rng.random() < 0.8 else palette_warm[rng.integers(len(palette_warm))])
                    x0 = col * 64 + 4; x1 = col * 64 + 61; y0 = fl * FLOOR + 6; y1 = fl * FLOOR + 98
                    emi[y0:y1, x0:x1] = c * rng.uniform(0.35, 0.9) * (0.75 + 0.35 * (1 - np.linspace(0, 1, y1 - y0))[:, None, None])
            if rng.random() < 0.18: emi[fl * FLOOR + 112:fl * FLOOR + 118, :] = np.array((0.15, 0.85, 1.0)) * 0.9
    elif kind == 'c':     # old brick
        brick_h, brick_w = 6, 14
        row = yy // brick_h; off = (row % 2) * (brick_w // 2)
        bx = (xx + off) % brick_w; by = yy % brick_h
        mortar = (bx < 1) | (by < 1)
        idb = ((xx + off) // brick_w + row * 37) % 251
        tab = rng.random(256)
        tone = tab[idb]
        brick = np.stack([0.24 + 0.08 * tone, 0.085 + 0.04 * tone, 0.065 + 0.03 * tone], -1) * (0.9 + 0.2 * grain[..., None])
        alb[:] = np.where(mortar[..., None], np.array((0.19, 0.17, 0.15)), brick)
        mr[..., 1] = 0.9
        for fl in range(NF):
            for bay in range(NB):
                wx0 = bay * BAY + 36; wx1 = bay * BAY + 92; wy0 = fl * FLOOR + 22; wy1 = fl * FLOOR + 108
                fill(alb, wx0 - 6, wy0 - 8, wx1 + 6, wy1 + 6, (0.30, 0.28, 0.25)); fill(mr, wx0 - 6, wy0 - 8, wx1 + 6, wy1 + 6, (0, 0.8, 0))
                alb[wy0:wy1, wx0:wx1] = np.linspace(0.07, 0.03, wy1 - wy0)[:, None, None] * np.array((0.8, 1.0, 1.2)); mr[wy0:wy1, wx0:wx1] = (0, 0.15, 0)
                fill(alb, (wx0 + wx1) // 2 - 1, wy0, (wx0 + wx1) // 2 + 1, wy1, (0.2, 0.18, 0.16))
                if rng.random() < 0.5:   # shutters
                    shc = np.array(((0.05, 0.22, 0.20), (0.18, 0.08, 0.05), (0.06, 0.10, 0.22)))[rng.integers(3)]
                    fill(alb, wx0 - 16, wy0 - 2, wx0 - 2, wy1 + 2, shc); fill(alb, wx1 + 2, wy0 - 2, wx1 + 16, wy1 + 2, shc)
                if rng.random() < 0.28:
                    c = np.array(palette_warm[rng.integers(len(palette_warm))]); emi[wy0:wy1, wx0:wx1] = c * rng.uniform(0.5, 1.0)
            if fl % 2 == 1:  # balcony slab + rail
                alb[fl * FLOOR + 112:fl * FLOOR + 120, :] = (0.26, 0.25, 0.23)
    else:                 # industrial corrugated cladding
        rib = 0.5 + 0.5 * np.cos(xx * 2 * math.pi / 8.0)
        col = np.where(((xx // 128 + (yy // 256)) % 2 == 0), 0.30, 0.24)
        v = (0.16 + 0.05 * rib) * (0.8 + 0.4 * f1) * (col / 0.27)
        alb[:] = np.stack([v * 0.95, v * 1.0, v * 0.97], -1)
        mr[..., 1] = 0.6 + 0.2 * rib; mr[..., 2] = 0.55
        for fl in range(NF):
            y0 = fl * FLOOR + 14; y1 = y0 + 22
            alb[y0:y1, 8:FW - 8] = (0.03, 0.035, 0.04); mr[y0:y1, 8:FW - 8] = (0, 0.15, 0)
            if rng.random() < 0.5:
                for seg in range(NB):
                    if rng.random() < 0.55:
                        emi[y0 + 2:y1 - 2, seg * BAY + 10:seg * BAY + BAY - 10] = np.array((1.0, 0.72, 0.30)) * rng.uniform(0.45, 0.95)
            for vx in rng.integers(10, FW - 40, size=2):
                alb[fl * FLOOR + 60:fl * FLOOR + 92, vx:vx + 28] = 0.06; mr[fl * FLOOR + 60:fl * FLOOR + 92, vx:vx + 28] = (0, 0.55, 0.9)
    alb *= _grime((FH, FW), seed + 7)[..., None]
    return (Image.fromarray(to_u8(to_srgb(np.clip(alb, 0, 1)))),
            Image.fromarray(to_u8(to_srgb(np.clip(emi, 0, 1)))),
            Image.fromarray(to_u8(np.clip(mr, 0, 1))))


# ------------------------------------------------------------------ skyline silhouettes
def skyline(width=2048, height=512, layers=2, seed=61, haze=0.0):
    """RGBA far-city silhouette. Colours already fogged so the plane can be unshaded."""
    rng = np.random.default_rng(seed)
    S = 2
    W, H = width * S, height * S
    img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for layer in range(layers):
        t = layer / max(1, layers - 1)
        col_base = np.array((16, 24, 40)) * (1 - t) + np.array((34, 48, 74)) * t     # nearer = darker, farther = hazier
        col_base = col_base * (1 - haze) + np.array((60, 76, 108)) * haze
        x = -int(rng.integers(0, 60)) * S
        while x < W:
            bw = int(rng.integers(40, 150) * S * (1.1 - 0.3 * t))
            peak = 0.55 - 0.35 * abs(x / W - 0.5) * 2
            bh = int((rng.uniform(0.18, 0.62) * (0.7 + 0.5 * peak) * (1 - 0.25 * layer)) * H)
            top = H - bh
            c = tuple(int(v * rng.uniform(0.85, 1.1)) for v in col_base) + (255,)
            d.rectangle([x, top, x + bw, H], fill=c)
            style = rng.integers(0, 4)
            if style == 0 and bw > 60 * S:   # stepped crown
                d.rectangle([x + bw // 4, top - int(20 * S), x + 3 * bw // 4, top], fill=c)
            elif style == 1:                  # antenna
                ax = x + bw // 2; d.rectangle([ax - S, top - int(70 * S), ax + S, top], fill=c)
                d.ellipse([ax - 3 * S, top - int(74 * S), ax + 3 * S, top - int(68 * S)], fill=(255, 40, 40, 255))
            elif style == 2:                  # slanted roof
                d.polygon([(x, top), (x + bw, top), (x + bw, top - int(26 * S)), (x, top)], fill=c)
            # lit windows
            if layer == 0 or rng.random() < 0.5:
                step = 7 * S
                for wy in range(top + 10 * S, H - 10 * S, step * 2):
                    for wx in range(x + 6 * S, x + bw - 6 * S, step):
                        if rng.random() < 0.20:
                            wc = [(255, 200, 120), (255, 170, 90), (150, 215, 255), (255, 235, 200)][int(rng.integers(0, 4))]
                            a = int(rng.uniform(120, 255))
                            d.rectangle([wx, wy, wx + 2 * S, wy + 3 * S], fill=wc + (a,))
            if rng.random() < 0.10 and bw > 70 * S:     # neon billboard strip
                nc = [(255, 90, 40), (40, 210, 255), (255, 60, 150)][int(rng.integers(0, 3))]
                yy = top + int(rng.uniform(0.15, 0.5) * bh)
                d.rectangle([x + 8 * S, yy, x + bw - 8 * S, yy + 8 * S], fill=nc + (255,))
            x += bw + int(rng.integers(-8, 14)) * S
    img = img.resize((width, height), Image.LANCZOS)
    a = np.asarray(img).astype(float)
    # haze gradient: fade silhouettes into the horizon colour near the bottom
    fade = np.linspace(0.0, 1.0, height)[:, None] ** 1.6
    glow = np.array((255, 120, 60)) * 0.0
    a[..., :3] = a[..., :3] * (1 - 0.35 * fade[..., None]) + np.array((70, 90, 130)) * 0.35 * fade[..., None]
    a[..., 3] *= (1.0 - 0.25 * fade)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
