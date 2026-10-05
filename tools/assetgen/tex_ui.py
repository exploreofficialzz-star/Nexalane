"""UI + VFX textures: route decals, HUD/nav icons, logo, light/glow sprites, launcher icons."""
from __future__ import annotations
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from .noise import fbm, blur

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FONT_BOLD = os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Bold.ttf')
FONT_MED = os.path.join(ROOT, 'assets', 'fonts', 'Poppins-Medium.ttf')
S = 4  # supersampling


def font(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_MED, int(size))


def _lin_grad(size, c0, c1, angle=90.0):
    """RGBA linear gradient (angle in degrees, 90 = top->bottom)."""
    w, h = size
    a = math.radians(angle)
    yy, xx = np.mgrid[0:h, 0:w]
    t = ((xx - w / 2) * math.cos(a) + (yy - h / 2) * math.sin(a)) / (abs(w * math.cos(a)) + abs(h * math.sin(a)) + 1e-9) + 0.5
    t = np.clip(t, 0, 1)[..., None]
    c0 = np.array(c0, float); c1 = np.array(c1, float)
    return Image.fromarray(np.clip(c0 * (1 - t) + c1 * t, 0, 255).astype(np.uint8), 'RGBA')


def _mask_paste(base, layer, mask):
    base.paste(layer, (0, 0), mask)


def add_glow(img, radius, gain=1.0, passes=1):
    a = np.asarray(img).astype(float)
    glow = img.filter(ImageFilter.GaussianBlur(radius))
    g = np.asarray(glow).astype(float)
    out = a.copy()
    for _ in range(passes):
        out[..., :3] = np.clip(out[..., :3] + g[..., :3] * gain * (g[..., 3:4] / 255.0), 0, 255)
    out[..., 3] = np.clip(np.maximum(a[..., 3], g[..., 3] * gain), 0, 255)
    return Image.fromarray(out.astype(np.uint8), 'RGBA')


def down(img, size):
    return img.resize((size, size) if isinstance(size, int) else size, Image.LANCZOS)


# --------------------------------------------------------------------------- HUD icons
def icon_credit(size=256):
    N = size * S; img = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    sh = Image.new('RGBA', (N, N), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse([N * .06, N * .10, N * .94, N * .98], fill=(0, 0, 0, 120))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(N * 0.025)))
    r = N * 0.47; c = N / 2; box = [c - r, c - r - N * .01, c + r, c + r - N * .01]
    m = Image.new('L', (N, N), 0); ImageDraw.Draw(m).ellipse(box, fill=255)
    _mask_paste(img, _lin_grad((N, N), (255, 240, 150, 255), (200, 120, 10, 255), 55), m)
    r2 = r * 0.84; m2 = Image.new('L', (N, N), 0); ImageDraw.Draw(m2).ellipse([c - r2, c - r2 - N * .01, c + r2, c + r2 - N * .01], fill=255)
    _mask_paste(img, _lin_grad((N, N), (190, 112, 8, 255), (255, 226, 120, 255), 55), m2)
    r3 = r * 0.74; m3 = Image.new('L', (N, N), 0); ImageDraw.Draw(m3).ellipse([c - r3, c - r3 - N * .01, c + r3, c + r3 - N * .01], fill=255)
    _mask_paste(img, _lin_grad((N, N), (255, 214, 82, 255), (236, 160, 22, 255), 60), m3)
    d = ImageDraw.Draw(img)
    # hexagon emblem + stylised N
    hx = [(c + r * 0.50 * math.cos(math.radians(60 * i + 30)), c - N * .01 + r * 0.50 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(hx, fill=(176, 104, 10, 255))
    hx2 = [(c + r * 0.43 * math.cos(math.radians(60 * i + 30)), c - N * .01 + r * 0.43 * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    d.polygon(hx2, fill=(255, 230, 130, 255))
    hh = r * 0.27; cy = c - N * .01; hw = r * 0.22; t = r * 0.095
    d.polygon([(c - hw, cy + hh), (c - hw, cy - hh), (c - hw + t, cy - hh), (c - hw + t, cy + hh)], fill=(150, 88, 6, 255))
    d.polygon([(c + hw - t, cy + hh), (c + hw - t, cy - hh), (c + hw, cy - hh), (c + hw, cy + hh)], fill=(150, 88, 6, 255))
    d.polygon([(c - hw, cy - hh), (c - hw + t * 1.15, cy - hh), (c + hw, cy + hh), (c + hw - t * 1.15, cy + hh)], fill=(150, 88, 6, 255))
    hl = Image.new('RGBA', (N, N), (0, 0, 0, 0)); ImageDraw.Draw(hl).arc([c - r * 0.93, c - r * 0.93 - N * .01, c + r * 0.93, c + r * 0.93 - N * .01], 200, 262, fill=(255, 255, 255, 190), width=int(N * 0.028))
    img.alpha_composite(hl.filter(ImageFilter.GaussianBlur(N * 0.004)))
    return down(img, size)


def icon_nova(size=256):
    N = size * S; img = Image.new('RGBA', (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    c = N / 2
    P = lambda x, y: (N * x, N * y)
    top = [P(.5, .06), P(.78, .30), P(.5, .40), P(.22, .30)]
    left = [P(.22, .30), P(.5, .40), P(.5, .94), P(.12, .42)]
    right = [P(.78, .30), P(.88, .42), P(.5, .94), P(.5, .40)]
    mid_l = [P(.22, .30), P(.12, .42), P(.5, .40)]
    mid_r = [P(.78, .30), P(.5, .40), P(.88, .42)]
    d.polygon(left, fill=(14, 120, 190, 255)); d.polygon(right, fill=(18, 160, 225, 255))
    d.polygon(mid_l, fill=(70, 200, 245, 255)); d.polygon(mid_r, fill=(110, 225, 255, 255))
    d.polygon(top, fill=(185, 245, 255, 255))
    for a, b in ((P(.5, .06), P(.5, .40)), (P(.22, .30), P(.78, .30))):
        d.line([a, b], fill=(255, 255, 255, 120), width=int(N * .008))
    d.line([P(.5, .06), P(.78, .30), P(.88, .42), P(.5, .94), P(.12, .42), P(.22, .30), P(.5, .06)], fill=(220, 252, 255, 255), width=int(N * .018), joint='curve')
    glow = Image.new('RGBA', (N, N), (0, 0, 0, 0)); ImageDraw.Draw(glow).polygon(top + left[1:] + right[:2][::-1], fill=(40, 200, 255, 160))
    base = glow.filter(ImageFilter.GaussianBlur(N * 0.05)); base.alpha_composite(img)
    return down(base, size)


def icon_flow(size=256):
    N = size * S; img = Image.new('RGBA', (N, N), (0, 0, 0, 0)); c = N / 2
    ring = Image.new('L', (N, N), 0); dr = ImageDraw.Draw(ring)
    dr.arc([N * .09, N * .09, N * .91, N * .91], 140, 400, fill=255, width=int(N * .13))
    for ang in (140, 400):  # round caps
        x = c + math.cos(math.radians(ang)) * N * .345; y = c + math.sin(math.radians(ang)) * N * .345
        dr.ellipse([x - N * .065, y - N * .065, x + N * .065, y + N * .065], fill=255)
    _mask_paste(img, _lin_grad((N, N), (40, 230, 255, 255), (255, 70, 190, 255), 20), ring)
    d = ImageDraw.Draw(img)
    bolt = [(.56, .17), (.31, .55), (.48, .55), (.42, .84), (.70, .43), (.52, .43)]
    d.polygon([(N * x, N * y) for x, y in bolt], fill=(255, 255, 255, 255))
    return down(add_glow(img, N * 0.02, 0.8), size)


def icon_shield(size=256):
    N = size * S; img = Image.new('RGBA', (N, N), (0, 0, 0, 0))
    P = lambda x, y: (N * x, N * y)
    pts = [P(.5, .05), P(.86, .18), P(.84, .52), P(.5, .95), P(.16, .52), P(.14, .18)]
    m = Image.new('L', (N, N), 0); ImageDraw.Draw(m).polygon(pts, fill=255)
    _mask_paste(img, _lin_grad((N, N), (120, 240, 255, 255), (20, 110, 190, 255), 80), m)
    inner = [P(.5, .13), P(.78, .23), P(.76, .50), P(.5, .85), P(.24, .50), P(.22, .23)]
    m2 = Image.new('L', (N, N), 0); ImageDraw.Draw(m2).polygon(inner, fill=255)
    _mask_paste(img, _lin_grad((N, N), (14, 70, 120, 255), (30, 150, 215, 255), 80), m2)
    d = ImageDraw.Draw(img)
    d.polygon([P(.5, .26), P(.64, .46), P(.5, .40), P(.36, .46)], fill=(210, 250, 255, 255))
    d.polygon([P(.5, .42), P(.66, .60), P(.5, .54), P(.34, .60)], fill=(120, 225, 255, 255))
    d.line(pts + [pts[0]], fill=(225, 252, 255, 255), width=int(N * .022), joint='curve')
    return down(add_glow(img, N * 0.02, 0.5), size)


def _glyph(draw_fn, size=128):
    N = size * S; img = Image.new('RGBA', (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    draw_fn(d, N); return down(img, size)

W_ = (255, 255, 255, 255)

def g_garage(d, N):
    d.pieslice([N * .14, N * .12, N * .86, N * .84], 180, 360, fill=W_)
    d.rounded_rectangle([N * .12, N * .48, N * .88, N * .70], N * .05, fill=W_)
    d.rounded_rectangle([N * .30, N * .50, N * .70, N * .60], N * .03, fill=(0, 0, 0, 0))
    d.rounded_rectangle([N * .32, N * .54, N * .68, N * .60], N * .02, fill=(0, 0, 0, 0))

def g_missions(d, N):
    d.rounded_rectangle([N * .20, N * .14, N * .80, N * .90], N * .07, outline=W_, width=int(N * .06))
    d.rounded_rectangle([N * .36, N * .08, N * .64, N * .22], N * .04, fill=W_)
    for i, y in enumerate((.36, .54, .72)):
        d.line([(N * .30, N * y), (N * .36, N * (y + .05)), (N * .46, N * (y - .05))], fill=W_, width=int(N * .045), joint='curve')
        d.line([(N * .54, N * y), (N * .72, N * y)], fill=W_, width=int(N * .045))

def g_shop(d, N):
    d.polygon([(N * .22, N * .36), (N * .78, N * .36), (N * .84, N * .88), (N * .16, N * .88)], fill=W_)
    d.arc([N * .32, N * .12, N * .68, N * .56], 180, 360, fill=W_, width=int(N * .06))
    d.arc([N * .40, N * .52, N * .60, N * .66], 0, 180, fill=(0, 0, 0, 0), width=int(N * .05))

def g_season(d, N):
    pts = []
    for i in range(10):
        r = N * (.38 if i % 2 == 0 else .16); a = math.radians(-90 + 36 * i)
        pts.append((N / 2 + r * math.cos(a), N * .47 + r * math.sin(a)))
    d.polygon(pts, fill=W_)
    d.polygon([(N * .30, N * .78), (N * .70, N * .78), (N * .62, N * .92), (N * .50, N * .86), (N * .38, N * .92)], fill=W_)

def g_ach(d, N):
    d.polygon([(N * .28, N * .12), (N * .72, N * .12), (N * .66, N * .52), (N * .34, N * .52)], fill=W_)
    d.pieslice([N * .34, N * .36, N * .66, N * .68], 0, 180, fill=W_)
    d.arc([N * .08, N * .14, N * .36, N * .46], 90, 270, fill=W_, width=int(N * .05))
    d.arc([N * .64, N * .14, N * .92, N * .46], 270, 450, fill=W_, width=int(N * .05))
    d.rectangle([N * .45, N * .62, N * .55, N * .76], fill=W_); d.rounded_rectangle([N * .30, N * .76, N * .70, N * .88], N * .03, fill=W_)

def g_leaders(d, N):
    d.rounded_rectangle([N * .10, N * .54, N * .34, N * .88], N * .02, fill=W_)
    d.rounded_rectangle([N * .38, N * .36, N * .62, N * .88], N * .02, fill=W_)
    d.rounded_rectangle([N * .66, N * .62, N * .90, N * .88], N * .02, fill=W_)
    pts = []
    for i in range(10):
        r = N * (.12 if i % 2 == 0 else .05); a = math.radians(-90 + 36 * i)
        pts.append((N * .5 + r * math.cos(a), N * .20 + r * math.sin(a)))
    d.polygon(pts, fill=W_)

def g_settings(d, N):
    c = N / 2
    for i in range(8):
        a = math.radians(45 * i)
        x, y = c + math.cos(a) * N * .36, c + math.sin(a) * N * .36
        d.polygon([(c + math.cos(a + .22) * N * .30, c + math.sin(a + .22) * N * .30), (x + math.cos(a + .14) * N * .02, y + math.sin(a + .14) * N * .02),
                   (x - math.cos(a + .14) * N * .0 + math.cos(a - .14) * N * .02, y + math.sin(a - .14) * N * .02), (c + math.cos(a - .22) * N * .30, c + math.sin(a - .22) * N * .30)], fill=W_)
    d.ellipse([c - N * .30, c - N * .30, c + N * .30, c + N * .30], fill=W_)
    d.ellipse([c - N * .13, c - N * .13, c + N * .13, c + N * .13], fill=(0, 0, 0, 0))

def g_pause(d, N):
    d.rounded_rectangle([N * .24, N * .18, N * .42, N * .82], N * .05, fill=W_); d.rounded_rectangle([N * .58, N * .18, N * .76, N * .82], N * .05, fill=W_)

def g_play(d, N):
    d.polygon([(N * .28, N * .16), (N * .80, N * .50), (N * .28, N * .84)], fill=W_)

def g_lock(d, N):
    d.rounded_rectangle([N * .22, N * .44, N * .78, N * .88], N * .08, fill=W_)
    d.arc([N * .30, N * .12, N * .70, N * .72], 180, 360, fill=W_, width=int(N * .08))
    d.rectangle([N * .30, N * .32, N * .38, N * .50], fill=W_); d.rectangle([N * .62, N * .32, N * .70, N * .50], fill=W_)
    d.ellipse([N * .45, N * .56, N * .55, N * .66], fill=(0, 0, 0, 0)); d.rectangle([N * .47, N * .62, N * .53, N * .76], fill=(0, 0, 0, 0))

def g_check(d, N):
    d.line([(N * .18, N * .54), (N * .40, N * .76), (N * .84, N * .26)], fill=W_, width=int(N * .13), joint='curve')

def g_close(d, N):
    d.line([(N * .22, N * .22), (N * .78, N * .78)], fill=W_, width=int(N * .12)); d.line([(N * .78, N * .22), (N * .22, N * .78)], fill=W_, width=int(N * .12))

def g_arrow(d, N):
    d.polygon([(N * .5, N * .10), (N * .86, N * .52), (N * .62, N * .52), (N * .62, N * .90), (N * .38, N * .90), (N * .38, N * .52), (N * .14, N * .52)], fill=W_)

def g_ad(d, N):
    d.rounded_rectangle([N * .10, N * .22, N * .90, N * .78], N * .08, outline=W_, width=int(N * .07))
    d.polygon([(N * .42, N * .36), (N * .66, N * .50), (N * .42, N * .64)], fill=W_)

def g_power(d, N):
    d.arc([N * .18, N * .22, N * .82, N * .86], -60, 240, fill=W_, width=int(N * .10))
    d.line([(N * .5, N * .08), (N * .5, N * .50)], fill=W_, width=int(N * .10))

GLYPHS = dict(icon_garage=g_garage, icon_missions=g_missions, icon_shop=g_shop, icon_season=g_season,
              icon_achievements=g_ach, icon_leaders=g_leaders, icon_settings=g_settings, icon_pause=g_pause,
              icon_play=g_play, icon_lock=g_lock, icon_check=g_check, icon_close=g_close, icon_arrow=g_arrow,
              icon_ad=g_ad, icon_power=g_power)


# --------------------------------------------------------------------------- VFX sprites
def vfx_glow(size=256):
    yy, xx = np.mgrid[0:size, 0:size]; r = np.hypot(xx - size / 2 + .5, yy - size / 2 + .5) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** 2.3
    out = np.zeros((size, size, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def vfx_spark(size=128):
    yy, xx = np.mgrid[0:size, 0:size]; x = (xx - size / 2 + .5) / (size / 2); y = (yy - size / 2 + .5) / (size / 2)
    a = np.clip(1 - np.hypot(x, y), 0, 1) ** 2.2 * 0.8
    a += np.clip(1 - np.abs(y) * 14, 0, 1) * np.clip(1 - np.abs(x), 0, 1) ** 1.5
    a += np.clip(1 - np.abs(x) * 14, 0, 1) * np.clip(1 - np.abs(y), 0, 1) ** 1.5
    out = np.zeros((size, size, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def vfx_ring(size=256):
    yy, xx = np.mgrid[0:size, 0:size]; r = np.hypot(xx - size / 2 + .5, yy - size / 2 + .5) / (size / 2)
    a = np.exp(-((r - 0.82) ** 2) / (2 * 0.045 ** 2)) + 0.25 * np.exp(-((r - 0.72) ** 2) / (2 * 0.09 ** 2))
    a *= np.clip((1 - r) * 7 + 0.2, 0, 1)
    out = np.zeros((size, size, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def vfx_streak(w=256, h=64):
    yy, xx = np.mgrid[0:h, 0:w]; x = xx / (w - 1); y = (yy - h / 2 + .5) / (h / 2)
    a = np.exp(-(y ** 2) / 0.05) * (x ** 1.6) * (1 - 0.25 * x) + 0.4 * np.exp(-(y ** 2) / 0.6) * x ** 3 * 0.35
    out = np.zeros((h, w, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def vfx_smoke(size=256):
    yy, xx = np.mgrid[0:size, 0:size]; r = np.hypot(xx - size / 2 + .5, yy - size / 2 + .5) / (size / 2)
    n = fbm((size, size), 2.6, 77)
    a = np.clip(1 - r, 0, 1) ** 1.2 * (0.35 + 1.1 * n); a = np.clip(a * 0.8, 0, 1)
    out = np.zeros((size, size, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')

def vfx_light_pool(size=256):
    yy, xx = np.mgrid[0:size, 0:size]; r = np.hypot(xx - size / 2 + .5, yy - size / 2 + .5) / (size / 2)
    a = np.clip(1 - r, 0, 1) ** 1.7 * 0.9
    out = np.zeros((size, size, 4), np.uint8); out[..., :3] = 255; out[..., 3] = (a * 255).astype(np.uint8)
    return Image.fromarray(out, 'RGBA')


# --------------------------------------------------------------------------- route decals (holographic gates)
ROUTE_STYLE = {
    'safe':   dict(label='SAFE',   sub='CLEAR LINE',    c=(60, 255, 190),  c2=(30, 170, 255)),
    'fast':   dict(label='FAST',   sub='SPEED PADS',    c=(255, 214, 60),  c2=(255, 120, 30)),
    'reward': dict(label='REWARD', sub='BONUS ORBS',    c=(255, 196, 40),  c2=(255, 236, 140)),
    'secret': dict(label='SECRET', sub='RARE CACHE',    c=(190, 120, 255), c2=(110, 80, 255)),
    'chaos':  dict(label='CHAOS',  sub='HIGH RISK x2',  c=(255, 60, 170),  c2=(255, 90, 60)),
}

def decal(key, W=512, H=256):
    st = ROUTE_STYLE[key]; c = st['c']; c2 = st['c2']
    w, h = W * 2, H * 2
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([14, 14, w - 14, h - 14], 44, fill=(8, 14, 26, 232))
    # animated-looking diagonal scan texture
    sc = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ds = ImageDraw.Draw(sc)
    for x in range(-h, w, 26): ds.line([(x, h), (x + h, 0)], fill=c + (16,), width=6)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle([14, 14, w - 14, h - 14], 44, fill=255)
    img.paste(sc, (0, 0), m)
    if key == 'chaos':
        for x in range(-h, w, 44): d.line([(x, h - 26), (x + 110, 26)], fill=(255, 60, 170, 70), width=18)
    edge = Image.new('RGBA', (w, h), (0, 0, 0, 0)); de = ImageDraw.Draw(edge)
    de.rounded_rectangle([14, 14, w - 14, h - 14], 44, outline=c + (255,), width=10)
    de.rounded_rectangle([34, 34, w - 34, h - 34], 30, outline=c2 + (150,), width=3)
    img.alpha_composite(add_glow(edge, 14, 1.2))
    fs = h * 0.40
    f = font(fs); tw = d.textlength(st['label'], font=f)
    while tw > w * 0.76:
        fs *= 0.94; f = font(fs); tw = d.textlength(st['label'], font=f)
    txt = Image.new('RGBA', (w, h), (0, 0, 0, 0)); dt = ImageDraw.Draw(txt)
    dt.text(((w - tw) / 2, h * 0.14), st['label'], font=f, fill=(255, 255, 255, 255))
    f2 = font(h * 0.105, bold=False); tw2 = d.textlength(st['sub'], font=f2)
    dt.text(((w - tw2) / 2, h * 0.62), st['sub'], font=f2, fill=c + (255,))
    for i in range(5):  # chevron row
        x = w * 0.5 + (i - 2) * 64 - 18; y = h * 0.84
        dt.polygon([(x, y - 16), (x + 22, y), (x, y + 16), (x + 9, y), ], fill=(c if i % 2 == 0 else c2) + (255,))
    img.alpha_composite(add_glow(txt, 10, 0.9))
    return img.resize((W, H), Image.LANCZOS)

def decal_spire(W=512, H=256):
    img = decal('safe', W, H)
    w, h = W * 2, H * 2
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([14, 14, w - 14, h - 14], 44, fill=(14, 10, 8, 235))
    c = (255, 150, 40); c2 = (255, 224, 140)
    edge = Image.new('RGBA', (w, h), (0, 0, 0, 0)); de = ImageDraw.Draw(edge)
    de.rounded_rectangle([14, 14, w - 14, h - 14], 44, outline=c + (255,), width=10); de.rounded_rectangle([34, 34, w - 34, h - 34], 30, outline=c2 + (140,), width=3)
    im.alpha_composite(add_glow(edge, 14, 1.2))
    sp = Image.new('RGBA', (w, h), (0, 0, 0, 0)); ds = ImageDraw.Draw(sp)
    cx = w * 0.22
    ds.polygon([(cx, h * 0.14), (cx + 46, h * 0.84), (cx - 46, h * 0.84)], fill=c + (255,)); ds.polygon([(cx, h * 0.26), (cx + 22, h * 0.84), (cx - 22, h * 0.84)], fill=c2 + (255,))
    f = font(h * 0.34); ds.text((w * 0.36, h * 0.20), 'SPIRE', font=f, fill=(255, 255, 255, 255))
    ds.text((w * 0.37, h * 0.62), 'CENTRAL DISTRICT', font=font(h * 0.095, False), fill=c + (255,))
    im.alpha_composite(add_glow(sp, 10, 0.9))
    return im.resize((W, H), Image.LANCZOS)


# --------------------------------------------------------------------------- logo + launcher icons
def logo(W=1024, H=300):
    w, h = W * 2, H * 2
    base = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(base)
    f = font(h * 0.52); text = 'NEXALANE'; track = 14
    widths = [d.textlength(ch, font=f) for ch in text]; total = sum(widths) + track * (len(text) - 1)
    x = (w - total) / 2; y = h * 0.14
    mask = Image.new('L', (w, h), 0); dm = ImageDraw.Draw(mask)
    for ch, cw in zip(text, widths):
        dm.text((x, y), ch, font=f, fill=255); x += cw + track
    # slanted cut for speed feel
    mask = mask.transform((w, h), Image.AFFINE, (1, 0.16, -h * 0.16 * 0.5, 0, 1, 0), Image.BICUBIC)
    fill = _lin_grad((w, h), (255, 255, 255, 255), (80, 220, 255, 255), 90)
    outline = mask.filter(ImageFilter.MaxFilter(9))
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 0)); sh.paste((255, 120, 40, 255), (0, 0), outline)
    base.alpha_composite(sh); base.paste(fill, (0, 0), mask)
    d = ImageDraw.Draw(base)
    ty = int(h * 0.80)
    for i, (a, b) in enumerate(((0.18, 0.40), (0.42, 0.58), (0.60, 0.82))):
        d.polygon([(w * a, ty), (w * b, ty), (w * b - 26, ty + 20), (w * a - 26, ty + 20)], fill=((255, 150, 50, 255) if i != 1 else (80, 220, 255, 255)))
    d.text((w * 0.5 - d.textlength('3D ENDLESS RUNNER', font=font(h * 0.07, False)) / 2, h * 0.905), '3D ENDLESS RUNNER', font=font(h * 0.07, False), fill=(200, 230, 255, 255))
    return add_glow(base, 16, 0.8).resize((W, H), Image.LANCZOS)


def launcher_icons(master_path, out_dir):
    src = Image.open(master_path).convert('RGB')
    s = min(src.size); src = src.crop(((src.width - s) // 2, (src.height - s) // 2, (src.width + s) // 2, (src.height + s) // 2))
    src.resize((192, 192), Image.LANCZOS).save(os.path.join(out_dir, 'nexalane_icon_192.png'), optimize=True)
    fg = Image.new('RGBA', (432, 432), (0, 0, 0, 0)); core = src.resize((288, 288), Image.LANCZOS).convert('RGBA')
    m = Image.new('L', (288, 288), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, 287, 287], 54, fill=255)
    fg.paste(core, (72, 72), m); fg.save(os.path.join(out_dir, 'nexalane_adaptive_fg_432.png'), optimize=True)
    bg = _lin_grad((432, 432), (8, 14, 28, 255), (20, 34, 58, 255), 70).convert('RGB'); bg.save(os.path.join(out_dir, 'nexalane_adaptive_bg_432.png'), optimize=True)
