#!/usr/bin/env python3
"""Verifies that gameplay/runner/gait_model.gd (GDScript) computes exactly what tools/gait_reference.py (Python) computes.

There is no Godot in the build container, so this file contains a tiny GDScript -> Python translator for the subset of the
language used by gait_model.gd (typed vars, static funcs, for/if, Basis / Vector3 maths), runs the translated code and compares
every public function with the reference on many inputs.  Exit code 0 = identical within 1e-5.

    python tools/check_gait_port.py
"""
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import gait_reference as g  # noqa: E402


# --------------------------------------------------------------------------- GDScript runtime shims
class Vector3:
    def __init__(self, x=0.0, y=0.0, z=0.0): self.v = np.array([x, y, z], float)
    x = property(lambda s: s.v[0]); y = property(lambda s: s.v[1]); z = property(lambda s: s.v[2])
    def __add__(self, o): r = Vector3(); r.v = self.v + o.v; return r


class Basis:
    def __init__(self, m=None): self.m = np.eye(3) if m is None else m
    @staticmethod
    def from_euler(e): return Basis(g.euler_yxz(e.x, e.y, e.z))
    def __mul__(self, o):
        if isinstance(o, Basis): return Basis(self.m @ o.m)
        r = Vector3(); r.v = self.m @ o.v; return r


class PackedFloat32Array(list):
    def resize(self, n): self.extend([0.0] * (n - len(self)))


def _smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3.0 - 2.0 * t)


SHIMS = dict(
    PI=math.pi, TAU=2 * math.pi, sin=math.sin, floorf=lambda x: float(math.floor(x)), absf=abs, lerpf=lambda a, b, t: a + (b - a) * t,
    clampf=lambda x, lo, hi: lo if x < lo else (hi if x > hi else x), maxf=max, minf=min, smoothstep=_smoothstep,
    Vector3=Vector3, Basis=Basis, PackedFloat32Array=PackedFloat32Array, float=float, int=int, range=range)


def translate(src: str) -> str:
    out = []
    for raw in src.split('\n'):
        line = raw.rstrip('\n')
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('extends ') or stripped.startswith('class_name '):
            continue
        indent = len(line) - len(line.lstrip('\t'))
        body = stripped
        m = re.match(r'^static func (\w+)\((.*)\)\s*(->\s*[\w\[\]]+)?\s*:$', body)
        if m:
            args = [a.split(':')[0].strip() for a in m.group(2).split(',') if a.strip()]
            body = f'def {m.group(1)}({", ".join(args)}):'
        elif body.startswith('const '):
            m = re.match(r'^const (\w+)\s*(?::\s*\w+)?\s*:?=\s*(.*)$', body)
            body = f'{m.group(1)} = {m.group(2)}'
        elif body.startswith('var '):
            m = re.match(r'^var (\w+)\s*(?::\s*[\w\[\]]+)?\s*(?::?=\s*(.*))?$', body)
            body = f'{m.group(1)} = {m.group(2)}' if m.group(2) is not None else f'{m.group(1)} = 0.0'
        body = re.sub(r'(\w+)\.size\(\)', r'len(\1)', body)
        out.append('    ' * indent + body)
    return '\n'.join(out)


def load_gd(path):
    ns = dict(SHIMS)
    code = translate(Path(path).read_text())
    exec(compile(code, str(path), 'exec'), ns)
    return ns


# --------------------------------------------------------------------------- comparison
def close(a, b, tol=1e-5):
    return np.allclose(np.asarray(a, float), np.asarray(b, float), atol=tol, rtol=1e-5)


def main():
    gd = load_gd(ROOT / 'gameplay' / 'runner' / 'gait_model.gd')
    fails = []

    def check(name, a, b):
        if not close(a, b): fails.append(f'{name}: GDScript {np.round(np.asarray(a, float), 5).tolist()[:6]} != reference {np.round(np.asarray(b, float), 5).tolist()[:6]}')

    for k in ('N_CH', 'PEL_X', 'ARM', 'LEG', 'THIGH', 'SHANK', 'REST_HIPS_Y', 'STANCE_JOG', 'STANCE_SPR', 'SLIDE_PELVIS_Y', 'AIR_PELVIS_Y'):
        ref = {'N_CH': g.N_CH, 'PEL_X': g.PEL_X, 'ARM': g.ARM, 'LEG': g.LEG, 'THIGH': g.rig.THIGH, 'SHANK': g.rig.SHANK,
               'REST_HIPS_Y': g.rig.BONES[0][2][1], 'STANCE_JOG': g.STANCE_JOG, 'STANCE_SPR': g.STANCE_SPR,
               'SLIDE_PELVIS_Y': g.SLIDE_PELVIS_Y, 'AIR_PELVIS_Y': g.AIR_PELVIS_Y}[k]
        check('const ' + k, gd[k], ref)
    for name in ('THIGH_JOG', 'THIGH_SPR', 'KNEE_JOG', 'KNEE_SPR', 'FOOT_JOG', 'FOOT_SPR'):
        check('table ' + name, gd[name], getattr(g, name))

    rng = np.random.default_rng(7)
    for i in range(60):
        ph = float(rng.uniform(-0.3, 1.8)); spd = float(rng.uniform(0, 36)); u = g.intensity(spd); over = g.overdrive(spd)
        extra = float(rng.uniform(-0.1, 0.4)); launch = float(rng.uniform(0, 1)); turn = float(rng.uniform(-1, 1)); cad = g.cadence(u, over)
        check(f'cyc {i}', gd['cyc'](g.THIGH_JOG, ph), g.cyc(g.THIGH_JOG, ph))
        check(f'intensity {i}', gd['intensity'](spd), u)
        check(f'overdrive {i}', gd['overdrive'](spd), over)
        check(f'cadence {i}', gd['cadence'](u, over), cad)
        check(f'stance {i}', gd['stance_fraction'](u), g.stance_fraction(u))
        a = gd['run_pose'](ph, u, over, extra, launch, turn)
        b = g.run_pose(ph, u, over, extra, launch, turn)
        check(f'run_pose {i} (ph={ph:.2f}, v={spd:.1f})', a, b)
        check(f'support_height {i}', gd['support_height'](a), g.support_height(b)[0])
        check(f'foot_low L {i}', gd['foot_low'](a, 0), g.foot_low(b, 0))
        check(f'foot_low R {i}', gd['foot_low'](a, 1), g.foot_low(b, 1))
        check(f'run_pelvis_y {i}', gd['run_pelvis_y'](ph, u, over, extra, launch, cad), g.run_pelvis_y(ph, u, over, extra, launch, cad))
    for t in (0.0, 0.7, 3.1, 11.9):
        check(f'idle {t}', gd['idle_pose'](t), g.idle_pose(t))
        check(f'ready {t}', gd['ready_pose'](t), g.ready_pose(t))
    for lead in (0, 1):
        check(f'slide lead {lead}', gd['slide_pose'](lead), g.slide_pose(lead))
        for a_ in np.linspace(0, 1, 11):
            check(f'air a={a_:.1f} lead {lead}', gd['air_pose'](float(a_), lead), g.air_pose(float(a_), lead))
    check('land', gd['land_pose'](), g.land_pose())
    check('hit recoil', gd['hit_recoil_pose'](), g.hit_recoil_pose())
    check('hit down', gd['hit_down_pose'](), g.hit_down_pose())
    # blending (the animator relies on the returned array)
    x = g.idle_pose(0.3); y = g.land_pose(); z = gd['blend_into'](PackedFloat32Array(list(x)), PackedFloat32Array(list(y)), 0.37)
    check('blend_into', z, x + (y - x) * 0.37)
    if fails:
        print('GDScript port differs from the reference:')
        for f in fails[:25]: print('  ', f)
        print(f'{len(fails)} mismatches')
        return 1
    print('gait_model.gd == gait_reference.py (60 random gait states, every pose, tables and constants)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
