#!/usr/bin/env python3
"""Reference implementation of the NEXALANE runner gait (0.5.0).

This file is the executable specification of gameplay/runner/gait_model.gd and runner_animator.gd:
every table and formula below exists once here and once in GDScript.  tools/gait_reference.py is used to

  * check the biomechanics numerically (foot clearance, ground contact, vertical COM oscillation, arm / leg phasing),
  * render pose sheets with the real skinned mesh (tools/render_runner_poses.py), and
  * print the "golden" values that tests/qa_harness.gd compares against the GDScript port (run with --golden).

Angles in the tables are DEGREES, everything the functions return is RADIANS / METRES.  Sign conventions are documented in
tools/assetgen/human_rig.py (identity rest rotations, +X rotation swings a hanging limb backwards).
"""
from __future__ import annotations
import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from assetgen import human_rig as rig  # noqa: E402

D = math.pi / 180.0
G = 9.81

# ----------------------------------------------------------------------------------------------- channels
PEL_X, PEL_Z, PEL_PITCH, PEL_YAW, PEL_ROLL = 0, 1, 2, 3, 4
SPN_PITCH, SPN_YAW, SPN_ROLL = 5, 6, 7
CHS_PITCH, CHS_YAW, CHS_ROLL = 8, 9, 10
NCK_PITCH, NCK_YAW, NCK_ROLL = 11, 12, 13
HD_PITCH, HD_YAW, HD_ROLL = 14, 15, 16
ARM = 17            # + side * 8 + (A_*)
A_CLAV_YAW, A_CLAV_ELEV, A_SH_FLEX, A_SH_ABD, A_SH_ROT, A_ELBOW, A_FORE_ROT, A_WRIST = range(8)
LEG = 33            # + side * 6 + (L_*)
L_HIP_FLEX, L_HIP_ABD, L_HIP_ROT, L_KNEE, L_ANKLE, L_TOE = range(6)
N_CH = 45


def arm_ch(side, k): return ARM + side * 8 + k
def leg_ch(side, k): return LEG + side * 6 + k


# ----------------------------------------------------------------------------------------------- tables (deg), 20 keys per gait cycle
# phase 0 = left foot initial contact.  Hip / knee are joint angles relative to the pelvis (flexion positive).
# foot pitch is the ABSOLUTE pitch of the foot (toes-down positive); the ankle angle is derived from it so the foot is
# flat on the ground during mid stance whatever the hip / knee do.
# Thigh angle is stored as the ABSOLUTE forward angle from vertical (theta); hip flexion = theta + pelvis tilt.
THIGH_JOG = [25, 24, 21, 15, 7, 1, -3, -8, -4, 3, 14, 27, 38, 46, 51, 53, 52, 48, 41, 33]
THIGH_SPR = [30, 25, 16, 4, -12, -16, -14, -8, 2, 16, 31, 45, 56, 63, 66, 66, 62, 56, 48, 40]
KNEE_JOG = [35, 43, 48, 49, 45, 44, 42, 37, 52, 76, 95, 105, 105, 98, 86, 72, 57, 45, 36, 33]
KNEE_SPR = [41, 49, 48, 41, 22, 22, 44, 76, 106, 127, 134, 130, 122, 110, 97, 84, 70, 56, 44, 38]
FOOT_JOG = [-14, -5, 0, 0, 2, 12, 28, 46, 58, 48, 30, 14, 4, -4, -9, -12, -14, -15, -15, -15]
FOOT_SPR = [14, 8, 3, 4, 10, 38, 60, 62, 50, 34, 20, 8, -2, -8, -12, -14, -14, -10, -2, 8]

STANCE_JOG, STANCE_SPR = 0.37, 0.25      # fraction of the cycle a foot is on the ground


def lerp(a, b, t): return a + (b - a) * t
def clamp(x, lo, hi): return lo if x < lo else (hi if x > hi else x)
def smoothstep(a, b, x):
    t = clamp((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def cyc(table, ph):
    """Periodic uniform Catmull-Rom sample of a table (phase in cycles)."""
    n = len(table)
    x = (ph - math.floor(ph)) * n
    i = int(math.floor(x)); f = x - i
    p0 = table[(i - 1) % n]; p1 = table[i % n]; p2 = table[(i + 1) % n]; p3 = table[(i + 2) % n]
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * f + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * f * f + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * f * f * f)


# ----------------------------------------------------------------------------------------------- speed -> gait parameters
def intensity(speed):
    """0 = relaxed jog, 1 = full sprint.  Game speeds are 16..31 m/s, far beyond a human, so the legs are run at 'flat out'
    effort over the whole range and only the cadence / lean keep growing."""
    if speed <= 0.0:
        return 0.0
    if speed < 8.0:
        return 0.40 * speed / 8.0
    return clamp(0.40 + 0.60 * (speed - 8.0) / 16.0, 0.0, 1.0)


def overdrive(speed):
    return clamp((speed - 24.0) / 10.0, 0.0, 1.0)


def cadence(u, over):
    """Gait cycles per second (two steps per cycle)."""
    return 1.25 + 1.10 * u + 0.20 * over


def stance_fraction(u):
    return lerp(STANCE_JOG, STANCE_SPR, u)


def new_pose():
    return np.zeros(N_CH)


# ----------------------------------------------------------------------------------------------- the running pose
def run_pose(ph, u, over=0.0, extra_lean=0.0, launch=0.0, turn=0.0):
    """Channels for running.  ph = phase of the LEFT leg in cycles; extra_lean in radians (acceleration lean),
    launch 0..1 = standing-start drive (strong lean, big arms), turn = signed lane-change input -1..1 (+ = left)."""
    c = new_pose()
    S = stance_fraction(u)
    sw = 2.0 * math.pi
    # --- pelvis
    tilt = (3.0 + 4.0 * u) * D + 0.45 * extra_lean + 1.8 * D * math.sin(2.0 * sw * (ph - 0.10))
    c[PEL_PITCH] = tilt
    c[PEL_ROLL] = lerp(2.5, 5.0, u) * D * math.sin(sw * ph)
    c[PEL_YAW] = lerp(4.0, 8.0, u) * D * math.sin(sw * ph)
    c[PEL_X] = lerp(0.012, 0.018, u) * math.sin(sw * ph)
    # --- trunk: world lean = pelvis tilt + spine + chest
    lean = (4.0 + 9.0 * u + 3.0 * over) * D + extra_lean + launch * 16.0 * D
    rest = lean - tilt
    c[SPN_PITCH] = 0.40 * rest
    c[CHS_PITCH] = 0.60 * rest
    twist = (lerp(4.0, 8.0, u) + lerp(5.0, 9.0, u)) * D            # pelvis yaw + counter rotation of the shoulders
    c[SPN_YAW] = -0.40 * twist * math.sin(sw * ph)
    c[CHS_YAW] = -0.60 * twist * math.sin(sw * ph)
    c[SPN_ROLL] = -0.55 * c[PEL_ROLL]
    c[CHS_ROLL] = -0.30 * c[PEL_ROLL]
    # --- head keeps the gaze level and forward
    c[NCK_PITCH] = -0.40 * 0.75 * lean
    c[HD_PITCH] = -0.60 * 0.75 * lean
    yaw_sum = c[PEL_YAW] + c[SPN_YAW] + c[CHS_YAW]
    roll_sum = c[PEL_ROLL] + c[SPN_ROLL] + c[CHS_ROLL]
    c[NCK_YAW] = -0.45 * yaw_sum + 0.30 * turn * 0.35
    c[HD_YAW] = -0.45 * yaw_sum + 0.70 * turn * 0.35
    c[NCK_ROLL] = -0.40 * roll_sum
    c[HD_ROLL] = -0.40 * roll_sum
    # --- arms (opposite to the leg on the same side)
    af = (25.0 + 30.0 * u + 5.0 * over + 10.0 * launch) * D
    ab = (32.0 + 33.0 * u + 5.0 * over + 8.0 * launch) * D
    em = (85.0 + 10.0 * u) * D
    for side in (0, 1):
        q = ph + 0.5 * side
        s = math.sin(sw * (q - 0.02))
        c[arm_ch(side, A_SH_FLEX)] = 0.5 * (af - ab) + 0.5 * (af + ab) * s
        c[arm_ch(side, A_ELBOW)] = em + 14.0 * D * s
        c[arm_ch(side, A_SH_ABD)] = (8.0 + 3.0 * s) * D
        c[arm_ch(side, A_FORE_ROT)] = -8.0 * D
        c[arm_ch(side, A_WRIST)] = 6.0 * D
        c[arm_ch(side, A_CLAV_YAW)] = 2.5 * D * s
        c[arm_ch(side, A_CLAV_ELEV)] = 1.5 * D * abs(s)
    # --- legs
    for side in (0, 1):
        p = ph + 0.5 * side
        hip = lerp(cyc(THIGH_JOG, p), cyc(THIGH_SPR, p), u) * D + tilt
        knee = lerp(cyc(KNEE_JOG, p), cyc(KNEE_SPR, p), u) * D
        foot = lerp(cyc(FOOT_JOG, p), cyc(FOOT_SPR, p), u) * D
        c[leg_ch(side, L_HIP_FLEX)] = hip
        c[leg_ch(side, L_KNEE)] = knee
        c[leg_ch(side, L_ANKLE)] = foot - (tilt - hip + knee)
        c[leg_ch(side, L_HIP_ABD)] = (3.0 + 2.0 * math.sin(sw * p)) * D
        pf = p - math.floor(p)
        w = smoothstep(0.0, 0.03, pf) * (1.0 - smoothstep(S, S + 0.04, pf))
        c[leg_ch(side, L_TOE)] = -clamp(foot, 0.0, 40.0 * D) * w
    return c


# ----------------------------------------------------------------------------------------------- forward kinematics of the legs
def rx(a):
    cs, sn = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, cs, -sn], [0, sn, cs]])


def ry(a):
    cs, sn = math.cos(a), math.sin(a)
    return np.array([[cs, 0, sn], [0, 1, 0], [-sn, 0, cs]])


def rz(a):
    cs, sn = math.cos(a), math.sin(a)
    return np.array([[cs, -sn, 0], [sn, cs, 0], [0, 0, 1]])


def euler_yxz(x, y, z):
    """Godot's Quaternion.from_euler / Basis.from_euler default order: R = Ry * Rx * Rz."""
    return ry(y) @ rx(x) @ rz(z)


def pelvis_basis(c):
    return euler_yxz(c[PEL_PITCH], c[PEL_YAW], c[PEL_ROLL])


def thigh_basis(c, side):
    sgn = 1.0 if side == 0 else -1.0
    return euler_yxz(-c[leg_ch(side, L_HIP_FLEX)], -sgn * c[leg_ch(side, L_HIP_ROT)], sgn * c[leg_ch(side, L_HIP_ABD)])


def leg_chain(c, side, pelvis_pos=(0.0, 0.0, 0.0)):
    """Joint positions of one leg relative to the Hips bone origin (before the pelvis translation is added)."""
    sgn = 1.0 if side == 0 else -1.0
    Bp = pelvis_basis(c)
    hip = Bp @ np.array([sgn * rig.HIP_HALF_WIDTH, -rig.HIP_DROP, 0.0])
    Bt = Bp @ thigh_basis(c, side)
    knee = hip + Bt @ np.array([0.0, -rig.THIGH, 0.0])
    Bs = Bt @ rx(c[leg_ch(side, L_KNEE)])
    ankle = knee + Bs @ np.array([0.0, -rig.SHANK, 0.0])
    Bf = Bs @ rx(c[leg_ch(side, L_ANKLE)])
    heel = ankle + Bf @ np.array([0.0, -rig.ANKLE_HEIGHT, rig.HEEL_Z])
    tz, ty = rig.TOE_JOINT
    toe_joint = ankle + Bf @ np.array([0.0, ty - rig.ANKLE_HEIGHT, tz])
    ball = toe_joint + Bf @ np.array([0.0, -ty, 0.0])
    Bto = Bf @ rx(c[leg_ch(side, L_TOE)])
    tip = toe_joint + Bto @ np.array([0.0, -ty, rig.TOE_TIP_Z])
    return dict(hip=hip, knee=knee, ankle=ankle, heel=heel, ball=ball, tip=tip, toe_joint=toe_joint)


def foot_low(c, side):
    ch = leg_chain(c, side)
    return min(ch['heel'][1], ch['ball'][1], ch['tip'][1])


def support_height(c):
    """Pelvis (Hips bone) height that keeps both feet on / above the ground, plus which foot is the lowest."""
    lo = [foot_low(c, 0), foot_low(c, 1)]
    return max(-lo[0], -lo[1]), (0 if -lo[0] >= -lo[1] else 1)


def run_pelvis_y(ph, u, over, extra_lean, launch, cad):
    """Vertical pelvis path: foot-planted during stance, ballistic arc during the two flight phases."""
    S = stance_fraction(u)
    p = ph - math.floor(ph)
    env = lambda q: support_height(run_pose(q, u, over, extra_lean, launch))[0]
    if p < S or (0.5 <= p < 0.5 + S):
        return env(p)
    a, b = (S, 0.5) if p < 0.5 else (0.5 + S, 1.0)
    tau = (p - a) / (b - a)
    ya, yb = env(a), env(b)
    tf = (b - a) / cad
    amp = G * tf * tf / 8.0
    y = ya + (yb - ya) * tau + 4.0 * amp * tau * (1.0 - tau)
    return max(y, env(p))


# ----------------------------------------------------------------------------------------------- other whole-body poses
def idle_pose(t=0.0):
    """Relaxed standing pose with breathing and a slow weight shift (t in seconds)."""
    c = new_pose()
    br = math.sin(t * 1.7)
    sh = math.sin(t * 0.37)
    c[PEL_PITCH] = 3.0 * D
    c[PEL_ROLL] = 1.2 * D * sh
    c[PEL_YAW] = 1.0 * D * math.sin(t * 0.23)
    c[PEL_X] = 0.010 * sh
    c[SPN_PITCH] = 1.5 * D + 0.5 * D * br
    c[CHS_PITCH] = 1.0 * D + 0.8 * D * br
    c[CHS_ROLL] = -1.0 * D * sh
    c[NCK_PITCH] = -1.0 * D
    c[HD_PITCH] = -2.0 * D + 1.0 * D * math.sin(t * 0.5)
    c[HD_YAW] = 6.0 * D * math.sin(t * 0.31) * math.sin(t * 0.11)
    for side in (0, 1):
        q = 1.0 if side == 0 else -1.0
        c[arm_ch(side, A_SH_FLEX)] = (4.0 + 1.0 * br) * D
        c[arm_ch(side, A_SH_ABD)] = (6.0 + 1.0 * br) * D
        c[arm_ch(side, A_ELBOW)] = (16.0 + 2.0 * math.sin(t * 0.9 + side)) * D
        c[arm_ch(side, A_FORE_ROT)] = 10.0 * D
        c[arm_ch(side, A_WRIST)] = 4.0 * D
        c[arm_ch(side, A_CLAV_ELEV)] = 1.0 * D * br
        c[leg_ch(side, L_HIP_FLEX)] = (3.0 + q * 0.8 * sh) * D
        c[leg_ch(side, L_KNEE)] = (4.0 + q * 0.8 * sh) * D
        c[leg_ch(side, L_HIP_ABD)] = 3.0 * D
        c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - c[leg_ch(side, L_HIP_FLEX)] + c[leg_ch(side, L_KNEE)])   # foot flat
    return c


def ready_pose(t=0.0):
    """Sprinter's 'get set' stance used during the countdown: staggered feet, weight forward, arms ready."""
    c = new_pose()
    br = math.sin(t * 2.6)
    c[PEL_PITCH] = 16.0 * D
    c[PEL_YAW] = 3.0 * D
    c[SPN_PITCH] = 8.0 * D + 0.6 * D * br
    c[CHS_PITCH] = 10.0 * D + 0.8 * D * br
    c[CHS_YAW] = -6.0 * D
    c[NCK_PITCH] = -12.0 * D
    c[HD_PITCH] = -10.0 * D
    c[HD_YAW] = 3.0 * D
    # left foot forward, right foot back
    c[leg_ch(0, L_HIP_FLEX)] = 46.0 * D;  c[leg_ch(0, L_KNEE)] = 62.0 * D
    c[leg_ch(1, L_HIP_FLEX)] = 6.0 * D;   c[leg_ch(1, L_KNEE)] = 30.0 * D
    for side in (0, 1):
        c[leg_ch(side, L_HIP_ABD)] = 3.0 * D
        c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - c[leg_ch(side, L_HIP_FLEX)] + c[leg_ch(side, L_KNEE)])
    # match the heights of both feet by solving the back knee
    lo0 = foot_low(c, 0)
    for _ in range(40):
        lo1 = foot_low(c, 1)
        c[leg_ch(1, L_KNEE)] -= (lo1 - lo0) * 1.6
        c[leg_ch(1, L_ANKLE)] = -(c[PEL_PITCH] - c[leg_ch(1, L_HIP_FLEX)] + c[leg_ch(1, L_KNEE)])
    # arms: right arm forward with the left foot
    c[arm_ch(1, A_SH_FLEX)] = 42.0 * D;  c[arm_ch(1, A_ELBOW)] = 95.0 * D
    c[arm_ch(0, A_SH_FLEX)] = -38.0 * D; c[arm_ch(0, A_ELBOW)] = 85.0 * D
    for side in (0, 1):
        c[arm_ch(side, A_SH_ABD)] = 9.0 * D
        c[arm_ch(side, A_FORE_ROT)] = -6.0 * D
    return c


SLIDE_PELVIS_Y = 0.374       # Hips height that makes the reclined body skim the ground (fitted against the skinned mesh)


def slide_pose(lead=0):
    """Feet-first slide: trunk reclined ~62 deg, legs reaching forward and slightly raised, arms trailing for balance.
    The whole body stays below 0.90 m (the slide hit box is 0.95 m)."""
    c = new_pose()
    c[PEL_PITCH] = -62.0 * D
    c[SPN_PITCH] = -6.0 * D
    c[CHS_PITCH] = -4.0 * D
    c[NCK_PITCH] = 26.0 * D
    c[HD_PITCH] = 12.0 * D
    for side in (0, 1):
        is_lead = side == lead
        thigh = (86.0 if is_lead else 82.0) * D                  # absolute thigh angle from vertical
        knee = (2.0 if is_lead else 9.0) * D
        hip = thigh + c[PEL_PITCH]
        c[leg_ch(side, L_HIP_FLEX)] = hip
        c[leg_ch(side, L_KNEE)] = knee
        c[leg_ch(side, L_ANKLE)] = -22.0 * D - (c[PEL_PITCH] - hip + knee)      # toes up, shoes skimming the ground
        c[leg_ch(side, L_HIP_ABD)] = 5.0 * D
        c[arm_ch(side, A_SH_FLEX)] = -50.0 * D
        c[arm_ch(side, A_SH_ABD)] = 26.0 * D
        c[arm_ch(side, A_ELBOW)] = 24.0 * D
        c[arm_ch(side, A_WRIST)] = -12.0 * D
    return c


AIR_PELVIS_Y = 0.94          # Hips height while airborne (relative to the capsule base)


def air_pose(a, lead=0):
    """Hurdle style leap.  a = 0..1 progress through the flight, lead = side of the leading leg."""
    c = new_pose()
    take = 1.0 - smoothstep(0.0, 0.22, a)                  # push-off extension
    land = smoothstep(0.58, 0.92, a)                       # reaching for the ground
    mid = max(1.0 - take - land, 0.0)
    c[PEL_PITCH] = (10.0 * take + 14.0 * mid + 6.0 * land) * D
    c[SPN_PITCH] = (6.0 * take + 10.0 * mid + 2.0 * land) * D
    c[CHS_PITCH] = (6.0 * take + 12.0 * mid + 2.0 * land) * D
    c[NCK_PITCH] = -12.0 * D
    c[HD_PITCH] = -10.0 * D
    for side in (0, 1):
        is_lead = side == lead
        if is_lead:
            hip = -8.0 * take + 72.0 * mid + 38.0 * land + 60.0 * take
            knee = 12.0 * take + 38.0 * mid + 22.0 * land + 70.0 * take
            foot = 34.0 * take - 4.0 * mid + 22.0 * land
            shoulder = 20.0 * take - 10.0 * mid + 30.0 * land
        else:
            hip = -14.0 * take + 14.0 * mid + 22.0 * land
            knee = 24.0 * take + 112.0 * mid + 50.0 * land
            foot = 34.0 * take + 18.0 * mid + 22.0 * land
            shoulder = 62.0 * take + 48.0 * mid + 30.0 * land
        c[leg_ch(side, L_HIP_FLEX)] = hip * D
        c[leg_ch(side, L_KNEE)] = knee * D
        c[leg_ch(side, L_ANKLE)] = foot * D - (c[PEL_PITCH] - hip * D + knee * D)
        c[leg_ch(side, L_HIP_ABD)] = (4.0 + 6.0 * mid) * D
        c[arm_ch(side, A_SH_FLEX)] = shoulder * D
        c[arm_ch(side, A_SH_ABD)] = (14.0 + 22.0 * mid) * D
        c[arm_ch(side, A_ELBOW)] = (80.0 * take + 70.0 * mid + 60.0 * land) * D
    return c


def land_pose():
    """Impact absorption: deep hip / knee / ankle flexion, trunk folded forward, arms thrown forward."""
    c = new_pose()
    c[PEL_PITCH] = 26.0 * D
    c[SPN_PITCH] = 10.0 * D
    c[CHS_PITCH] = 10.0 * D
    c[NCK_PITCH] = -18.0 * D
    c[HD_PITCH] = -14.0 * D
    for side in (0, 1):
        hip, knee = 58.0 * D, 78.0 * D
        c[leg_ch(side, L_HIP_FLEX)] = hip
        c[leg_ch(side, L_KNEE)] = knee
        c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
        c[leg_ch(side, L_HIP_ABD)] = 7.0 * D
        c[arm_ch(side, A_SH_FLEX)] = 36.0 * D
        c[arm_ch(side, A_SH_ABD)] = 22.0 * D
        c[arm_ch(side, A_ELBOW)] = 62.0 * D
    return c


def hit_recoil_pose():
    """The instant of impact: upper body snaps back, arms fly out, legs brace."""
    c = new_pose()
    c[PEL_PITCH] = 4.0 * D
    c[SPN_PITCH] = -8.0 * D
    c[CHS_PITCH] = -10.0 * D
    c[NCK_PITCH] = 12.0 * D
    c[HD_PITCH] = 10.0 * D
    for side in (0, 1):
        hip, knee = 24.0 * D, 34.0 * D
        c[leg_ch(side, L_HIP_FLEX)] = hip
        c[leg_ch(side, L_KNEE)] = knee
        c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
        c[leg_ch(side, L_HIP_ABD)] = 10.0 * D
        c[arm_ch(side, A_SH_FLEX)] = 78.0 * D
        c[arm_ch(side, A_SH_ABD)] = 52.0 * D
        c[arm_ch(side, A_ELBOW)] = 34.0 * D
        c[arm_ch(side, A_WRIST)] = -20.0 * D
    return c


def hit_down_pose():
    """Winded crouch after the stumble: knees bent, trunk folded, head down, hands towards the knees."""
    c = new_pose()
    c[PEL_PITCH] = 34.0 * D
    c[SPN_PITCH] = 22.0 * D
    c[CHS_PITCH] = 20.0 * D
    c[NCK_PITCH] = -6.0 * D
    c[HD_PITCH] = 18.0 * D
    for side in (0, 1):
        hip, knee = 78.0 * D, 96.0 * D
        c[leg_ch(side, L_HIP_FLEX)] = hip
        c[leg_ch(side, L_KNEE)] = knee
        c[leg_ch(side, L_ANKLE)] = -(c[PEL_PITCH] - hip + knee)
        c[leg_ch(side, L_HIP_ABD)] = 12.0 * D
        c[arm_ch(side, A_SH_FLEX)] = 40.0 * D
        c[arm_ch(side, A_SH_ABD)] = 14.0 * D
        c[arm_ch(side, A_ELBOW)] = 34.0 * D
    return c


# ----------------------------------------------------------------------------------------------- channels -> bones
def bone_rotations(c):
    """Local rotation matrix of every bone (identity rest) for a channel set."""
    R = [np.eye(3) for _ in rig.NAMES]
    I = rig.IDX
    R[I['Hips']] = euler_yxz(c[PEL_PITCH], c[PEL_YAW], c[PEL_ROLL])
    R[I['Spine']] = euler_yxz(c[SPN_PITCH], c[SPN_YAW], c[SPN_ROLL])
    R[I['Chest']] = euler_yxz(c[CHS_PITCH], c[CHS_YAW], c[CHS_ROLL])
    R[I['Neck']] = euler_yxz(c[NCK_PITCH], c[NCK_YAW], c[NCK_ROLL])
    R[I['Head']] = euler_yxz(c[HD_PITCH], c[HD_YAW], c[HD_ROLL])
    for side, nm in ((0, 'Left'), (1, 'Right')):
        sgn = 1.0 if side == 0 else -1.0
        R[I[nm + 'Shoulder']] = euler_yxz(0.0, -sgn * c[arm_ch(side, A_CLAV_YAW)], sgn * c[arm_ch(side, A_CLAV_ELEV)])
        R[I[nm + 'UpperArm']] = euler_yxz(-c[arm_ch(side, A_SH_FLEX)], -sgn * c[arm_ch(side, A_SH_ROT)], sgn * c[arm_ch(side, A_SH_ABD)])
        R[I[nm + 'LowerArm']] = euler_yxz(-c[arm_ch(side, A_ELBOW)], -sgn * c[arm_ch(side, A_FORE_ROT)], 0.0)
        R[I[nm + 'Hand']] = euler_yxz(-c[arm_ch(side, A_WRIST)], 0.0, 0.0)
        R[I[nm + 'UpperLeg']] = thigh_basis(c, side)
        R[I[nm + 'LowerLeg']] = rx(c[leg_ch(side, L_KNEE)])
        R[I[nm + 'Foot']] = rx(c[leg_ch(side, L_ANKLE)])
        R[I[nm + 'Toes']] = rx(c[leg_ch(side, L_TOE)])
    return R


def pose_world(c, pel_y, secondary=None):
    """Forward kinematics of the whole skeleton: returns (world rotation, world position) per bone.
    secondary: optional dict bone name -> extra local rotation matrix (hair / pack / hood springs)."""
    R = bone_rotations(c)
    if secondary:
        for n, m in secondary.items():
            R[rig.IDX[n]] = m
    wr = [None] * len(rig.BONES); wp = [None] * len(rig.BONES)
    for i, (n, parent, pos) in enumerate(rig.BONES):
        off = np.array(rig.local_offset(i))
        if parent < 0:
            off = off + np.array([c[PEL_X], pel_y - pos[1], c[PEL_Z]])
            wr[i] = R[i]; wp[i] = off
        else:
            wr[i] = wr[parent] @ R[i]; wp[i] = wp[parent] + wr[parent] @ off
    return wr, wp


# ----------------------------------------------------------------------------------------------- analysis
def analyse(speed, steps=400):
    u = intensity(speed); over = overdrive(speed); cad = cadence(u, over)
    ys, envs, who, lows, heel_hi = [], [], [], [], []
    clear = 1e9
    for k in range(steps):
        ph = k / steps
        c = run_pose(ph, u, over)
        y = run_pelvis_y(ph, u, over, 0.0, 0.0, cad)
        env, foot = support_height(c)
        ys.append(y); envs.append(env); who.append(foot)
        lo = [foot_low(c, 0) + y, foot_low(c, 1) + y]
        lows.append(lo)
        clear = min(clear, min(lo))
    ys = np.array(ys); lows = np.array(lows)
    return dict(u=u, over=over, cadence=cad, stance=stance_fraction(u), y=ys, env=np.array(envs), who=np.array(who), lows=lows,
                p2p=float(ys.max() - ys.min()), min_foot=float(clear))


def golden():
    """Values the in-engine QA compares with the GDScript port (see tests/qa_harness.gd)."""
    out = []
    for (ph, spd) in ((0.0, 16.0), (0.31, 16.0), (0.74, 22.0), (0.52, 31.0)):
        u = intensity(spd); over = overdrive(spd); cad = cadence(u, over)
        c = run_pose(ph, u, over)
        out.append(dict(phase=ph, speed=spd, u=u, cadence=cad,
                        hipL=c[leg_ch(0, L_HIP_FLEX)], kneeL=c[leg_ch(0, L_KNEE)], ankleL=c[leg_ch(0, L_ANKLE)],
                        shoulderL=c[arm_ch(0, A_SH_FLEX)], elbowR=c[arm_ch(1, A_ELBOW)], pelvisY=run_pelvis_y(ph, u, over, 0.0, 0.0, cad)))
    return out


if __name__ == '__main__':
    if '--golden' in sys.argv:
        for g in golden():
            print({k: round(v, 5) for k, v in g.items()})
        sys.exit(0)
    for spd in (4.0, 8.0, 16.0, 24.0, 31.0):
        a = analyse(spd)
        print(f"speed {spd:5.1f}  u={a['u']:.2f} cad={a['cadence']:.2f} c/s ({a['cadence'] * 120:.0f} steps/min) stance={a['stance']:.2f}  "
              f"pelvis p2p={a['p2p'] * 100:.1f} cm  min={a['y'].min():.3f} max={a['y'].max():.3f}  lowest foot point={a['min_foot'] * 100:+.1f} cm")
