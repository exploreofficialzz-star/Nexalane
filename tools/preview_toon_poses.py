#!/usr/bin/env python3
"""Renders the cartoon runner (assets/models/runner_base.glb) in the poses of gameplay/runner/toon_gait.gd.

There is no Godot in the build container, so toon_gait.gd is executed through the small GDScript -> Python translator of
tools/check_gait_port.py (toon_gait.gd is written in that subset on purpose) and the resulting channels are applied to the
skeleton with the same forward kinematics RunnerAnimator uses.  What you see in docs/previews/toon_pose_sheet.png is therefore
what the animator will produce in the game (apart from the engine's lighting).

    python tools/preview_toon_poses.py            writes docs/previews/toon_pose_sheet.png
    python tools/preview_toon_poses.py --check    only runs the numeric sanity checks (feet never below the floor, ...)
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gait_reference as g                       # noqa: E402  (channel layout + bone_rotations, rig independent)
import check_gait_port as T                      # noqa: E402  (the GDScript -> Python translator)
from assetgen import toon_preview as tp          # noqa: E402
from assetgen import toon_rig as rig             # noqa: E402

GLB = ROOT / 'assets' / 'models' / 'runner_base.glb'
TINT = (1.0, 0.40, 0.09)                         # default accent (orange), linear


def load_gait():
    ns = dict(T.SHIMS)
    ns.update(cos=math.cos, sqrt=math.sqrt, pow=pow, exp=math.exp, atan2=math.atan2)
    code = T.translate((ROOT / 'gameplay' / 'runner' / 'toon_gait.gd').read_text())
    exec(compile(code, 'toon_gait.gd', 'exec'), ns)
    return ns


def pose_world(c, pel_y):
    R = g.bone_rotations(c)
    wr = [None] * len(rig.BONES); wp = [None] * len(rig.BONES)
    for i, (n, parent, pos) in enumerate(rig.BONES):
        off = np.array(rig.local_offset(i))
        if parent < 0:
            off = off + np.array([c[g.PEL_X], pel_y - pos[1], c[g.PEL_Z]])
            wr[i] = R[i]; wp[i] = off
        else:
            wr[i] = wr[parent] @ R[i]; wp[i] = wp[parent] + wr[parent] @ off
    return wr, wp


def calibrate(gd):
    """Back foot of the 'get set' stance on the floor: find the knee angle that equalises both foot heights."""
    lo, hi = 0.0, 120.0
    for _ in range(50):
        mid = 0.5 * (lo + hi)
        gd['READY_KNEE_BACK_DEG'] = mid
        c = gd['ready_pose'](0.0)
        d = gd['foot_low'](c, 1) - gd['foot_low'](c, 0)
        if d > 0: hi = mid          # back foot floats above the front foot -> straighten the knee (more flexion lifts the foot)
        else: lo = mid
    return 0.5 * (lo + hi)


def sanity(gd):
    """Numeric checks that do not need a renderer."""
    problems = []
    worst_sink = 0.0
    lows = []
    for spd in (8.0, 16.0, 24.0, 31.0):
        u = gd['intensity'](spd); over = gd['overdrive'](spd); cad = gd['cadence'](u, over)
        ys = []
        for i in range(64):
            ph = i / 64.0
            c = gd['run_pose'](ph, u, over, 0.0, 0.0, 0.0)
            y = gd['run_pelvis_y'](ph, u, over, 0.0, 0.0, cad)
            ys.append(y)
            low = min(gd['foot_low'](c, 0), gd['foot_low'](c, 1)) + y
            worst_sink = min(worst_sink, low)
            lows.append(low)
            if not (0.55 < y < 1.05): problems.append(f'pelvis height {y:.3f} out of range at {spd} m/s phase {ph:.2f}')
        if max(ys) - min(ys) < 0.03: problems.append(f'no bounce at {spd} m/s')
        if max(ys) - min(ys) > 0.30: problems.append(f'bounce too violent at {spd} m/s ({max(ys) - min(ys):.2f} m)')
    if worst_sink < -0.004: problems.append(f'feet sink {worst_sink:.3f} m into the floor')
    return problems, worst_sink


def render_pose(sk, c, y, view, size=(240, 330), ssaa=2, bg=(50, 58, 94), center=None):
    wr, wp = pose_world(c, y)
    prims = tp.posed(sk, wr, wp)
    yaw, pitch = view
    return tp.render(prims, size=size, yaw=yaw, pitch=pitch, center=center or (0.0, 0.95, 0.0), fit=1.18, ssaa=ssaa, bg=bg, tint=TINT)


def main():
    gd = load_gait()
    knee = calibrate(gd)
    declared = float((ROOT / 'gameplay' / 'runner' / 'toon_gait.gd').read_text().split('READY_KNEE_BACK_DEG: float = ')[1].split('\n')[0])
    print(f'READY_KNEE_BACK_DEG that puts the back foot on the floor: {knee:.3f} (toon_gait.gd declares {declared:.3f})')
    if abs(knee - declared) > 0.05:
        print('  PROBLEM  READY_KNEE_BACK_DEG in toon_gait.gd is out of date'); return 1
    problems, sink = sanity(gd)
    print(f'worst foot sink {sink * 100:.2f} cm')
    for p in problems[:10]: print('  PROBLEM', p)
    if '--check' in sys.argv:
        return 1 if problems else 0
    gd2 = load_gait()
    sk = tp.load(str(GLB))
    cells = []

    def cell(label, c, y, view, size=(240, 330), center=None):
        im = render_pose(sk, c, y, view, size, center=center)
        d = ImageDraw.Draw(im); d.text((6, 4), label, fill=(240, 240, 250))
        cells.append(im)

    # run cycle, side view, 16 m/s
    u = gd2['intensity'](16.0); over = gd2['overdrive'](16.0); cad = gd2['cadence'](u, over)
    for i in range(8):
        ph = i / 8.0
        cell(f'run 16 m/s  {ph:.3f}', gd2['run_pose'](ph, u, over, 0.0, 0.0, 0.0), gd2['run_pelvis_y'](ph, u, over, 0.0, 0.0, cad), (90, 3))
    # run cycle as the game camera sees it (behind, slightly above), 28 m/s
    u = gd2['intensity'](28.0); over = gd2['overdrive'](28.0); cad = gd2['cadence'](u, over)
    for i in range(8):
        ph = i / 8.0
        cell(f'game cam 28 m/s  {ph:.3f}', gd2['run_pose'](ph, u, over, 0.0, 0.0, 0.0), gd2['run_pelvis_y'](ph, u, over, 0.0, 0.0, cad), (180, 13))
    # jump, slide, landing, hit
    for a in (0.08, 0.30, 0.55, 0.85):
        c = gd2['air_pose'](a, 0)
        cell(f'jump {a:.2f}', c, gd2['AIR_PELVIS_Y'], (90, 3))
    c = gd2['land_pose'](); cell('landing', c, gd2['support_height'](c), (90, 3))
    c = gd2['slide_pose'](0); cell('slide', c, gd2['SLIDE_PELVIS_Y'], (90, 3), (240, 330), center=(0.0, 0.62, 0.0))
    c = gd2['hit_recoil_pose'](); cell('hit recoil', c, gd2['support_height'](c), (90, 3))
    c = gd2['hit_down_pose'](); cell('hit crouch', c, gd2['support_height'](c), (90, 3))
    # menu hero, ready stance, idle, front view of the run
    c = gd2['idle_pose'](0.0); cell('menu idle (hero view)', c, gd2['support_height'](c), (25, 8))
    c = gd2['idle_pose'](1.3); cell('idle (back)', c, gd2['support_height'](c), (180, 8))
    c = gd2['ready_pose'](0.0); cell('get set', c, gd2['support_height'](c), (60, 5))
    u = gd2['intensity'](22.0); over = gd2['overdrive'](22.0); cad = gd2['cadence'](u, over)
    for ph in (0.0, 0.5):
        cell(f'run front {ph:.1f}', gd2['run_pose'](ph, u, over, 0.0, 0.0, 0.0), gd2['run_pelvis_y'](ph, u, over, 0.0, 0.0, cad), (20, 6))
    cols = 8
    rows = math.ceil(len(cells) / cols)
    w, h = cells[0].size
    sheet = Image.new('RGB', (cols * w, rows * h), (30, 34, 52))
    for i, im in enumerate(cells):
        sheet.paste(im, ((i % cols) * w, (i // cols) * h))
    out = ROOT / 'docs' / 'previews' / 'toon_pose_sheet.png'
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    print('wrote', out, sheet.size)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
