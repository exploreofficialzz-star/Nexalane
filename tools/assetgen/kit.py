"""Shared materials + small modelling helpers for NEXALANE's procedural GLB models."""
from __future__ import annotations
import math
import numpy as np
from PIL import Image, ImageDraw
from .geo import *
from .glb import Mat, Node


def lin(rgb, a=1.0):
    c = np.array(rgb[:3], float) / 255.0
    l = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return (float(l[0]), float(l[1]), float(l[2]), a)


def hazard_texture(size=256, stripes=8):
    img = Image.new('RGB', (size, size), (24, 24, 26)); d = ImageDraw.Draw(img)
    step = size // stripes
    for i in range(-stripes, stripes * 2):
        x = i * step
        d.polygon([(x, size), (x + step // 2, size), (x + step // 2 + size, 0), (x + size, 0)], fill=(248, 192, 12))
    return img


def make_mats(tex: dict):
    """tex: hazard, coin, facade_{a..d}: (albedo, emission, mr)."""
    M = {}

    def add(name, rgb, metal=0.0, rough=0.7, emissive=None, alpha='OPAQUE', double=False, **kw):
        base = lin(rgb) if emissive is None else (0.02, 0.02, 0.02, 1.0)
        if alpha != 'OPAQUE' and len(rgb) == 4: base = lin(rgb, rgb[3] / 255.0)
        M[name] = Mat(name, base, metal, rough, tuple(lin(emissive)[:3]) if emissive else (0, 0, 0), alpha, double, **kw)

    add('concrete', (122, 124, 128), 0.0, 0.93); add('concrete_dark', (66, 69, 76), 0.0, 0.9)
    add('steel_dark', (44, 48, 56), 0.9, 0.42); add('steel_light', (168, 174, 184), 0.85, 0.32)
    add('steel_wet', (60, 66, 76), 0.95, 0.12); add('rust', (122, 62, 38), 0.35, 0.85)
    add('paint_orange', (232, 96, 22), 0.2, 0.42); add('paint_yellow', (244, 188, 18), 0.15, 0.4)
    add('paint_white', (232, 232, 228), 0.05, 0.5); add('paint_red', (190, 34, 30), 0.15, 0.42)
    add('paint_blue', (34, 84, 176), 0.2, 0.4); add('paint_teal', (24, 140, 140), 0.2, 0.45)
    add('container', (176, 62, 38), 0.3, 0.68); add('container_dark', (120, 40, 26), 0.3, 0.75)
    add('rubber', (14, 14, 16), 0.0, 0.95); add('wood', (112, 78, 50), 0.0, 0.82)
    add('glass', (28, 46, 62, 150), 0.0, 0.08, alpha='BLEND', double=True)
    add('glass_dark', (8, 12, 18), 0.2, 0.06)
    add('rotor', (180, 200, 220, 70), 0.0, 0.3, alpha='BLEND', double=True)
    add('steam', (235, 240, 245, 70), 0.0, 1.0, alpha='BLEND', double=True)
    add('fruit_orange', (240, 120, 20), 0, 0.6); add('fruit_red', (200, 30, 40), 0, 0.5); add('fruit_green', (80, 170, 50), 0, 0.6)
    for n, c in (('glow_orange', (255, 120, 30)), ('glow_cyan', (40, 210, 255)), ('glow_red', (255, 40, 30)),
                 ('glow_white', (255, 244, 220)), ('glow_accent', (255, 120, 30)), ('glow_magenta', (255, 60, 160)),
                 ('glow_green', (60, 255, 150)), ('glow_amber', (255, 176, 40)), ('glow_gold', (255, 200, 60)),
                 ('glow_visor', (60, 230, 255))):
        add(n, (0, 0, 0), 0.0, 0.4, emissive=c)
    add('laser_halo', (0, 0, 0), 0.0, 0.5, emissive=(255, 40, 30), alpha='BLEND', double=True)
    M['laser_halo'].base = (0.02, 0.0, 0.0, 0.28)
    M['hazard'] = Mat('hazard', (1, 1, 1, 1), 0.1, 0.5, base_tex=tex['hazard'])
    # runner
    add('RunnerSuit', (36, 40, 50), 0.05, 0.68); add('RunnerSuit2', (50, 55, 66), 0.05, 0.78)
    add('RunnerAccent', (236, 96, 22), 0.1, 0.45); add('RunnerGlove', (14, 14, 17), 0.0, 0.5)
    add('RunnerGlow', (0, 0, 0), 0.0, 0.4, emissive=(255, 110, 30))
    add('RunnerShoe', (210, 214, 220), 0.1, 0.55); add('RunnerPad', (20, 21, 24), 0.0, 0.85)
    add('RunnerHelmet', (38, 42, 50), 0.7, 0.32); add('RunnerVisor', (6, 10, 16), 0.9, 0.05)
    add('RunnerSkin', (170, 120, 92), 0.0, 0.6); add('RunnerPack', (46, 50, 56), 0.2, 0.7)
    # collectibles
    M['coin_face'] = Mat('coin_face', (1, 1, 1, 1), 0.85, 0.28, emissive=(0.22, 0.14, 0.02), base_tex=tex['coin'])
    add('coin_edge', (230, 160, 30), 0.9, 0.3)
    add('nova_crystal', (30, 200, 255), 0.2, 0.08, emissive=(30, 150, 255))
    # buildings (textured)
    for k in 'abcd':     # placeholders: ModelLibrary swaps in shared textured materials (see model_library.gd)
        M['facade_' + k] = Mat('facade_' + k, lin((120, 124, 132)), 0.0, 0.8)
    add('roof', (52, 55, 62), 0.1, 0.88); add('shop_glass', (255, 200, 120), 0.0, 0.2, emissive=(255, 190, 110))
    add('pole', (30, 33, 40), 0.85, 0.45); add('led_head', (30, 33, 40), 0.7, 0.35)
    add('sign_frame', (24, 26, 32), 0.8, 0.4)
    return M


def align_y(d):
    """4x4 rotation taking +Y onto direction d."""
    d = np.array(d, float); d /= np.linalg.norm(d) + 1e-12
    y = np.array([0, 1.0, 0]); v = np.cross(y, d); c = float(y @ d); s = np.linalg.norm(v)
    if s < 1e-9:
        return np.eye(4) if c > 0 else Rx(math.pi)
    k = v / s; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + K * s + K @ K * (1 - c)
    m = np.eye(4); m[:3, :3] = R; return m


def rod(m: Mesh, mat, p0, p1, r=0.03, seg=8):
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    mid = (p0 + p1) / 2; L = float(np.linalg.norm(p1 - p0))
    m.cyl(mat, r, r, L, seg, xf=compose(T(*mid), align_y(p1 - p0)))


def wheel(m: Mesh, x, y, z, r=0.32, w=0.22, tyre='rubber', hub='steel_light'):
    xf = compose(T(x, y, z), Rz(math.pi / 2))
    m.cyl(tyre, r, r, w, 18, xf=xf); m.cyl(hub, r * 0.55, r * 0.55, w + 0.02, 14, xf=xf)


def bounds(node: Node, off=(0, 0, 0)):
    """World AABB of a node tree (translation-only hierarchy, as produced by these builders)."""
    o = np.array(off, float) + np.array(node.t, float)
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    if node.mesh is not None:
        for mat in node.mesh.materials():
            p = node.mesh.arrays(mat)[0] + o
            lo = np.minimum(lo, p.min(0)); hi = np.maximum(hi, p.max(0))
    for c in node.children:
        l2, h2 = bounds(c, o); lo = np.minimum(lo, l2); hi = np.maximum(hi, h2)
    return lo, hi
