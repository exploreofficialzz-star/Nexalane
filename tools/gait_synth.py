#!/usr/bin/env python3
"""Offline synthesis of the stance part of the gait tables (0.5.0).

The hand-keyed swing curves of tools/gait_reference.py are kept; the STANCE part is solved with a planar two-bone IK so that

  * the foot is planted with heel -> flat -> ball roll-over (no sliding relative to the ground model),
  * the pelvis follows a spring-mass vertical path (high at touch-down and toe-off, lowest ~45 % of stance),
  * the ankle trajectory is continuous with the swing keys.

Run:  python3 tools/gait_synth.py        (prints the table rows that are pasted into gait_reference.py / gait_model.gd)
"""
import math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gait_reference as g
from assetgen import human_rig as rig

D = g.D
T, S_ = rig.THIGH, rig.SHANK
HEEL = (rig.HEEL_Z, -rig.ANKLE_HEIGHT)           # (z, y) of the heel point relative to the ankle (foot frame)
BALL = (rig.TOE_JOINT[0], -rig.ANKLE_HEIGHT)


def rot(p, v):
    """foot-frame (z, y) -> world-aligned (z, y) for a foot pitched toes-down by p."""
    z, y = v
    return (y * math.sin(p) + z * math.cos(p), y * math.cos(p) - z * math.sin(p))


def ik(rel):
    """Planar two-bone IK. rel = (z, y) of the ankle relative to the hip joint. Returns (thigh abs angle fwd, knee flexion)."""
    z, y = rel
    d = min(math.hypot(z, y), (T + S_) * 0.9995)
    cosg = (T * T + S_ * S_ - d * d) / (2 * T * S_)
    knee = math.pi - math.acos(max(-1, min(1, cosg)))
    base = math.atan2(z, -y)                                        # angle of the hip->ankle line from straight down
    cosb = (T * T + d * d - S_ * S_) / (2 * T * d)
    beta = math.acos(max(-1, min(1, cosb)))
    return base + beta, knee


def stance_solution(foot_tab, cad, S, v_gait, y_edge, y_mid, contact_len, keys):
    """IK angles at the requested phases (all < S)."""
    out = []
    # planted contact positions (world z) chosen so the foot is under the hip at ~45 % of stance
    phi_m = 0.45 * S
    z_hip = lambda ph: v_gait * ph / cad
    zc_mid = z_hip(phi_m) + 0.01
    # flat foot centre = heel + 0.105 ; heel contact world z is where the flat foot centre sits under the hip
    jog_like = foot_tab[0] < 0.0
    z_h0 = z_hip(0.5 * S * 0.55) - 0.10 if jog_like else None
    z_b0 = (z_h0 + (rig.TOE_JOINT[0] - rig.HEEL_Z)) if jog_like else zc_mid
    for ph in keys:
        p = g.cyc(foot_tab, ph) * D
        y_pel = y_edge - (y_edge - y_mid) * math.sin(math.pi * ph / S)
        hipj = (z_hip(ph), y_pel - rig.HIP_DROP)
        if p < 0.0 and jog_like:
            zc, off = z_h0, HEEL
        else:
            zc, off = z_b0, BALL
        oz, oy = rot(p, off)
        ankle_w = (zc - oz, 0.0 - oy)
        rel = (ankle_w[0] - hipj[0], ankle_w[1] - hipj[1])
        th, kn = ik(rel)
        out.append((ph, th / D, kn / D, rel))
    return out


# hand keyed SWING keys (absolute thigh angle, knee flexion) for phases after toe-off; None = take the IK stance value
SWING = {
    'JOG': dict(theta={0.40: -4, 0.45: 3, 0.50: 14, 0.55: 27, 0.60: 38, 0.65: 46, 0.70: 51, 0.75: 53, 0.80: 52, 0.85: 48, 0.90: 41, 0.95: 33},
                knee={0.40: 52, 0.45: 76, 0.50: 95, 0.55: 105, 0.60: 105, 0.65: 98, 0.70: 86, 0.75: 72, 0.80: 57, 0.85: 45, 0.90: 36, 0.95: 33}),
    'SPR': dict(theta={0.30: -14, 0.35: -8, 0.40: 2, 0.45: 16, 0.50: 31, 0.55: 45, 0.60: 56, 0.65: 63, 0.70: 66, 0.75: 66, 0.80: 62, 0.85: 56, 0.90: 48, 0.95: 40},
                knee={0.30: 44, 0.35: 76, 0.40: 106, 0.45: 127, 0.50: 134, 0.55: 130, 0.60: 122, 0.65: 110, 0.70: 97, 0.75: 84, 0.80: 70, 0.85: 56, 0.90: 44, 0.95: 38}),
}
CFG = {
    'JOG': dict(foot='FOOT_JOG', cad=(0, 0), S='STANCE_JOG', y_edge=0.925, y_mid=0.872, contact=0.64),
    'SPR': dict(foot='FOOT_SPR', cad=(1, 0), S='STANCE_SPR', y_edge=0.925, y_mid=0.883, contact=0.60),
}


def final_tables():
    out = {}
    for name, c in CFG.items():
        foot = getattr(g, c['foot']); S = getattr(g, c['S']); cad = g.cadence(*c['cad'])
        v = c['contact'] * cad / S
        keys = [k / 20 for k in range(20) if k / 20 <= S + 1e-9]
        sol = {round(ph, 2): (th, kn) for ph, th, kn, _ in stance_solution(foot, cad, S, v, c['y_edge'], c['y_mid'], c['contact'], keys)}
        th_t, kn_t = [], []
        for k in range(20):
            ph = round(k / 20, 2)
            if ph in sol:
                th, kn = sol[ph]
            else:
                th, kn = SWING[name]['theta'][ph], SWING[name]['knee'][ph]
            th_t.append(round(th)); kn_t.append(round(kn))
        out[name] = (th_t, kn_t, v)
    return out


if __name__ == '__main__':
    for name, (th, kn, v) in final_tables().items():
        print(f'# {name}: v_gait = {v:.2f} m/s')
        print(f'THIGH_{name} = {th}')
        print(f'KNEE_{name} = {kn}')
