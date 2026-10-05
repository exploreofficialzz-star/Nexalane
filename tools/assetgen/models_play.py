"""Gameplay models: articulated runner, 15 obstacle families, collectibles.

Authoring conventions
* metres, +Y up, origin on the ground at the object's centre.
* Runner / collectibles face +Z (travel direction).  Obstacles are authored facing -Z, i.e. their
  detailed "front" (lights, cab, signage) looks back at the oncoming player.
"""
from __future__ import annotations
import math
import numpy as np
from .geo import *
from .glb import Node
from .kit import rod, wheel, bounds


# ============================================================================ runner
def build_runner():
    R = Node('Runner')
    hips = R.add(Node('Hips', t=(0, 0.94, 0)))
    hm = Mesh(); hm.box('RunnerSuit2', (0.35, 0.20, 0.23), bevel=0.055); hm.box('RunnerAccent', (0.36, 0.03, 0.235), center=(0, 0.075, 0), bevel=0.01)
    hips.mesh = hm
    torso = hips.add(Node('Torso', t=(0, 0.09, 0)))
    tm = Mesh()
    tm.loft('RunnerSuit', [(0.00, 0.168, 0.108, 0, 0), (0.14, 0.160, 0.102, 0, 0), (0.30, 0.192, 0.116, 0, 0.004), (0.44, 0.208, 0.122, 0, 0), (0.52, 0.170, 0.102, 0, 0), (0.575, 0.075, 0.062, 0, 0)], seg=20, caps=(False, True))
    tm.box('RunnerAccent', (0.40, 0.034, 0.012), center=(0, 0.34, 0.123), bevel=0.005)          # chest band
    tm.box('RunnerAccent', (0.034, 0.30, 0.012), center=(0.07, 0.30, 0.122), bevel=0.005, xf=Rz(-0.35))
    tm.box('RunnerSuit2', (0.30, 0.20, 0.016), center=(0, 0.22, 0.118), bevel=0.006)             # zip panel
    tm.cyl('RunnerSuit', 0.10, 0.085, 0.07, 18, center=(0, 0.60, 0))                              # collar
    tm.box('RunnerPack', (0.31, 0.40, 0.155), center=(0, 0.30, -0.205), bevel=0.05)               # backpack
    tm.box('RunnerAccent', (0.04, 0.34, 0.012), center=(0.09, 0.32, -0.29), bevel=0.004)
    tm.box('RunnerAccent', (0.04, 0.34, 0.012), center=(-0.09, 0.32, -0.29), bevel=0.004)
    tm.box('RunnerGlow', (0.022, 0.26, 0.01), center=(0, 0.30, -0.286))
    tm.box('RunnerAccent', (0.045, 0.30, 0.012), center=(0.115, 0.34, 0.118), bevel=0.004, xf=Rz(0.18))
    tm.box('RunnerAccent', (0.045, 0.30, 0.012), center=(-0.115, 0.34, 0.118), bevel=0.004, xf=Rz(-0.18))
    hm2 = Mesh()
    hm2.cyl('RunnerSkin', 0.046, 0.05, 0.10, 14, center=(0, 0.0, 0))
    hm2.sphere('RunnerHelmet', 1.0, seg=22, rings=14, center=(0, 0.105, -0.005), scale=(0.118, 0.136, 0.150))
    hm2.sphere('RunnerVisor', 1.0, seg=18, rings=10, center=(0, 0.100, 0.082), scale=(0.104, 0.060, 0.082))
    hm2.box('glow_visor', (0.118, 0.012, 0.012), center=(0, 0.108, 0.158), bevel=0.003)
    hm2.box('RunnerAccent', (0.026, 0.012, 0.30), center=(0, 0.238, -0.005), bevel=0.004, xf=Rx(-0.02))
    for sx in (1, -1):
        hm2.cyl('RunnerPad', 0.045, 0.045, 0.045, 14, center=(sx * 0.118, 0.095, -0.01), xf=Rz(math.pi / 2))
        hm2.box('RunnerAccent', (0.008, 0.05, 0.05), center=(sx * 0.144, 0.095, -0.01))
    tm.merge(hm2, xf=T(0, 0.63, 0))
    torso.mesh = tm
    for side, sx in (('L', 1), ('R', -1)):
        arm = torso.add(Node('Arm' + side, t=(sx * 0.232, 0.47, 0)))
        am = Mesh()
        am.sphere('RunnerSuit', 0.074, seg=14, rings=9, scale=(1.0, 0.92, 1.0))
        am.loft('RunnerSuit', capsule_sections(0.30, 0.047, 0.060, rings=4), seg=14, caps=(False, False), xf=T(0, -0.30, 0))
        am.cyl('RunnerAccent', 0.062, 0.062, 0.035, 14, center=(0, -0.10, 0))
        arm.mesh = am
        fa = arm.add(Node('Forearm' + side, t=(0, -0.285, 0)))
        fm = Mesh()
        fm.loft('RunnerSuit', capsule_sections(0.27, 0.040, 0.047, rings=4), seg=14, caps=(False, False), xf=T(0, -0.27, 0))
        fm.cyl('RunnerAccent', 0.045, 0.045, 0.03, 14, center=(0, -0.22, 0))
        fm.box('RunnerGlove', (0.088, 0.105, 0.115), center=(0, -0.315, 0.012), bevel=0.03)
        fm.box('RunnerGlove', (0.05, 0.03, 0.07), center=(sx * -0.0, -0.275, 0.03), bevel=0.01, xf=T(0, 0, 0.02))
        fa.mesh = fm
        leg = hips.add(Node('Leg' + side, t=(sx * 0.098, -0.02, 0)))
        lm = Mesh()
        lm.loft('RunnerSuit2', capsule_sections(0.47, 0.060, 0.094, rings=4), seg=16, caps=(False, False), xf=T(0, -0.47, 0))
        lm.box('RunnerAccent', (0.012, 0.30, 0.03), center=(sx * 0.093, -0.22, 0), bevel=0.004)
        leg.mesh = lm
        shin = leg.add(Node('Shin' + side, t=(0, -0.44, 0)))
        sm = Mesh()
        sm.loft('RunnerSuit2', capsule_sections(0.43, 0.046, 0.062, rings=4), seg=14, caps=(False, False), xf=T(0, -0.43, 0))
        sm.box('RunnerPad', (0.105, 0.13, 0.05), center=(0, 0.015, 0.058), bevel=0.02)          # knee pad
        shin.mesh = sm
        fo = Mesh()
        fo.box('RunnerShoe', (0.118, 0.085, 0.30), center=(0, 0.0, 0.065), bevel=0.03)
        fo.box('RunnerAccent', (0.122, 0.022, 0.31), center=(0, -0.047, 0.065), bevel=0.008)
        fo.box('RunnerSuit', (0.10, 0.07, 0.10), center=(0, 0.02, -0.07), bevel=0.02)
        sm.merge(fo, xf=T(0, -0.42, 0))
        shin.mesh = sm
    lo, hi = bounds(R)
    R.t = (0, -float(lo[1]), 0)           # feet exactly on y = 0
    return [R]


# ============================================================================ obstacles
def _root(name, mesh):
    return [Node(name, mesh=mesh)]


def obstacle_barrier():
    m = Mesh()
    poly = [(-0.45, 0), (0.45, 0), (0.45, 0.18), (0.17, 0.62), (0.14, 1.0), (-0.14, 1.0), (-0.17, 0.62), (-0.45, 0.18)]
    m.extrude('concrete', poly, 2.5, xf=Ry(math.pi / 2))
    for sz in (-1, 1):
        m.box('hazard', (2.3, 0.26, 0.012), center=(0, 0.82, sz * 0.146), uv=1.6)
    m.box('paint_white', (2.5, 0.05, 0.3), center=(0, 1.0, 0), bevel=0.01)
    for sx in (-1, 1):
        m.cyl('glow_red', 0.07, 0.07, 0.08, 12, center=(sx * 1.0, 1.06, 0))
    m.box('glow_orange', (2.3, 0.03, 0.012), center=(0, 0.50, -0.205))
    return _root('Barrier', m)


def obstacle_traffic():
    m = Mesh()
    m.box('paint_yellow', (1.95, 0.62, 4.4), center=(0, 0.68, 0), bevel=0.14)
    m.box('paint_yellow', (1.80, 0.50, 2.2), center=(0, 1.20, 0.25), bevel=0.16)
    m.box('glass', (1.83, 0.36, 2.34), center=(0, 1.22, 0.25), bevel=0.12)
    m.box('rubber', (1.97, 0.07, 4.0), center=(0, 0.80, 0))
    m.box('glow_amber', (0.55, 0.15, 0.22), center=(0, 1.56, 0.25), bevel=0.04)
    m.box('rubber', (1.9, 0.16, 0.10), center=(0, 0.45, -2.2), bevel=0.04); m.box('rubber', (1.9, 0.16, 0.10), center=(0, 0.45, 2.2), bevel=0.04)
    for sx in (-1, 1):
        m.box('glow_white', (0.34, 0.16, 0.06), center=(sx * 0.68, 0.76, -2.2), bevel=0.03)
        m.box('glow_red', (0.34, 0.14, 0.06), center=(sx * 0.70, 0.80, 2.2), bevel=0.03)
        for sz in (-1.35, 1.35):
            wheel(m, sx * 0.93, 0.33, sz)
    m.box('paint_white', (0.40, 0.12, 0.02), center=(0, 0.52, -2.215))
    return _root('Taxi', m)


def obstacle_train():
    m = Mesh()
    m.box('steel_light', (2.9, 3.0, 8.0), center=(0, 1.9, 0), bevel=0.28)
    m.box('steel_dark', (2.86, 0.46, 7.9), center=(0, 0.52, 0), bevel=0.06)
    m.box('glass_dark', (2.93, 0.72, 6.3), center=(0, 2.42, 0.2), bevel=0.1)
    m.box('paint_orange', (2.94, 0.16, 7.9), center=(0, 1.62, 0), bevel=0.02)
    m.box('glass_dark', (2.15, 1.05, 0.06), center=(0, 2.45, -4.0), bevel=0.04)
    m.box('steel_dark', (2.3, 0.10, 0.07), center=(0, 2.98, -4.0))
    m.box('glow_accent', (1.2, 0.26, 0.05), center=(0, 3.14, -4.01))
    for sx in (-1, 1):
        m.box('glow_white', (0.24, 0.24, 0.06), center=(sx * 0.95, 1.18, -4.01), bevel=0.04)
        m.box('glow_red', (0.14, 0.14, 0.06), center=(sx * 0.62, 1.18, -4.01), bevel=0.03)
    m.box('steel_dark', (1.6, 0.22, 0.30), center=(0, 0.80, -4.12), bevel=0.04)        # coupler
    for z in (-2.7, 2.7): m.box('steel_dark', (2.5, 0.38, 1.5), center=(0, 0.30, z), bevel=0.05)
    for z in (-1.8, 1.4): m.box('steel_dark', (1.2, 0.26, 1.8), center=(0, 3.38, z), bevel=0.05)
    return _root('TrainCar', m)


def obstacle_beam():
    m = Mesh()
    for sx in (-1, 1): m.box('steel_dark', (0.28, 2.4, 0.5), center=(sx * 1.5, 1.2, 0), bevel=0.04)
    m.box('hazard', (3.2, 0.30, 0.72), center=(0, 1.20, 0), uv=2.0)
    m.box('steel_dark', (3.2, 0.95, 0.70), center=(0, 1.825, 0), bevel=0.04)
    m.box('steel_light', (3.2, 0.06, 0.74), center=(0, 2.33, 0), bevel=0.01)
    m.box('glow_accent', (2.4, 0.07, 0.02), center=(0, 1.78, -0.36))
    for sx in (-1, 1): m.cyl('glow_orange', 0.11, 0.11, 0.12, 14, center=(sx * 1.5, 2.46, 0))
    return _root('LowBeam', m)


def obstacle_trench():
    m = Mesh()
    m.box('rubber', (2.7, 0.04, 2.2), center=(0, 0.03, 0))
    for sz in (-1, 1):
        m.box('hazard', (2.8, 0.58, 0.16), center=(0, 0.30, sz * 1.12), bevel=0.03, uv=2.0)
    for sx in (-1, 1):
        m.box('wood', (0.12, 0.46, 2.3), center=(sx * 1.4, 0.23, 0), bevel=0.02)
        for sz in (-1, 1):
            m.cyl('steel_dark', 0.03, 0.03, 0.95, 8, center=(sx * 1.3, 0.47, sz * 1.1))
            m.cyl('glow_orange', 0.07, 0.07, 0.10, 12, center=(sx * 1.3, 0.97, sz * 1.1))
    m.box('wood', (2.6, 0.07, 0.26), center=(0, 0.22, 0.2), bevel=0.01)
    m.box('wood', (2.6, 0.07, 0.26), center=(0, 0.22, -0.4), bevel=0.01, xf=T(0, 0, 0))
    for x in (-0.9, 0.0, 0.9): rod(m, 'rust', (x, 0.04, -0.8), (x, 0.52, -0.7), 0.025)
    return _root('Trench', m)


def obstacle_drone():
    m = Mesh()
    cy = 1.55
    m.box('steel_dark', (0.78, 0.30, 0.78), center=(0, cy, 0), bevel=0.11)
    m.sphere('glass_dark', 0.24, seg=16, rings=10, center=(0, cy - 0.10, -0.30))
    m.sphere('glow_red', 0.085, seg=12, rings=8, center=(0, cy - 0.10, -0.50))
    m.cyl('glow_cyan', 0.34, 0.34, 0.025, 28, center=(0, cy - 0.17, 0))
    for sx in (-1, 1):
        for sz in (-1, 1):
            p = np.array([sx * 0.50, cy + 0.04, sz * 0.50])
            rod(m, 'steel_light', (sx * 0.12, cy + 0.02, sz * 0.12), tuple(p), 0.04)
            m.cyl('steel_dark', 0.085, 0.085, 0.12, 12, center=tuple(p + np.array([0, 0.05, 0])))
            m.cyl('rotor', 0.30, 0.30, 0.012, 28, center=tuple(p + np.array([0, 0.13, 0])))
    m.box('glow_white', (0.30, 0.04, 0.05), center=(0, cy + 0.16, -0.40))
    return _root('Drone', m)


def obstacle_gate():
    m = Mesh()
    for sx in (-1, 1):
        m.box('concrete_dark', (0.30, 2.5, 0.5), center=(sx * 1.45, 1.25, 0), bevel=0.03)
        m.cyl('glow_red', 0.07, 0.07, 0.04, 12, center=(sx * 1.45, 1.0, -0.27), xf=Rx(math.pi / 2))
    m.box('steel_dark', (3.2, 1.25, 0.5), center=(0, 1.675, 0), bevel=0.07)
    m.box('hazard', (3.2, 0.13, 0.52), center=(0, 1.115, 0), uv=2.0)
    m.box('glow_accent', (2.6, 0.30, 0.02), center=(0, 1.78, -0.26))
    m.box('steel_light', (3.2, 0.05, 0.54), center=(0, 2.32, 0), bevel=0.01)
    return _root('Gate', m)


def obstacle_container():
    m = Mesh()
    m.box('container', (2.44, 2.5, 5.95), center=(0, 1.3, 0), bevel=0.05)
    for sx in (-1, 1):
        for i in range(29):
            m.box('container_dark', (0.07, 2.3, 0.10), center=(sx * 1.245, 1.3, -2.8 + i * 0.2))
    for sx in (-1, 1):
        for sy in (0.07, 2.53):
            for sz in (-1, 1):
                m.box('steel_dark', (0.2, 0.2, 0.2), center=(sx * 1.2, sy, sz * 2.9), bevel=0.02)
    for sx in (-0.5, 0.5):
        m.cyl('steel_light', 0.03, 0.03, 2.2, 8, center=(sx, 1.3, -3.0))
    m.box('steel_dark', (2.3, 0.07, 0.06), center=(0, 1.3, -3.0))
    for i, x in enumerate((-0.6, 0.0, 0.6)):
        m.box('paint_white', (0.34, 0.20, 0.012), center=(x * 1.0, 2.1, -3.0))
    return _root('Container', m)


def obstacle_crane():
    m = Mesh()
    m.box('paint_yellow', (2.0, 1.5, 2.0), center=(0, 1.8, 0), bevel=0.07)
    for y in (1.22, 2.38): m.box('hazard', (2.03, 0.18, 2.03), center=(0, y, 0), uv=2.0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box('steel_dark', (0.16, 0.16, 0.16), center=(sx * 0.9, 2.5, sz * 0.9), bevel=0.02)
            rod(m, 'steel_dark', (sx * 0.9, 2.55, sz * 0.9), (0, 4.3, 0), 0.025)
            m.cyl('glow_orange', 0.05, 0.05, 0.05, 10, center=(sx * 0.9, 2.62, sz * 0.9))
    m.box('steel_dark', (0.34, 0.30, 0.18), center=(0, 4.32, 0), bevel=0.04)
    m.box('steel_dark', (4.0, 0.34, 0.5), center=(0, 4.75, 0), bevel=0.04)
    return _root('CraneLoad', m)


def obstacle_steam():
    m = Mesh()
    m.box('concrete_dark', (1.6, 0.12, 1.6), center=(0, 0.06, 0), bevel=0.02)
    m.box('hazard', (1.6, 0.06, 0.12), center=(0, 0.14, -0.74), uv=2.0); m.box('hazard', (1.6, 0.06, 0.12), center=(0, 0.14, 0.74), uv=2.0)
    m.cyl('steel_light', 0.28, 0.28, 1.5, 22, center=(-0.30, 0.87, 0.18))
    for y in (0.35, 0.95, 1.55): m.cyl('steel_dark', 0.34, 0.34, 0.08, 22, center=(-0.30, y, 0.18))
    m.cyl('rust', 0.20, 0.20, 1.1, 18, center=(0.36, 0.67, -0.22))
    for y in (0.3, 1.1): m.cyl('steel_dark', 0.25, 0.25, 0.07, 18, center=(0.36, y, -0.22))
    m.cyl('steel_dark', 0.22, 0.30, 0.18, 20, center=(-0.30, 1.72, 0.18))
    m.cyl('paint_red', 0.20, 0.20, 0.04, 20, center=(0.36, 1.0, -0.22), xf=Rx(math.pi / 2))
    m.cyl('glow_amber', 0.07, 0.07, 0.03, 14, center=(-0.30, 1.0, -0.12), xf=Rx(math.pi / 2))
    m.cyl('steam', 0.55, 0.20, 1.0, 20, center=(-0.30, 2.3, 0.18), caps=False)
    return _root('SteamVent', m)


def obstacle_forklift():
    m = Mesh()
    m.box('paint_orange', (1.3, 0.70, 2.2), center=(0, 0.65, 0.35), bevel=0.12)
    m.box('steel_dark', (1.4, 0.80, 0.6), center=(0, 0.75, 1.3), bevel=0.08)
    for sx in (-1, 1):
        for sz in (-0.05, 0.75): m.box('steel_dark', (0.06, 1.15, 0.06), center=(sx * 0.55, 1.58, 0.3 + sz - 0.4))
        m.box('steel_dark', (0.09, 1.9, 0.12), center=(sx * 0.28, 0.95, -0.95))
        m.box('steel_light', (0.12, 0.06, 0.95), center=(sx * 0.36, 0.14, -1.12), bevel=0.01)
        m.box('glow_white', (0.2, 0.12, 0.05), center=(sx * 0.45, 0.85, -0.76), bevel=0.02)
        wheel(m, sx * 0.72, 0.30, -0.45, r=0.30, w=0.20); wheel(m, sx * 0.68, 0.25, 1.05, r=0.25, w=0.18)
    m.box('steel_dark', (1.2, 0.06, 1.25), center=(0, 2.15, 0.28), bevel=0.01)
    m.box('rubber', (0.5, 0.12, 0.5), center=(0, 1.0, 0.45), bevel=0.04); m.box('rubber', (0.5, 0.5, 0.10), center=(0, 1.3, 0.72), bevel=0.04)
    m.box('steel_dark', (0.95, 0.10, 0.1), center=(0, 1.2, -0.95))
    m.cyl('glow_amber', 0.08, 0.08, 0.12, 14, center=(0, 2.24, 0.3))
    return _root('Forklift', m)


def obstacle_laser():
    m = Mesh()
    for sx in (-1, 1):
        m.cyl('steel_dark', 0.10, 0.10, 0.9, 14, center=(sx * 1.45, 0.45, 0))
        m.box('steel_dark', (0.24, 0.30, 0.24), center=(sx * 1.40, 0.40, 0), bevel=0.03)
        m.box('hazard', (0.42, 0.05, 0.42), center=(sx * 1.45, 0.025, 0), uv=2.0)
        m.cyl('glow_red', 0.055, 0.055, 0.03, 12, center=(sx * 1.28, 0.32, 0), xf=Rz(math.pi / 2))
        m.cyl('glow_red', 0.055, 0.055, 0.03, 12, center=(sx * 1.28, 0.48, 0), xf=Rz(math.pi / 2))
    for y in (0.32, 0.48):
        m.cyl('glow_red', 0.03, 0.03, 2.56, 8, center=(0, y, 0), xf=Rz(math.pi / 2))
        m.cyl('laser_halo', 0.085, 0.085, 2.56, 12, center=(0, y, 0), xf=Rz(math.pi / 2), caps=False)
    return _root('LaserFence', m)


def obstacle_ramp():
    m = Mesh()
    m.box('steel_wet', (2.8, 0.6, 3.0), center=(0, 0.3, 0), bevel=0.12)
    m.box('hazard', (2.5, 0.02, 2.6), center=(0, 0.605, 0), uv=2.0)
    for sx in (-1, 1): m.box('glow_orange', (0.05, 0.05, 2.8), center=(sx * 1.36, 0.50, 0))
    for sz in (-1, 1): m.box('glow_orange', (2.5, 0.05, 0.05), center=(0, 0.50, sz * 1.46))
    return _root('SteelPlate', m)


def obstacle_cart():
    m = Mesh()
    m.box('wood', (1.5, 0.12, 0.95), center=(0, 0.62, 0), bevel=0.02)
    for sz in (-1, 1): m.box('wood', (1.5, 0.34, 0.05), center=(0, 0.79, sz * 0.45), bevel=0.01)
    for sx in (-1, 1):
        m.box('wood', (0.05, 0.34, 0.95), center=(sx * 0.72, 0.79, 0), bevel=0.01)
        wheel(m, sx * 0.80, 0.28, 0.0, r=0.28, w=0.08, tyre='rubber', hub='wood')
        for sz in (-1, 1):
            m.cyl('steel_dark', 0.025, 0.025, 0.5, 8, center=(sx * 0.7, 0.86, sz * 0.46))
        rod(m, 'steel_dark', (sx * 0.4, 0.62, 0.45), (sx * 0.4, 0.95, 0.82), 0.02)
    rng = np.random.default_rng(5)
    for i in range(16):
        x = rng.uniform(-0.6, 0.6); z = rng.uniform(-0.3, 0.3)
        mat = ('fruit_orange', 'fruit_red', 'fruit_green')[i % 3]
        m.sphere(mat, 0.115, seg=8, rings=5, center=(x, 0.80, z))
    m.box('paint_red', (1.65, 0.04, 1.05), center=(0, 1.07, 0), bevel=0.01)
    m.box('paint_white', (1.65, 0.041, 0.26), center=(0, 1.072, 0), bevel=0.01)
    m.sphere('glow_amber', 0.07, seg=10, rings=7, center=(0, 0.98, -0.52))
    return _root('MarketCart', m)


def obstacle_scooter():
    m = Mesh()
    m.box('paint_blue', (0.46, 0.08, 1.0), center=(0, 0.30, 0.05), bevel=0.03)
    m.box('paint_blue', (0.42, 0.62, 0.34), center=(0, 0.56, -0.56), bevel=0.08, xf=compose(T(0, 0, 0)))
    m.box('paint_blue', (0.38, 0.36, 0.56), center=(0, 0.50, 0.56), bevel=0.08)
    m.box('rubber', (0.32, 0.10, 0.52), center=(0, 0.74, 0.32), bevel=0.04)
    rod(m, 'steel_dark', (0, 0.28, -0.72), (0, 0.98, -0.62), 0.028)
    m.box('steel_dark', (0.72, 0.04, 0.04), center=(0, 1.0, -0.62))
    for sx in (-1, 1):
        m.box('steel_light', (0.07, 0.07, 0.04), center=(sx * 0.30, 1.09, -0.60), bevel=0.01)
        m.box('RunnerPad', (0.10, 0.04, 0.14), center=(sx * 0.35, 1.0, -0.62), bevel=0.01)
    m.sphere('glow_white', 0.08, seg=12, rings=8, center=(0, 0.86, -0.80))
    m.box('glow_red', (0.14, 0.05, 0.04), center=(0, 0.52, 0.86))
    wheel(m, 0, 0.22, -0.78, r=0.22, w=0.10); wheel(m, 0, 0.22, 0.72, r=0.22, w=0.10)
    return _root('Scooter', m)


# ============================================================================ collectibles
def collectible_coin():
    m = Mesh()
    xf = Rx(math.pi / 2)
    m.cyl('coin_face', 0.30, 0.30, 0.07, 28, caps=False, xf=xf, uv=0)
    m.disc('coin_face', 0.30, y=0.0355, up=True, seg=28, xf=xf)
    m.disc('coin_face', 0.30, y=-0.0355, up=False, seg=28, xf=xf)
    return [Node('Coin', mesh=m)]


def collectible_nova():
    m = Mesh()
    gem = [(0, -0.30), (0.17, -0.06), (0.11, 0.17), (0, 0.32), (-0.11, 0.17), (-0.17, -0.06)]
    m.extrude('nova_crystal', gem, 0.10)
    m.extrude('nova_crystal', gem, 0.10, xf=Ry(math.pi / 2))
    m.extrude('nova_crystal', gem, 0.10, xf=Ry(math.pi / 4))
    m.extrude('nova_crystal', gem, 0.10, xf=Ry(-math.pi / 4))
    return [Node('NovaShard', mesh=m)]


OBSTACLE_BUILDERS = dict(
    obstacle_barrier=obstacle_barrier, obstacle_traffic=obstacle_traffic, obstacle_train=obstacle_train,
    obstacle_beam=obstacle_beam, obstacle_trench=obstacle_trench, obstacle_drone=obstacle_drone,
    obstacle_gate=obstacle_gate, obstacle_container=obstacle_container, obstacle_crane=obstacle_crane,
    obstacle_steam=obstacle_steam, obstacle_forklift=obstacle_forklift, obstacle_laser=obstacle_laser,
    obstacle_ramp=obstacle_ramp, obstacle_cart=obstacle_cart, obstacle_scooter=obstacle_scooter)
PLAY_BUILDERS = dict(runner_base=build_runner, collectible_coin=collectible_coin, collectible_nova=collectible_nova, **OBSTACLE_BUILDERS)
