#!/usr/bin/env python3
"""Side-view stick-figure sheet of the run cycle (for eyeballing the gait).  Usage: plot_gait_sheet.py out.png"""
import sys, math
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gait_reference as g
from assetgen import human_rig as rig
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

I = rig.IDX
CHAINS = [('Hips', 'Spine', 'Chest', 'Neck', 'Head'),
          ('Chest', 'LeftShoulder', 'LeftUpperArm', 'LeftLowerArm', 'LeftHand'),
          ('Chest', 'RightShoulder', 'RightUpperArm', 'RightLowerArm', 'RightHand'),
          ('Hips', 'LeftUpperLeg', 'LeftLowerLeg', 'LeftFoot', 'LeftToes'),
          ('Hips', 'RightUpperLeg', 'RightLowerLeg', 'RightFoot', 'RightToes')]


def draw(ax, c, pel_y, off, color_l='tab:red', color_r='tab:blue'):
    wr, wp = g.pose_world(c, pel_y)
    for ch in CHAINS:
        pts = [wp[I[n]] for n in ch]
        col = color_l if ('Left' in ch[1]) else (color_r if 'Right' in ch[1] else 'k')
        ax.plot([p[2] + off for p in pts], [p[1] for p in pts], '-o', color=col, ms=2.5, lw=1.6)
    # head top, hand tips, toe tips
    head = wp[I['Head']] + wr[I['Head']] @ np.array([0, 0.27, 0]); neck = wp[I['Head']]
    ax.plot([neck[2] + off, head[2] + off], [neck[1], head[1]], 'k-', lw=3)
    for nm, col in (('Left', color_l), ('Right', color_r)):
        side = 0 if nm == 'Left' else 1
        h = wp[I[nm + 'Hand']]; tip = h + wr[I[nm + 'Hand']] @ np.array([0, -0.2, 0])
        ax.plot([h[2] + off, tip[2] + off], [h[1], tip[1]], '-', color=col, lw=2.5)
        ch = g.leg_chain(c, side)
        base = wp[I['Hips']]
        # foot sole polyline heel -> ball -> tip using hip-relative points
        rel = np.array([c[g.PEL_X], 0.0, c[g.PEL_Z]])
        pts = [base + ch['heel'], base + ch['ball'], base + ch['tip']]
        ax.plot([p[2] + off for p in pts], [p[1] for p in pts], '-', color=col, lw=2.5)


def sheet(path, speeds=(8.0, 16.0, 30.0), n=10):
    fig, axes = plt.subplots(len(speeds), 1, figsize=(15, 3.6 * len(speeds)))
    for ax, spd in zip(axes, speeds):
        u = g.intensity(spd); over = g.overdrive(spd); cad = g.cadence(u, over)
        for k in range(n):
            ph = k / n
            c = g.run_pose(ph, u, over)
            y = g.run_pelvis_y(ph, u, over, 0.0, 0.0, cad)
            draw(ax, c, y, k * 1.0)
            ax.text(k * 1.0, -0.12, f'{ph:.1f}', ha='center', fontsize=8)
        ax.axhline(0, color='gray', lw=1)
        ax.set_aspect('equal'); ax.set_xlim(-0.6, n * 1.0 - 0.2); ax.set_ylim(-0.2, 1.95)
        ax.set_title(f'speed {spd:.0f} m/s -> u={u:.2f}  cadence {cad:.2f} c/s  (red = left, blue = right, runner faces right)', fontsize=9)
        ax.axis('off')
    fig.tight_layout(); fig.savefig(path, dpi=80)


if __name__ == '__main__':
    sheet(sys.argv[1] if len(sys.argv) > 1 else '/tmp/gait_sheet.png')
