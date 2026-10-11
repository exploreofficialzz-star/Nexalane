#!/usr/bin/env python3
"""Renders docs/previews/runner_pose_sheet.png from the SHIPPED assets/models/runner_base.glb and the Python gait reference
(tools/gait_reference.py), i.e. it shows exactly what GaitModel / RunnerAnimator drive in game.  It also refreshes the
runner tile of docs/previews/models_overview.png.

    python tools/render_runner_poses.py
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gait_reference as g  # noqa: E402
from assetgen import skin_preview as sp  # noqa: E402

CELL = (260, 380)


def render_pose(sk, c, pel_y, yaw, pitch=6, center=(0.0, 0.92, 0.0), fit=0.52, size=CELL, caption=None):
    wr, wp = g.pose_world(c, pel_y)
    im = sp.render_posed(sk, wr, wp, size=size, yaw=yaw, pitch=pitch, center=center, fit=fit)
    if caption:
        ImageDraw.Draw(im).text((7, 6), caption, fill=(235, 240, 255))
    return im


def run_frame(sk, k, n, speed, yaw, pitch=6, caption=None, fit=0.52, center=(0.0, 0.92, 0.0)):
    u = g.intensity(speed); over = g.overdrive(speed); cad = g.cadence(u, over)
    ph = k / n
    c = g.run_pose(ph, u, over)
    y = g.run_pelvis_y(ph, u, over, 0.0, 0.0, cad)
    return render_pose(sk, c, y, yaw, pitch, center, fit, caption=caption)


def sheet(sk, path):
    cols = 6
    rows = []
    n = 6
    rows.append([run_frame(sk, k, n, 16.0, 90, caption=f'run 16 m/s  phase {k / n:.2f}') for k in range(n)])
    rows.append([run_frame(sk, k, n, 26.0, -150, pitch=14, caption=f'run 26 m/s (game cam) {k / n:.2f}', fit=0.56, center=(0.0, 0.95, 0.0)) for k in range(n)])
    specials = []
    for a, lead in ((0.10, 0), (0.45, 0), (0.88, 0)):
        specials.append(render_pose(sk, g.air_pose(a, lead), g.AIR_PELVIS_Y, 90, caption=f'jump  {a:.2f}'))
    land = g.land_pose()
    specials.append(render_pose(sk, land, g.support_height(land)[0], 90, caption='landing absorb'))
    specials.append(render_pose(sk, g.slide_pose(0), g.SLIDE_PELVIS_Y, 90, fit=0.62, center=(0.0, 0.62, 0.0), caption='slide'))
    rdy = g.ready_pose(0.0)
    specials.append(render_pose(sk, rdy, g.support_height(rdy)[0], 90, caption='countdown "get set"'))
    rows.append(specials)
    extra = []
    rec = g.hit_recoil_pose(); dn = g.hit_down_pose()
    extra.append(render_pose(sk, rec, g.support_height(rec)[0], 90, caption='hit: recoil'))
    extra.append(render_pose(sk, dn, g.support_height(dn)[0], 90, fit=0.62, center=(0.0, 0.62, 0.0), caption='hit: winded crouch'))
    idle = g.idle_pose(1.0)
    iy = g.support_height(idle)[0]
    extra.append(render_pose(sk, idle, iy, 28, pitch=4, caption='menu idle (hero view)'))
    extra.append(render_pose(sk, idle, iy, -150, pitch=6, caption='idle (back)'))
    for ph, spd in ((0.0, 16.0), (0.5, 16.0)):
        u = g.intensity(spd); over = g.overdrive(spd)
        c = g.run_pose(ph, u, over)
        extra.append(render_pose(sk, c, g.run_pelvis_y(ph, u, over, 0.0, 0.0, g.cadence(u, over)), 28, pitch=4, caption=f'run, front view {ph:.1f}'))
    rows.append(extra)
    W, H = cols * CELL[0], len(rows) * CELL[1]
    out = Image.new('RGB', (W, H), (18, 21, 30))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            out.paste(im, (c * CELL[0], r * CELL[1]))
    out.save(path)
    return out


def overview_tile(sk, path):
    p = Path(path)
    if not p.exists():
        return
    base = Image.open(p).convert('RGB')
    cell = base.width // 4
    c = g.idle_pose(0.0)
    tile = render_pose(sk, c, g.support_height(c)[0], 32, pitch=5, center=(0.0, 0.93, 0.0), fit=0.66, size=(cell, cell), caption='runner_base')
    base.paste(tile, (0, 0))
    base.save(p)


if __name__ == '__main__':
    sk = sp.load_skinned(str(ROOT / 'assets' / 'models' / 'runner_base.glb'))
    out = sheet(sk, ROOT / 'docs' / 'previews' / 'runner_pose_sheet.png')
    print('wrote runner_pose_sheet.png', out.size)
    overview_tile(sk, ROOT / 'docs' / 'previews' / 'models_overview.png')
    print('refreshed models_overview.png runner tile')
