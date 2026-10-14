"""Procedural cartoon runner for NEXALANE (0.6.0) - a big, chunky, friendly street runner in the spirit of the classic
three-lane runners: oversized head with a cap, wide hoodie, backpack, baggy jeans and huge sneakers.

ONE skinned mesh on the 25-bone skeleton of toon_rig.py (same bone names as the old human rig, so RunnerAnimator binds it).
Surfaces (so the engine can tint / light them):
    matte         skin, hair, jeans, shoes, backpack ... (colour carried in COLOR_0, with a little baked "ambient occlusion")
    RunnerAccent  hoodie, sleeves, cap, shoe toe caps (white-ish grey in COLOR_0, tinted at run time by the runner colour)
    RunnerGlow    emissive strips (arm bands, heel lights, pack strip) - tinted at run time
    RunnerOutline unlit dark inverted-hull shell: the cartoon outline, skinned with the same weights

    python -m assetgen.toon          (from tools/)   prints triangle counts
"""
from __future__ import annotations
import math
import numpy as np

from .geo import Rx, Ry, Rz
from .glb import GLBWriter, Mat, CLASS_MATS
from .human import (SkinnedModel, Part, tube as _tube, tube_z as _tube_z, ellip as _ellip, box, shift, mirror_x, chain, rigid, mix,
                    top4, fix_winding, Y, NY, Zc, C)
from . import toon_rig as rig

IDX = rig.IDX
NB = len(rig.BONES)

# Mobile budget: the authored segment / ring counts below are scaled down so the whole runner (body + outline shell) stays
# under about 9k triangles.  Raise these two numbers for a hero render.
Q_SEG = 0.52
Q_STEP = 2.6
Q_ELLIP = 0.56


def tube(sections, seg=14, caps=(True, True), step=0.03, extra=(), xf=None, keep=True):
    return _tube(sections, max(8, int(round(seg * Q_SEG))), caps, step * Q_STEP, extra, xf, keep)


def tube_z(sections, seg=12, caps=(True, True), step=0.02, extra=(), keep=True):
    return _tube_z(sections, max(8, int(round(seg * Q_SEG))), caps, step * Q_STEP, extra, keep)


def ellip(radii, center=(0, 0, 0), xf=None, seg=10, rings=6):
    return _ellip(radii, center, xf, max(6, int(round(seg * Q_ELLIP))), max(4, int(round(rings * Q_ELLIP))))
LX = rig.BONES[IDX['LeftUpperLeg']][2][0]            # 0.115

OUTLINE = 0.0105                                      # shell thickness (m)
OUTLINE_COLOR = (0.030, 0.034, 0.075, 1.0)

# ------------------------------------------------------------------------------------------------ palette (linear RGBA)
PAL = dict(
    skin=C(236, 172, 130), skin_shade=C(218, 148, 112), hair=C(52, 34, 28), brow=C(40, 26, 22),
    eye_w=C(252, 252, 255), pupil=C(30, 24, 34), mouth=C(150, 38, 52), tongue=C(236, 104, 116), teeth=C(255, 252, 246),
    jeans=C(62, 102, 176), jeans_dk=C(48, 82, 146), cuff=C(236, 240, 248),
    shoe=C(250, 250, 253), sole=C(214, 222, 238), sole_dk=C(150, 162, 188), lace=C(205, 212, 226),
    pack=C(46, 50, 70), pack_hi=C(66, 72, 98), strap=C(36, 40, 56),
    white=C(248, 249, 252), accent=(1.0, 1.0, 1.0, 1.0), accent_dk=(0.78, 0.78, 0.78, 1.0), accent_lt=(1.0, 1.0, 1.0, 1.0),
    glow=(1.0, 1.0, 1.0, 1.0))


# ------------------------------------------------------------------------------------------------ sections (y, rx, rz, cx, cz)
HOODIE = [
    (0.790, 0.242, 0.188, 0, -0.004), (0.840, 0.236, 0.184, 0, -0.002), (0.930, 0.226, 0.178, 0, 0.004),
    (1.030, 0.224, 0.178, 0, 0.008), (1.130, 0.240, 0.184, 0, 0.004), (1.230, 0.268, 0.190, 0, -0.002),
    (1.320, 0.284, 0.186, 0, -0.008), (1.395, 0.250, 0.168, 0, -0.010), (1.450, 0.178, 0.138, 0, -0.010),
    (1.492, 0.118, 0.104, 0, -0.008), (1.515, 0.098, 0.090, 0, -0.006)]
PANTS = [(0.640, 0.150, 0.128, 0, -0.004), (0.720, 0.206, 0.160, 0, -0.004), (0.800, 0.208, 0.162, 0, -0.004),
         (0.900, 0.206, 0.160, 0, -0.004)]
LEG = [  # y, rx, rz, cx (relative to the hip), cz
    (0.920, 0.100, 0.118, 0.000, -0.004), (0.820, 0.108, 0.122, 0.000, 0.000), (0.700, 0.116, 0.120, 0.000, 0.000),
    (0.580, 0.105, 0.109, 0.000, 0.000), (0.470, 0.101, 0.106, 0.000, 0.004), (0.370, 0.099, 0.103, 0.000, 0.000),
    (0.270, 0.102, 0.104, 0.000, -0.002), (0.200, 0.110, 0.112, 0.000, -0.004), (0.160, 0.112, 0.114, 0.000, -0.004)]
ARM = [  # y, rx, rz  (cx follows the arm axis)
    (1.440, 0.074, 0.076), (1.395, 0.094, 0.094), (1.330, 0.088, 0.088), (1.250, 0.083, 0.083), (1.160, 0.079, 0.079),
    (1.080, 0.076, 0.076), (1.000, 0.073, 0.073), (0.920, 0.069, 0.069), (0.850, 0.065, 0.065), (0.805, 0.065, 0.065)]
NECK = [(1.400, 0.082, 0.080, 0, 0.0), (1.470, 0.076, 0.074, 0, 0.004), (1.545, 0.074, 0.074, 0, 0.008)]

HC = np.array([0.0, 1.695, 0.010])                    # head centre
HR = np.array([0.236, 0.228, 0.236])                  # head radii (big cartoon head)


def face_z(x, y):
    q = 1.0 - ((x - HC[0]) / HR[0]) ** 2 - ((y - HC[1]) / HR[1]) ** 2
    return float(HC[2] + HR[2] * math.sqrt(max(q, 0.0)))


def arm_axis_x(y, side):
    ys = [1.36, 1.06, 0.78]; xs = [0.300, 0.330, 0.345]
    return side * float(np.interp(-y, [-v for v in ys], xs))


def arm_radius(y):
    a = np.array(sorted(ARM), float)
    return float(np.interp(y, a[:, 0], a[:, 1]))


class ToonModel(SkinnedModel):
    """SkinnedModel + per-part outline flag, grey vertex colours on the accent class, baked shading and the outline shell."""

    def add(self, arrays, cls, color, weights, outline=True):
        super().add(arrays, cls, color, weights)
        self.parts[-1].outline = outline

    # ---- shading hint baked into the vertex colours (top lighter, underside darker)
    @staticmethod
    def _shade(nrm):
        return (0.80 + 0.20 * (0.5 + 0.5 * np.clip(nrm[:, 1], -1.0, 1.0)))[:, None]

    def classes(self):
        out = {}
        for pt in self.parts:
            n = len(pt.pos)
            col = pt.color(pt.pos) if callable(pt.color) else np.tile(np.array(pt.color, float), (n, 1))
            if pt.cls in ('matte', 'RunnerAccent'):
                col = col.copy(); col[:, :3] *= self._shade(pt.nrm)
            W = pt.weights(pt.pos) if callable(pt.weights) else pt.weights
            jnt, wgt = top4(W)
            g = out.setdefault(pt.cls, dict(pos=[], nrm=[], uv=[], idx=[], col=[], jnt=[], wgt=[], n=0))
            g['pos'].append(pt.pos); g['nrm'].append(pt.nrm); g['uv'].append(pt.uv)
            g['idx'].append(np.asarray(pt.idx, int) + g['n']); g['col'].append(col); g['jnt'].append(jnt); g['wgt'].append(wgt)
            g['n'] += len(pt.pos)
        res = {k: dict(pos=np.vstack(v['pos']), nrm=np.vstack(v['nrm']), uv=np.vstack(v['uv']), idx=np.vstack(v['idx']),
                       col=np.vstack(v['col']), jnt=np.vstack(v['jnt']), wgt=np.vstack(v['wgt'])) for k, v in out.items()}
        ol = self.outline_shell()
        if ol is not None:
            res['RunnerOutline'] = ol
        return res

    # ---- inverted hull
    @staticmethod
    def _smooth_normals(pos, nrm):
        key = np.round(pos * 2000.0).astype(np.int64)
        _, inv = np.unique(key, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        acc = np.zeros((inv.max() + 1, 3))
        np.add.at(acc, inv, nrm)
        acc /= np.linalg.norm(acc, axis=1, keepdims=True) + 1e-12
        return acc[inv]

    def outline_shell(self):
        pos, nrm, idx, jnt, wgt = [], [], [], [], []
        n = 0
        for pt in self.parts:
            if not getattr(pt, 'outline', True) or pt.cls == 'RunnerGlow':
                continue
            sn = self._smooth_normals(pt.pos, pt.nrm)
            p = pt.pos + sn * OUTLINE
            W = pt.weights(pt.pos) if callable(pt.weights) else pt.weights
            j, w = top4(W)
            t = np.asarray(pt.idx, int)[:, [0, 2, 1]] + n          # flipped winding: only the far side of the shell is drawn
            pos.append(p); nrm.append(-sn); idx.append(t); jnt.append(j); wgt.append(w); n += len(p)
        if not pos:
            return None
        return dict(pos=np.vstack(pos), nrm=np.vstack(nrm), uv=np.zeros((n, 2)), idx=np.vstack(idx), col=None,
                    jnt=np.vstack(jnt), wgt=np.vstack(wgt))

    # ---- glTF
    def write(self, path, mats=None):
        import json, struct
        cls = self.classes()
        w = GLBWriter(generator='NEXALANE procedural assets 0.6.0 (cartoon runner)')
        material = {
            'matte': Mat('matte', (1, 1, 1, 1), 0.0, 0.66),
            'RunnerAccent': Mat('RunnerAccent', (1.0, 0.376, 0.086, 1.0), 0.0, 0.52),
            'RunnerGlow': Mat('RunnerGlow', (0.02, 0.02, 0.02, 1.0), 0.0, 0.4, emissive=(1.0, 0.43, 0.12)),
            'RunnerOutline': Mat('RunnerOutline', OUTLINE_COLOR, 0.0, 1.0, unlit=True)}
        order = [k for k in ('matte', 'RunnerAccent', 'RunnerGlow', 'RunnerOutline') if k in cls]
        prims = []
        for k in order:
            g = cls[k]
            attrs = {"POSITION": w._accessor(g['pos'].astype('<f4'), 5126, "VEC3", 34962, minmax=True),
                     "NORMAL": w._accessor(g['nrm'].astype('<f4'), 5126, "VEC3", 34962),
                     "TEXCOORD_0": w._accessor(g['uv'].astype('<f4'), 5126, "VEC2", 34962)}
            if g['col'] is not None and k in ('matte', 'RunnerAccent'):
                attrs["COLOR_0"] = w._accessor(g['col'].astype('<f4'), 5126, "VEC4", 34962)
            attrs["JOINTS_0"] = w._accessor(g['jnt'].astype('u1'), 5121, "VEC4", 34962)
            attrs["WEIGHTS_0"] = w._accessor(g['wgt'].astype('<f4'), 5126, "VEC4", 34962)
            flat = g['idx'].reshape(-1)
            big = flat.max() >= 65535
            a_idx = w._accessor(flat.astype('<u4' if big else '<u2'), 5125 if big else 5123, "SCALAR", 34963)
            prims.append({"attributes": attrs, "indices": a_idx, "material": w.material(material[k]), "mode": 4})
        w.meshes.append({"name": "RunnerBody", "primitives": prims})
        nodes = [{"name": "Runner", "children": [1]}]
        for i, (name, parent, _) in enumerate(rig.BONES):
            nodes.append({"name": name, "translation": [float(v) for v in rig.local_offset(i)]})
        for i, (_, parent, _) in enumerate(rig.BONES):
            if parent >= 0:
                nodes[parent + 1].setdefault("children", []).append(i + 1)
        nodes.append({"name": "RunnerBody", "mesh": 0, "skin": 0})
        nodes[0]["children"].append(NB + 1)
        ibm = np.zeros((NB, 16), '<f4')
        for i, (_, _, pos) in enumerate(rig.BONES):
            m = np.eye(4); m[:3, 3] = -np.array(pos)
            ibm[i] = m.T.reshape(-1)
        a_ibm = w._accessor(ibm, 5126, "MAT4", None)
        skin = {"name": "RunnerRig", "inverseBindMatrices": a_ibm, "joints": list(range(1, NB + 1)), "skeleton": 1}
        js = {"asset": {"version": "2.0", "generator": w.generator}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": nodes,
              "skins": [skin], "meshes": w.meshes, "materials": w.materials, "accessors": w.accessors,
              "bufferViews": w.buffer_views, "buffers": [{"byteLength": len(w.bin)}]}
        if w.uses_unlit:
            js["extensionsUsed"] = ["KHR_materials_unlit"]
        jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
        while len(jb) % 4:
            jb += b" "
        w._align()
        total = 12 + 8 + len(jb) + 8 + len(w.bin)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(jb), 0x4E4F534A)); f.write(jb)
            f.write(struct.pack("<II", len(w.bin), 0x004E4942)); f.write(bytes(w.bin))
        return total


def dome(cx, cy, cz, rx, ry, rz, y_rim, bottom_open=True, rings=7, seg=22):
    """Smooth ellipsoidal dome from the rim height y_rim up to the top (a loft with a clean, round rim)."""
    ys = np.linspace(y_rim, cy + ry * 0.999, rings)
    secs = []
    for y in ys:
        q = max(1.0 - ((y - cy) / ry) ** 2, 0.0)
        secs.append((float(y), max(rx * math.sqrt(q), 0.004), max(rz * math.sqrt(q), 0.004), cx, cz))
    return _tube(secs, max(8, int(round(seg * Q_SEG))), (not bottom_open, True), 0.09, (), None, True)


# ------------------------------------------------------------------------------------------------ the runner
def _trim(arrays, keep_fn):
    p, n, u, t = arrays
    cent = p[np.asarray(t, int)].mean(1)
    keep = keep_fn(cent)
    return p, n, u, np.asarray(t, int)[keep]


def build_runner() -> ToonModel:
    m = ToonModel()
    P = PAL

    # =========================================================================== torso (hoodie), pants, hood, pocket
    torso_w = chain(Y, ['Hips', 'Spine', 'Chest', 'Neck'], [0.95, 1.10, 1.47], [0.06, 0.07, 0.03])
    m.add(tube(HOODIE, 22, (False, True), 0.06, extra=(1.40, 1.46), keep=False), 'RunnerAccent', P['accent'], torso_w)
    m.add(tube(PANTS, 22, (True, False), 0.06, keep=False), 'matte', P['jeans'], chain(Y, ['Hips', 'Spine'], [1.00], [0.05]))
    # hem band + chest colour-block band (white)
    m.add(tube([(0.790, 0.244, 0.190, 0, -0.004), (0.836, 0.2385, 0.186, 0, -0.002)], 22, (False, False), 0.02), 'matte', P['white'],
          chain(Y, ['Hips', 'Spine'], [1.00], [0.05]))
    m.add(tube([(1.180, 0.2465, 0.1865, 0, 0.004), (1.226, 0.2705, 0.1925, 0, -0.002)], 22, (False, False), 0.02), 'matte', P['white'], torso_w)
    # kangaroo pocket
    m.add(box((0.300, 0.150, 0.030), (0.0, 0.955, 0.194), 0.020, xf=Rx(-0.10)), 'RunnerAccent', P['accent_dk'], torso_w, outline=False)
    # drawstrings
    for sx in (-1, 1):
        m.add(tube([(1.300, 0.0075, 0.0075, sx * 0.045, 0.186), (1.440, 0.0075, 0.0075, sx * 0.040, 0.158)], 8, (True, True), 0.03),
              'matte', P['white'], torso_w, outline=False)
        m.add(ellip((0.011, 0.020, 0.011), (sx * 0.045, 1.292, 0.188), seg=8, rings=5), 'matte', P['white'], torso_w, outline=False)
    # hood bundle behind the neck (springs on the Hood bone)
    m.add(ellip((0.165, 0.095, 0.085), (0.0, 1.452, -0.135), xf=Rx(-0.28), seg=14, rings=8), 'RunnerAccent', P['accent_dk'],
          mix(rigid('Chest'), rigid('Hood'), 0.80))
    # neck + collar
    neck_w = chain(Y, ['Chest', 'Neck', 'Head'], [1.455, 1.55], [0.03, 0.03])
    m.add(tube(NECK, 14, (False, False), 0.04), 'matte', P['skin_shade'], neck_w, outline=False)
    m.add(tube([(1.480, 0.130, 0.112, 0, -0.008), (1.512, 0.112, 0.098, 0, -0.006)], 20, (False, False), 0.02), 'matte', P['white'],
          chain(Y, ['Chest', 'Neck'], [1.50], [0.03]), outline=False)

    # =========================================================================== backpack (springs on the Pack bone)
    m.add(box((0.330, 0.400, 0.150), (0.0, 1.190, -0.255), 0.060), 'matte', P['pack'], rigid('Pack'))
    m.add(box((0.250, 0.150, 0.060), (0.0, 1.060, -0.345), 0.030), 'matte', P['pack_hi'], rigid('Pack'), outline=False)
    m.add(box((0.034, 0.300, 0.014), (0.0, 1.215, -0.338), 0.0), 'RunnerGlow', P['glow'], rigid('Pack'), outline=False)
    for sx in (-1, 1):                                                                       # shoulder straps
        m.add(box((0.060, 0.300, 0.026), (sx * 0.125, 1.275, 0.198), 0.010, xf=Rx(-0.06)), 'matte', P['strap'], mix(rigid('Chest'), rigid('Pack'), 0.30), outline=False)
        m.add(box((0.060, 0.100, 0.100), (sx * 0.125, 1.440, -0.030), 0.020), 'matte', P['strap'], mix(rigid('Chest'), rigid('Pack'), 0.30), outline=False)

    # =========================================================================== legs, shoes
    for side, nm in ((1, 'Left'), (-1, 'Right')):
        w_leg = chain(NY, ['Hips', nm + 'UpperLeg', nm + 'LowerLeg'], [-0.90, -0.47], [0.04, 0.08])
        secs = [(y, rx, rz, side * (LX + cx), cz) for y, rx, rz, cx, cz in LEG]
        m.add(tube(secs, 18, (False, False), 0.07, extra=(0.52, 0.47, 0.42), keep=False), 'matte', P['jeans'], w_leg)
        m.add(tube([(0.158, 0.1145, 0.1165, side * LX, -0.004), (0.232, 0.1145, 0.1165, side * LX, -0.004)], 18, (False, True), 0.03),
              'matte', P['cuff'], w_leg)                                                      # rolled cuff
        shoe_w = chain(Zc, [nm + 'Foot', nm + 'Toes'], [0.140], [0.045])
        ax, ay = side * LX, rig.ANKLE_HEIGHT
        upper = tube_z([(-0.108, 0.050, 0.056, 0, -0.030), (-0.080, 0.066, 0.078, 0, -0.026), (-0.030, 0.071, 0.080, 0, -0.030),
                        (0.030, 0.072, 0.066, 0, -0.045), (0.100, 0.074, 0.052, 0, -0.056), (0.170, 0.075, 0.046, 0, -0.062),
                        (0.230, 0.068, 0.040, 0, -0.064), (0.272, 0.046, 0.032, 0, -0.065), (0.290, 0.020, 0.018, 0, -0.066)],
                       14, (True, True), 0.04, keep=True)
        toe_cap = tube_z([(0.160, 0.0770, 0.0485, 0, -0.063), (0.230, 0.0705, 0.0425, 0, -0.065), (0.272, 0.0485, 0.0345, 0, -0.066),
                          (0.291, 0.021, 0.0195, 0, -0.067)], 14, (False, True), 0.04, keep=True)
        sole = tube_z([(-0.112, 0.050, 0.022, 0, -0.088), (-0.070, 0.074, 0.022, 0, -0.088), (0.000, 0.080, 0.022, 0, -0.088),
                       (0.100, 0.082, 0.022, 0, -0.088), (0.190, 0.082, 0.022, 0, -0.088), (0.255, 0.066, 0.022, 0, -0.088),
                       (0.296, 0.032, 0.022, 0, -0.088)], 14, (True, True), 0.05, keep=True)
        m.add(shift(upper, (ax, ay, 0)), 'matte', P['shoe'], shoe_w)
        m.add(shift(toe_cap, (ax, ay, 0)), 'RunnerAccent', P['accent'], shoe_w, outline=False)
        m.add(shift(sole, (ax, ay, 0)), 'matte', P['sole'], shoe_w)
        m.add(box((0.100, 0.026, 0.012), (ax, ay - 0.022, -0.112), 0.004), 'RunnerGlow', P['glow'], shoe_w, outline=False)     # heel light
        m.add(box((0.090, 0.030, 0.050), (ax, ay + 0.010, 0.044), 0.014, xf=Rx(0.55)), 'matte', P['lace'], shoe_w, outline=False)  # tongue / laces

    # =========================================================================== arms (hoodie sleeves), hands
    for side, nm in ((1, 'Left'), (-1, 'Right')):
        w_arm = chain(NY, [nm + 'UpperArm', nm + 'LowerArm', nm + 'Hand'], [-1.06, -0.78], [0.07, 0.03])
        secs = [(y, rx, rz, arm_axis_x(y, side), 0.0) for y, rx, rz in ARM]
        m.add(tube(secs, 16, (False, False), 0.06, extra=(1.10, 1.02, 0.98), keep=False), 'RunnerAccent', P['accent'], w_arm)
        cap_w = mix(rigid(nm + 'UpperArm'), chain(Y, [nm + 'UpperArm', nm + 'Shoulder'], [1.46], [0.05]), lambda p: np.clip((p[:, 1] - 1.38) / 0.08, 0, 0.7))
        m.add(ellip((0.098, 0.092, 0.092), (side * 0.282, 1.380, 0.0), seg=14, rings=8), 'RunnerAccent', P['accent'], cap_w)     # shoulder cap
        for yb, rr in ((1.205, 0.0), (0.838, 0.0)):                                                        # glow band / white cuff
            r = arm_radius(yb) + 0.003
            if yb > 1.0:
                m.add(tube([(yb - 0.014, r, r, arm_axis_x(yb, side), 0.0), (yb + 0.014, r, r, arm_axis_x(yb, side), 0.0)], 16, (False, False), 0.02),
                      'RunnerGlow', P['glow'], w_arm, outline=False)
            else:
                m.add(tube([(yb - 0.030, r + 0.004, r + 0.004, arm_axis_x(yb, side), 0.0), (yb + 0.030, r + 0.004, r + 0.004, arm_axis_x(yb, side), 0.0)],
                           16, (False, False), 0.02), 'matte', P['cuff'], mix(rigid(nm + 'LowerArm'), rigid(nm + 'Hand'), 0.25))
        hx = side * 0.345
        hand_w = rigid(nm + 'Hand')
        m.add(ellip((0.082, 0.095, 0.072), (hx, 0.712, 0.006), seg=14, rings=8), 'matte', P['skin'], hand_w)                  # big mitt
        m.add(ellip((0.034, 0.056, 0.034), (hx - side * 0.060, 0.735, 0.060), xf=Rx(0.5) @ Rz(side * 0.35), seg=10, rings=6), 'matte', P['skin'], hand_w)   # thumb

    # =========================================================================== head
    head_w = rigid('Head')
    hx, hy, hz = HR
    m.add(ellip(tuple(HR), tuple(HC), seg=26, rings=16), 'matte', P['skin'], head_w)
    for sx in (-1, 1):
        m.add(ellip((0.030, 0.054, 0.038), (sx * hx * 0.995, HC[1] - 0.030, 0.004), xf=Rz(-sx * 0.12), seg=10, rings=6), 'matte', P['skin_shade'], head_w)   # ears
        ex, ey = sx * 0.083, HC[1] - 0.012
        ez = face_z(ex, ey) - 0.018
        m.add(ellip((0.056, 0.068, 0.038), (ex, ey, ez), seg=14, rings=9), 'matte', P['eye_w'], head_w, outline=False)                  # eye white
        m.add(ellip((0.030, 0.042, 0.014), (ex * 0.92, ey - 0.005, ez + 0.031), seg=10, rings=6), 'matte', P['pupil'], head_w, outline=False)
        m.add(ellip((0.011, 0.011, 0.007), (ex * 0.92 + sx * 0.013, ey + 0.016, ez + 0.042), seg=8, rings=4), 'matte', P['eye_w'], head_w, outline=False)
        by = HC[1] + 0.066
        m.add(ellip((0.058, 0.014, 0.018), (sx * 0.088, by, face_z(sx * 0.088, by) + 0.002), xf=Rz(sx * 0.22), seg=8, rings=4), 'matte', P['brow'], head_w, outline=False)
        cy = HC[1] - 0.105
        m.add(ellip((0.046, 0.034, 0.022), (sx * 0.135, cy, face_z(sx * 0.135, cy) - 0.005), seg=10, rings=6), 'matte', P['skin'], head_w, outline=False)   # cheeks
    ny = HC[1] - 0.070
    m.add(ellip((0.035, 0.031, 0.034), (0.0, ny, face_z(0.0, ny) + 0.013), seg=12, rings=8), 'matte', P['skin_shade'], head_w, outline=False)     # nose
    my = HC[1] - 0.138
    zm = face_z(0.0, my)
    m.add(ellip((0.078, 0.040, 0.015), (0.0, my, zm - 0.004), seg=14, rings=6), 'matte', P['mouth'], head_w, outline=False)                       # open grin
    m.add(ellip((0.064, 0.013, 0.012), (0.0, my + 0.022, zm + 0.002), seg=10, rings=4), 'matte', P['teeth'], head_w, outline=False)
    m.add(ellip((0.036, 0.013, 0.010), (0.0, my - 0.020, zm + 0.001), seg=8, rings=4), 'matte', P['tongue'], head_w, outline=False)

    # hair: a shell shifted backwards, so only the back and the sides show below the cap (the face stays clear)
    hair = dome(0.0, 1.670, -0.040, 0.250, 0.170, 0.250, 1.545, bottom_open=True)
    m.add(hair, 'matte', P['hair'], mix(rigid('Head'), rigid('HairBack'), lambda p: np.clip((-p[:, 2] - 0.13) / 0.14, 0, 0.55)))
    m.add(ellip((0.066, 0.056, 0.110), (0.0, 1.735, -0.300), xf=Rx(-0.35), seg=10, rings=6), 'matte', P['hair'],
          mix(rigid('Head'), rigid('HairBack'), 0.85))
    for sx in (-1, 1):
        m.add(ellip((0.032, 0.066, 0.036), (sx * 0.226, HC[1] - 0.045, 0.080), xf=Rz(-sx * 0.25), seg=10, rings=6), 'matte', P['hair'],
              mix(rigid('Head'), rigid('HairFront'), 0.55), outline=False)                    # sideburn tufts

    # =========================================================================== cap
    cap = dome(0.0, 1.800, -0.006, 0.262, 0.152, 0.272, 1.758, bottom_open=True)
    m.add(cap, 'RunnerAccent', P['accent'], head_w)
    m.add(tube([(1.744, 0.2575, 0.2685, 0, -0.006), (1.770, 0.2575, 0.2685, 0, -0.006)], 24, (False, False), 0.02), 'RunnerAccent', P['accent_dk'], head_w, outline=False)
    m.add(ellip((0.172, 0.017, 0.135), (0.0, 1.758, 0.300), xf=Rx(0.20), seg=16, rings=6), 'RunnerAccent', P['accent_dk'], head_w)       # brim
    m.add(ellip((0.118, 0.088, 0.034), (0.0, 1.832, 0.228), xf=Rx(-0.30), seg=14, rings=8), 'matte', P['white'], head_w, outline=False)   # front panel
    m.add(ellip((0.020, 0.020, 0.020), (0.0, 1.950, -0.006), seg=8, rings=5), 'RunnerAccent', P['accent_dk'], head_w, outline=False)
    return m


if __name__ == '__main__':
    mdl = build_runner()
    cls = mdl.classes()
    print('triangles', sum(len(v['idx']) for v in cls.values()))
    for k, v in cls.items():
        print(f'  {k:14s} verts={len(v["pos"]):5d} tris={len(v["idx"]):5d}')
