"""Skeleton of the NEXALANE runner (0.5.0): a 25-bone humanoid, bone names follow Godot's humanoid profile.

Conventions (identical to the rest of the asset pipeline): metres, +Y up, the runner faces +Z, so the character's
LEFT side is +X.  Every bone has an IDENTITY rest rotation (all joints are pure translations), which means a bone's local
axes equal the world axes in the rest pose:

    rotation about +X  : pitch.  For a limb that hangs down, +X swings the end BACKWARDS (-Z); for the trunk +X leans FORWARD.
    rotation about +Y  : yaw.    +Y turns the character to its left (+X).
    rotation about +Z  : roll.   +Z tips the top of the body to the right (-X).

The same numbers are mirrored in gameplay/runner/runner_animator.gd (constants LEG_*, FOOT_*, ...) and checked by
tests/qa_harness.gd, so change both together.
"""
from __future__ import annotations

HEIGHT = 1.82            # standing height, head top (m)

# --------------------------------------------------------------------------------------------- bones
# name, parent, world rest position of the joint (x, y, z)
BONES = [
    ('Hips',          -1, (0.000, 0.960, 0.000)),
    ('Spine',          0, (0.000, 1.080, 0.000)),
    ('Chest',          1, (0.000, 1.250, 0.000)),
    ('Neck',           2, (0.000, 1.460, 0.005)),
    ('Head',           3, (0.000, 1.550, 0.005)),
    ('LeftShoulder',   2, (0.035, 1.430, 0.020)),
    ('LeftUpperArm',   5, (0.190, 1.430, 0.000)),
    ('LeftLowerArm',   6, (0.205, 1.110, 0.000)),
    ('LeftHand',       7, (0.215, 0.840, 0.000)),
    ('RightShoulder',  2, (-0.035, 1.430, 0.020)),
    ('RightUpperArm',  9, (-0.190, 1.430, 0.000)),
    ('RightLowerArm', 10, (-0.205, 1.110, 0.000)),
    ('RightHand',     11, (-0.215, 0.840, 0.000)),
    ('LeftUpperLeg',   0, (0.095, 0.950, 0.000)),
    ('LeftLowerLeg',  13, (0.095, 0.500, 0.000)),
    ('LeftFoot',      14, (0.095, 0.080, 0.000)),
    ('LeftToes',      15, (0.095, 0.035, 0.150)),
    ('RightUpperLeg',  0, (-0.095, 0.950, 0.000)),
    ('RightLowerLeg', 17, (-0.095, 0.500, 0.000)),
    ('RightFoot',     18, (-0.095, 0.080, 0.000)),
    ('RightToes',     19, (-0.095, 0.035, 0.150)),
    # secondary motion (spring driven in the animator, not part of the gait)
    ('Pack',           2, (0.000, 1.280, -0.120)),
    ('Hood',           2, (0.000, 1.440, -0.080)),
    ('HairFront',      4, (0.000, 1.795, 0.050)),
    ('HairBack',       4, (0.000, 1.775, -0.060)),
]
NAMES = [b[0] for b in BONES]
IDX = {n: i for i, n in enumerate(NAMES)}
CORE_BONES = 21          # bones 0..20 are required by the animator; 21..24 are optional secondary bones

# segment lengths used by the animator for foot-contact maths
THIGH = 0.450
SHANK = 0.420
HIP_HALF_WIDTH = 0.095
HIP_DROP = 0.010                 # hip joint sits 1 cm below the Hips bone origin
ANKLE_HEIGHT = 0.080             # ankle joint above the sole
TOE_JOINT = (0.150, 0.035)       # (z forward of ankle, y above sole) of the ball-of-foot joint
HEEL_Z = -0.065                  # heel back from the ankle
TOE_TIP_Z = 0.085                # toe tip beyond the toe joint


def local_offset(i: int):
    """Translation of bone i relative to its parent (what the glTF node stores)."""
    _, parent, pos = BONES[i]
    if parent < 0:
        return tuple(pos)
    pp = BONES[parent][2]
    return (pos[0] - pp[0], pos[1] - pp[1], pos[2] - pp[2])


def self_check():
    """Cheap consistency checks run by the generator."""
    assert [b[0] for b in BONES][:3] == ['Hips', 'Spine', 'Chest']
    for i, (n, p, _) in enumerate(BONES):
        assert p < i, f'{n}: parent must come before the child'
    lh = BONES[IDX['LeftUpperLeg']][2]; lk = BONES[IDX['LeftLowerLeg']][2]; la = BONES[IDX['LeftFoot']][2]
    assert abs((lh[1] - lk[1]) - THIGH) < 1e-6, 'thigh length constant out of sync'
    assert abs((lk[1] - la[1]) - SHANK) < 1e-6, 'shank length constant out of sync'
    assert abs(la[1] - ANKLE_HEIGHT) < 1e-6
    assert abs(BONES[IDX['Hips']][2][1] - BONES[IDX['LeftUpperLeg']][2][1] - HIP_DROP) < 1e-6
    for l, r in (('Left', 'Right'),):
        for part in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand', 'UpperLeg', 'LowerLeg', 'Foot', 'Toes'):
            a = BONES[IDX[l + part]][2]; b = BONES[IDX[r + part]][2]
            assert abs(a[0] + b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9 and abs(a[2] - b[2]) < 1e-9, f'{part} is not mirrored'


self_check()
