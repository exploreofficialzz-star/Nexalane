"""Skeleton of the NEXALANE cartoon runner (0.6.0).

Same 25 bone names, order and conventions as human_rig.py (so RunnerAnimator can bind it unchanged), but chunky "mobile
runner" proportions: a big round head, a wide hooded torso, thick short-ish limbs and oversized sneakers - a character that
fills the screen like the classic 3-lane runners.

Conventions: metres, +Y up, the runner faces +Z, so the character's LEFT side is +X.  Every bone has an IDENTITY rest
rotation (all joints are pure translations):

    rotation about +X : pitch.  For a limb that hangs down, +X swings the end BACKWARDS (-Z); for the trunk +X leans FORWARD.
    rotation about +Y : yaw.    +Y turns the character to its left (+X).
    rotation about +Z : roll.   +Z tips the top of the body to the right (-X).

The same numbers are mirrored in gameplay/runner/toon_gait.gd (THIGH, SHANK, ...) - change both together.
"""
from __future__ import annotations

HEIGHT = 1.93            # standing height incl. cap (m); the physics hit box is 1.85 m tall (a little generous on purpose)

# name, parent, world rest position of the joint (x, y, z)
BONES = [
    ('Hips',          -1, (0.000, 0.880, 0.000)),
    ('Spine',          0, (0.000, 1.000, 0.000)),
    ('Chest',          1, (0.000, 1.170, 0.000)),
    ('Neck',           2, (0.000, 1.430, 0.000)),
    ('Head',           3, (0.000, 1.520, 0.000)),
    ('LeftShoulder',   2, (0.070, 1.380, 0.000)),
    ('LeftUpperArm',   5, (0.300, 1.360, 0.000)),
    ('LeftLowerArm',   6, (0.330, 1.060, 0.000)),
    ('LeftHand',       7, (0.345, 0.780, 0.000)),
    ('RightShoulder',  2, (-0.070, 1.380, 0.000)),
    ('RightUpperArm',  9, (-0.300, 1.360, 0.000)),
    ('RightLowerArm', 10, (-0.330, 1.060, 0.000)),
    ('RightHand',     11, (-0.345, 0.780, 0.000)),
    ('LeftUpperLeg',   0, (0.115, 0.870, 0.000)),
    ('LeftLowerLeg',  13, (0.115, 0.470, 0.000)),
    ('LeftFoot',      14, (0.115, 0.110, 0.000)),
    ('LeftToes',      15, (0.115, 0.050, 0.140)),
    ('RightUpperLeg',  0, (-0.115, 0.870, 0.000)),
    ('RightLowerLeg', 17, (-0.115, 0.470, 0.000)),
    ('RightFoot',     18, (-0.115, 0.110, 0.000)),
    ('RightToes',     19, (-0.115, 0.050, 0.140)),
    # secondary motion (spring driven in the animator, not part of the gait)
    ('Pack',           2, (0.000, 1.220, -0.170)),
    ('Hood',           2, (0.000, 1.420, -0.130)),
    ('HairFront',      4, (0.000, 1.700, 0.170)),
    ('HairBack',       4, (0.000, 1.720, -0.200)),
]
NAMES = [b[0] for b in BONES]
IDX = {n: i for i, n in enumerate(NAMES)}
CORE_BONES = 21

THIGH = 0.400
SHANK = 0.360
HIP_HALF_WIDTH = 0.115
HIP_DROP = 0.010                 # hip joint sits 1 cm below the Hips bone origin
ANKLE_HEIGHT = 0.110             # ankle joint above the sole
TOE_JOINT = (0.140, 0.050)       # (z forward of the ankle, y above the sole) of the ball-of-foot joint
HEEL_Z = -0.090                  # heel back from the ankle
TOE_TIP_Z = 0.120                # toe tip beyond the toe joint


def local_offset(i: int):
    """Translation of bone i relative to its parent (what the glTF node stores)."""
    _, parent, pos = BONES[i]
    if parent < 0:
        return tuple(pos)
    pp = BONES[parent][2]
    return (pos[0] - pp[0], pos[1] - pp[1], pos[2] - pp[2])


def self_check():
    assert [b[0] for b in BONES][:3] == ['Hips', 'Spine', 'Chest']
    for i, (n, p, _) in enumerate(BONES):
        assert p < i, f'{n}: parent must come before the child'
    lh = BONES[IDX['LeftUpperLeg']][2]; lk = BONES[IDX['LeftLowerLeg']][2]; la = BONES[IDX['LeftFoot']][2]
    assert abs((lh[1] - lk[1]) - THIGH) < 1e-6, 'thigh length constant out of sync'
    assert abs((lk[1] - la[1]) - SHANK) < 1e-6, 'shank length constant out of sync'
    assert abs(la[1] - ANKLE_HEIGHT) < 1e-6
    assert abs(BONES[IDX['Hips']][2][1] - BONES[IDX['LeftUpperLeg']][2][1] - HIP_DROP) < 1e-6
    assert abs(BONES[IDX['LeftUpperLeg']][2][0] - HIP_HALF_WIDTH) < 1e-6
    for part in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand', 'UpperLeg', 'LowerLeg', 'Foot', 'Toes'):
        a = BONES[IDX['Left' + part]][2]; b = BONES[IDX['Right' + part]][2]
        assert abs(a[0] + b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9 and abs(a[2] - b[2]) < 1e-9, f'{part} is not mirrored'
    lt = BONES[IDX['LeftToes']][2]
    assert abs((lt[2] - la[2]) - TOE_JOINT[0]) < 1e-6 and abs(lt[1] - TOE_JOINT[1]) < 1e-6


self_check()
