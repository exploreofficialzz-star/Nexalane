"""World dressing: textured buildings (near + far tiers), street furniture, district props, set pieces.

Authoring: origin on the ground; the side that must face the street/road is -Z.  Level code rotates a
prop -90deg about Y for the left side of the road and +90deg for the right side.
"""
from __future__ import annotations
import math
import numpy as np
from .geo import *
from .glb import Node
from .kit import rod

SU, SV = 1 / 12.8, 1 / 25.6          # facade tile: 12.8 m wide x 25.6 m tall (4 bays x 8 floors)


def _shell(kind, w, d, h):
    m = Mesh()
    m.box('facade_' + kind, (w, h, d), center=(0, h / 2, 0), uv=(SU, SV), uv_off=(0.0, -(h / 2) * SV))
    m.box('roof', (w + 0.3, 0.4, d + 0.3), center=(0, h + 0.2, 0), bevel=0.04)
    return m


def _ac_units(m, w, d, h, rng, n=4):
    for _ in range(n):
        x = rng.uniform(-w * 0.35, w * 0.35); z = rng.uniform(-d * 0.35, d * 0.35)
        m.box('steel_light', (rng.uniform(1.0, 1.8), 0.8, rng.uniform(1.0, 1.6)), center=(x, h + 0.8, z), bevel=0.04)
        m.cyl('steel_dark', 0.32, 0.32, 0.06, 14, center=(x, h + 1.22, z))


def _shopfront(m, w, d, awning=False, door=False):
    z = -d / 2 - 0.04
    if door:
        m.box('steel_dark', (w * 0.5, 3.2, 0.1), center=(0, 1.6, z), bevel=0.02)
        m.box('hazard', (w * 0.5, 0.35, 0.12), center=(0, 3.25, z), uv=2.0)
        return
    m.box('sign_frame', (w - 0.6, 3.3, 0.10), center=(0, 1.65, z), bevel=0.03)
    for i in range(int((w - 1.2) // 3.2)):
        x = -((int((w - 1.2) // 3.2) - 1) * 3.2) / 2 + i * 3.2
        m.box('shop_glass', (2.6, 2.3, 0.05), center=(x, 1.45, z - 0.04))
    if awning:
        m.box('paint_red', (w - 0.8, 0.12, 1.3), center=(0, 3.15, z - 0.6), xf=Rx(-0.22), bevel=0.02)
        m.box('paint_white', (w - 0.8, 0.13, 0.26), center=(0, 3.17, z - 0.55), xf=Rx(-0.22), bevel=0.02)


def building_a():
    rng = np.random.default_rng(1); w, d, h = 12.8, 12.8, 38.4
    m = _shell('a', w, d, h); _shopfront(m, w, d)
    m.box('facade_a', (w * 0.62, 6.4, d * 0.62), center=(0, h + 3.2 + 0.4, 0), uv=(SU, SV), uv_off=(0.0, -(h + 0.4 + 3.2) * SV))
    m.box('roof', (w * 0.62 + 0.3, 0.3, d * 0.62 + 0.3), center=(0, h + 6.8 + 0.15, 0), bevel=0.03)
    m.box('glow_accent', (w * 0.62 + 0.05, 0.16, d * 0.62 + 0.05), center=(0, h + 6.45, 0))
    _ac_units(m, w, d, h, rng); rod(m, 'steel_dark', (3, h + 7.0, 2), (3, h + 12, 2), 0.06); m.sphere('glow_red', 0.14, 10, 6, center=(3, h + 12.1, 2))
    return [Node('BuildingA', mesh=m)]


def building_b():
    rng = np.random.default_rng(2); w, d, h = 12.8, 12.8, 64.0
    m = _shell('b', w, d, h); _shopfront(m, w, d)
    m.box('facade_b', (w * 0.8, 3.2, d * 0.8), center=(0, h + 0.4 + 1.6, 0), uv=(SU, SV), uv_off=(0.0, -(h + 2.0) * SV))
    m.box('glow_cyan', (w * 0.8 + 0.06, 0.12, d * 0.8 + 0.06), center=(0, h + 3.7, 0))
    rod(m, 'steel_light', (0, h + 3.6, 0), (0, h + 14, 0), 0.09); m.sphere('glow_red', 0.18, 10, 6, center=(0, h + 14.1, 0))
    for sx in (-1, 1):
        m.box('glow_cyan', (0.05, h - 2, 0.05), center=(sx * (w / 2 + 0.02), h / 2 + 1, -d / 2 - 0.02))
    return [Node('BuildingB', mesh=m)]


def building_c():
    rng = np.random.default_rng(3); w, d, h = 12.8, 9.6, 19.2
    m = _shell('c', w, d, h); _shopfront(m, w, d, awning=True)
    m.box('concrete', (w + 0.7, 0.5, d + 0.7), center=(0, h + 0.15, 0), bevel=0.06)         # cornice
    for sx in (-1, 1):
        m.cyl('wood', 1.1, 1.1, 1.8, 16, center=(sx * 3.0, h + 3.1, 1.0))
        m.cyl('rust', 1.15, 1.15, 0.06, 16, center=(sx * 3.0, h + 3.1, 1.0))
        m.cyl('wood', 0.0, 1.2, 0.7, 16, center=(sx * 3.0, h + 4.35, 1.0))
        for ax, az in ((-0.8, -0.6), (0.8, -0.6), (-0.8, 0.6), (0.8, 0.6)):
            rod(m, 'steel_dark', (sx * 3.0 + ax, h + 0.4, 1.0 + az), (sx * 3.0 + ax, h + 2.2, 1.0 + az), 0.05)
    _ac_units(m, w, d, h, rng, 3)
    return [Node('BuildingC', mesh=m)]


def building_d():
    rng = np.random.default_rng(4); w, d, h = 19.2, 12.8, 12.8
    m = _shell('d', w, d, h); _shopfront(m, w, d, door=True)
    for i in range(5):
        x = -w / 2 + 1.9 + i * (w - 3.8) / 4
        m.extrude('roof', [(-1.6, 0), (1.6, 0), (1.6, 2.4), (-1.6, 0.4)][:4], d - 0.4, xf=compose(T(x, h + 0.4, 0), Ry(math.pi / 2)))
    m.cyl('concrete_dark', 0.9, 1.15, 16, 16, center=(w / 2 - 2.2, h + 8.0, 3.0)); m.cyl('paint_red', 0.93, 0.93, 1.6, 16, center=(w / 2 - 2.2, h + 14.4, 3.0))
    m.cyl('paint_white', 0.92, 0.92, 1.6, 16, center=(w / 2 - 2.2, h + 12.0, 3.0)); m.sphere('glow_red', 0.2, 10, 6, center=(w / 2 - 2.2, h + 16.4, 3.0))
    _ac_units(m, w, d, h, rng, 5)
    return [Node('BuildingD', mesh=m)]


def _far(kind, w, d, h, crown):
    m = Mesh(); m.box('facade_' + kind, (w, h, d), center=(0, h / 2, 0), uv=(SU, SV), uv_off=(0.0, -(h / 2) * SV))
    m.box('roof', (w + 0.3, 0.4, d + 0.3), center=(0, h + 0.2, 0), bevel=0.03)
    if crown == 'mast':
        rod(m, 'steel_light', (0, h + 0.4, 0), (0, h + 16, 0), 0.12); m.sphere('glow_red', 0.25, 8, 5, center=(0, h + 16.2, 0))
    elif crown == 'band':
        m.box('glow_accent', (w + 0.08, 0.5, d + 0.08), center=(0, h - 2.0, 0)); m.box('glow_cyan', (w * 0.5, 0.4, d * 0.5), center=(0, h + 1.0, 0))
    elif crown == 'step':
        m.box('facade_' + kind, (w * 0.6, 8, d * 0.6), center=(0, h + 4.4, 0), uv=(SU, SV), uv_off=(0.0, -(h + 4.4) * SV)); m.box('glow_cyan', (w * 0.6 + 0.06, 0.3, d * 0.6 + 0.06), center=(0, h + 8.2, 0))
    return m


def building_far_a(): return [Node('BuildingFarA', mesh=_far('a', 16.0, 16.0, 96.0, 'mast'))]
def building_far_b(): return [Node('BuildingFarB', mesh=_far('b', 12.8, 12.8, 128.0, 'step'))]
def building_far_c(): return [Node('BuildingFarC', mesh=_far('d', 19.2, 16.0, 70.4, 'band'))]
def building_far_d(): return [Node('BuildingFarD', mesh=_far('c', 16.0, 16.0, 57.6, 'mast'))]


# --------------------------------------------------------------------------- street furniture
def street_light():
    m = Mesh()
    m.cyl('pole', 0.17, 0.2, 0.30, 12, center=(0, 0.15, 0))
    m.cyl('pole', 0.07, 0.11, 7.2, 12, center=(0, 3.75, 0))
    pts = [(0, 7.3, 0), (0, 7.78, -0.55), (0, 7.88, -1.5), (0, 7.74, -2.65)]
    for a, b in zip(pts[:-1], pts[1:]): rod(m, 'pole', a, b, 0.05)
    m.box('led_head', (0.52, 0.12, 1.15), center=(0, 7.62, -2.9), bevel=0.05)
    m.box('glow_white', (0.40, 0.025, 0.95), center=(0, 7.545, -2.9))
    m.box('led_head', (0.3, 0.08, 0.3), center=(0, 7.4, -0.12), bevel=0.03)
    rod(m, 'pole', (0, 3.5, 0), (0, 3.7, -0.34), 0.03); m.sphere('glow_amber', 0.13, 10, 6, center=(0, 3.62, -0.38))
    return [Node('StreetLight', mesh=m)]


def _neon(color, seed):
    rng = np.random.default_rng(seed)
    m = Mesh()
    rod(m, 'sign_frame', (0, 5.2, 0), (0, 5.2, -0.95), 0.04); rod(m, 'sign_frame', (0, 4.1, 0), (0, 5.05, -0.95), 0.03)
    m.box('sign_frame', (0.14, 3.0, 1.15), center=(0, 5.2, -1.45), bevel=0.03)
    y = 6.45
    while y > 4.0:
        hgt = rng.uniform(0.18, 0.5); wid = rng.uniform(0.35, 0.95)
        if y - hgt < 3.9: break
        for sx in (-1, 1):
            m.box(color, (0.025, hgt, wid), center=(sx * 0.082, y - hgt / 2, -1.45 + rng.uniform(-0.05, 0.05)))
        y -= hgt + rng.uniform(0.12, 0.25)
    for sx in (-1, 1):
        m.box('glow_white', (0.03, 2.9, 0.025), center=(sx * 0.082, 5.2, -1.45 - 0.55)); m.box('glow_white', (0.03, 2.9, 0.025), center=(sx * 0.082, 5.2, -1.45 + 0.55))
    return [Node('NeonSign', mesh=m)]


def neon_sign_a(): return _neon('glow_orange', 11)
def neon_sign_b(): return _neon('glow_cyan', 12)
def neon_sign_c(): return _neon('glow_magenta', 13)


def prop_bollard():
    m = Mesh(); m.cyl('steel_dark', 0.11, 0.12, 0.9, 12, center=(0, 0.45, 0)); m.cyl('glow_amber', 0.115, 0.115, 0.07, 12, center=(0, 0.72, 0))
    m.sphere('steel_dark', 0.12, 10, 5, center=(0, 0.9, 0), scale=(1, 0.5, 1))
    return [Node('Bollard', mesh=m)]


# --------------------------------------------------------------------------- district props
def prop_container_stack():
    m = Mesh()
    for (x, y, z, mat) in ((0, 1.3, 0, 'container'), (0, 3.9, 0, 'paint_blue'), (2.8, 1.3, 0.6, 'paint_teal'), (-2.8, 1.3, -0.8, 'container_dark')):
        m.box(mat, (2.44, 2.5, 6.0), center=(x, y, z), bevel=0.05)
        for i in range(10):
            m.box('steel_dark', (2.5, 2.3, 0.05), center=(x, y, z - 2.7 + i * 0.6))
    return [Node('ContainerStack', mesh=m)]


def prop_pipe_rack():
    m = Mesh()
    for z in (-4.5, 0, 4.5):
        for sx in (-1, 1): m.box('steel_dark', (0.22, 3.4, 0.22), center=(sx * 1.6, 1.7, z), bevel=0.03)
        m.box('steel_dark', (3.5, 0.2, 0.26), center=(0, 3.4, z), bevel=0.03); m.box('steel_dark', (3.5, 0.2, 0.26), center=(0, 2.2, z), bevel=0.03)
    for (x, y, r, mat) in ((-0.9, 3.7, 0.38, 'steel_light'), (0.3, 3.7, 0.30, 'rust'), (1.2, 3.7, 0.42, 'paint_yellow'), (-0.4, 2.5, 0.28, 'steel_light'), (0.7, 2.5, 0.34, 'paint_red')):
        m.cyl(mat, r, r, 11.0, 16, center=(x, y, 0), xf=Rx(math.pi / 2))
        for z in (-3, 1, 4): m.cyl('steel_dark', r + 0.03, r + 0.03, 0.12, 16, center=(x, y, z), xf=Rx(math.pi / 2))
    m.box('glow_amber', (0.1, 0.1, 0.1), center=(1.6, 3.6, -4.5))
    return [Node('PipeRack', mesh=m)]


def prop_scaffold():
    m = Mesh(); W, D, H = 4.0, 2.0, 14.0
    for sx in (-1, 1):
        for sz in (-1, 1): rod(m, 'steel_light', (sx * W / 2, 0, sz * D / 2), (sx * W / 2, H, sz * D / 2), 0.05)
    for lvl in range(0, int(H // 2.0) + 1):
        y = lvl * 2.0
        m.box('wood', (W + 0.2, 0.07, D + 0.2), center=(0, y, 0), bevel=0.01)
        for sz in (-1, 1): rod(m, 'steel_light', (-W / 2, y + 1.0, sz * D / 2), (W / 2, y + 1.0, sz * D / 2), 0.03)
        if lvl % 2 == 0 and lvl > 0: rod(m, 'steel_dark', (-W / 2, y - 2.0, -D / 2), (W / 2, y, -D / 2), 0.025)
    for y in (3.0, 7.0, 11.0): m.sphere('glow_amber', 0.12, 8, 5, center=(1.6, y, -D / 2 - 0.1))
    m.box('paint_teal', (W, 5.0, 0.03), center=(0, 11.2, -D / 2 - 0.08))
    return [Node('Scaffold', mesh=m)]


def prop_market_stall():
    m = Mesh()
    m.box('wood', (2.8, 0.9, 1.1), center=(0, 0.45, 0), bevel=0.03)
    for sx in (-1, 1):
        for sz in (-1, 1): rod(m, 'steel_dark', (sx * 1.35, 0, sz * 0.55 - 0.3), (sx * 1.35, 2.5, sz * 0.55 - 0.3), 0.04)
    for i in range(7):
        m.box('paint_red' if i % 2 == 0 else 'paint_white', (0.42, 0.06, 1.9), center=(-1.26 + i * 0.42, 2.55, -0.35), xf=Rx(-0.30), bevel=0.01)
    for i in range(5): m.sphere('glow_amber', 0.07, 8, 5, center=(-1.1 + i * 0.55, 2.15, -1.2))
    rng = np.random.default_rng(8)
    for i in range(12): m.sphere(('fruit_orange', 'fruit_red', 'fruit_green')[i % 3], 0.14, 8, 5, center=(-1.1 + (i % 6) * 0.44, 0.98, rng.uniform(-0.3, 0.3)))
    return [Node('MarketStall', mesh=m)]


def prop_catenary_pole():
    m = Mesh()
    m.box('steel_dark', (0.30, 8.6, 0.30), center=(0, 4.3, 0), bevel=0.03); m.box('concrete', (0.8, 0.5, 0.8), center=(0, 0.25, 0), bevel=0.05)
    rod(m, 'steel_dark', (0, 8.2, 0), (0, 8.2, -4.6), 0.07); rod(m, 'steel_dark', (0, 6.5, 0), (0, 8.1, -3.2), 0.04)
    m.box('steel_dark', (20.0, 0.06, 0.06), center=(0, 7.3, -4.6)); m.box('steel_dark', (20.0, 0.04, 0.04), center=(0, 7.75, -4.6))
    m.box('glow_cyan', (0.18, 0.18, 0.18), center=(0, 8.45, -4.6), bevel=0.03)
    return [Node('CatenaryPole', mesh=m)]


def prop_chimney():
    m = Mesh(); H = 30.0
    for i in range(6):
        m.cyl('paint_red' if i % 2 == 0 else 'paint_white', 1.5 - i * 0.07, 1.6 - i * 0.07, H / 6, 20, center=(0, H / 12 + i * H / 6, 0))
    m.cyl('concrete_dark', 1.2, 1.5, 0.8, 20, center=(0, H + 0.4, 0)); m.sphere('glow_red', 0.26, 10, 6, center=(0, H + 1.0, 0))
    m.cyl('steam', 1.6, 0.5, 6.0, 16, center=(0, H + 4.0, 0), caps=False)
    return [Node('Chimney', mesh=m)]


def prop_arch():
    m = Mesh(); half = 6.4
    for sx in (-1, 1):
        m.box('steel_dark', (0.7, 7.2, 0.7), center=(sx * half, 3.6, 0), bevel=0.08); m.box('concrete', (1.3, 0.5, 1.3), center=(sx * half, 0.25, 0), bevel=0.05)
        m.box('glow_accent', (0.08, 6.4, 0.08), center=(sx * (half - 0.38), 3.7, -0.38))
    m.box('steel_dark', (half * 2 + 1.0, 1.1, 0.8), center=(0, 7.2, 0), bevel=0.08)
    m.box('glow_accent', (half * 2 + 0.6, 0.10, 0.04), center=(0, 6.72, -0.42)); m.box('glow_cyan', (half * 2 + 0.6, 0.06, 0.04), center=(0, 7.75, -0.42))
    return [Node('RouteArch', mesh=m)]


def prop_boost_pad():
    m = Mesh()
    m.box('steel_dark', (2.6, 0.05, 5.6), center=(0, 0.025, 0), bevel=0.01)
    for i in range(3):
        z = -1.5 + i * 1.5
        m.extrude('glow_amber', [(-1.0, -0.5), (0, 0.2), (1.0, -0.5), (1.0, -0.15), (0, 0.55), (-1.0, -0.15)], 0.03, xf=compose(T(0, 0.07, z), Rx(-math.pi / 2)))
    for sx in (-1, 1): m.box('glow_amber', (0.06, 0.06, 5.6), center=(sx * 1.28, 0.06, 0))
    return [Node('BoostPad', mesh=m)]


# --------------------------------------------------------------------------- set pieces
def setpiece_crane():
    m = Mesh(); H = 36.0; S = 1.8
    for sx in (-1, 1):
        for sz in (-1, 1): rod(m, 'paint_yellow', (sx * S / 2, 0, sz * S / 2), (sx * S / 2, H, sz * S / 2), 0.09)
    for i in range(int(H // 2.4)):
        y0, y1 = i * 2.4, (i + 1) * 2.4
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            rod(m, 'paint_yellow', (a[0] * S / 2, y0, a[1] * S / 2), (b[0] * S / 2, y0, b[1] * S / 2), 0.04)
        rod(m, 'paint_yellow', (-S / 2, y0, -S / 2), (S / 2, y1, -S / 2), 0.035); rod(m, 'paint_yellow', (S / 2, y0, S / 2), (-S / 2, y1, S / 2), 0.035)
    m.box('paint_white', (2.6, 1.4, 2.6), center=(0, H + 0.7, 0), bevel=0.08); m.box('glass_dark', (1.0, 0.9, 0.06), center=(0, H + 1.5, -1.35))
    m.box('paint_yellow', (1.5, 1.5, 24.0), center=(0, H + 2.6, -12.0 + 1.0), bevel=0.05)  # jib
    for i in range(10):
        z = -1.0 - i * 2.2
        rod(m, 'paint_yellow', (-0.7, H + 1.9, z), (0, H + 3.7, z - 1.1), 0.04); rod(m, 'paint_yellow', (0.7, H + 1.9, z), (0, H + 3.7, z - 1.1), 0.04)
    m.box('concrete_dark', (2.2, 1.8, 3.0), center=(0, H + 2.4, 5.0), bevel=0.05); m.box('paint_yellow', (1.3, 1.3, 9.0), center=(0, H + 2.6, 4.0))
    rod(m, 'steel_dark', (0, H + 3.4, -18), (0, H - 5, -18), 0.03); m.box('steel_dark', (0.7, 0.5, 0.7), center=(0, H - 5.3, -18), bevel=0.04)
    m.sphere('glow_red', 0.3, 10, 6, center=(0, H + 4.4, -22.0)); m.sphere('glow_red', 0.3, 10, 6, center=(0, H + 4.4, 7.5))
    return [Node('TowerCrane', mesh=m)]


def setpiece_spire():
    m = Mesh()
    tiers = [(0, 9.0, 6.0, 8.0), (8.0, 6.0, 4.2, 14.0), (22.0, 4.2, 2.6, 18.0), (40.0, 2.6, 1.3, 20.0)]
    for (y, rb, rt, h) in tiers:
        m.cyl('facade_b' if False else 'steel_dark', rt, rb, h, 24, center=(0, y + h / 2, 0))
        m.cyl('glow_cyan', rt + 0.06, rt + 0.06, 0.4, 24, center=(0, y + h - 0.4, 0), caps=False)
        m.cyl('glow_accent', rb + 0.05, rb + 0.05, 0.35, 24, center=(0, y + 0.8, 0), caps=False)
    rod(m, 'steel_light', (0, 60, 0), (0, 92, 0), 0.22)
    for y in (66, 74, 82): m.cyl('glow_cyan', 0.9 - (y - 66) * 0.04, 0.9 - (y - 66) * 0.04, 0.12, 20, center=(0, y, 0), caps=False)
    m.sphere('glow_red', 0.5, 12, 8, center=(0, 92.4, 0))
    for i in range(12):
        a = 2 * math.pi * i / 12; m.box('glow_white', (0.12, 12, 0.12), center=(math.cos(a) * 9.05, 5.0, math.sin(a) * 9.05))
    return [Node('Spire', mesh=m)]


WORLD_BUILDERS = dict(
    building_a=building_a, building_b=building_b, building_c=building_c, building_d=building_d,
    building_far_a=building_far_a, building_far_b=building_far_b, building_far_c=building_far_c, building_far_d=building_far_d,
    street_light=street_light, neon_sign_a=neon_sign_a, neon_sign_b=neon_sign_b, neon_sign_c=neon_sign_c,
    prop_bollard=prop_bollard, prop_container_stack=prop_container_stack, prop_pipe_rack=prop_pipe_rack,
    prop_scaffold=prop_scaffold, prop_market_stall=prop_market_stall, prop_catenary_pole=prop_catenary_pole,
    prop_chimney=prop_chimney, prop_arch=prop_arch, prop_boost_pad=prop_boost_pad,
    setpiece_crane=setpiece_crane, setpiece_spire=setpiece_spire)
