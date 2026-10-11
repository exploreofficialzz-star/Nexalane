"""Procedural, skinned human for the NEXALANE runner (0.5.0).

The runner is ONE skinned mesh (about 7k triangles, 5 surfaces) on the 25-bone skeleton of human_rig.py:
anatomical proportions (1.82 m, 8 heads), tapered muscle-shaped limbs, a real head (jaw, brow, nose, eyes, lips, ears, tousled hair),
a hooded technical jacket with orange piping, a low pack, fingerless gloves, a wrist device, cargo pants with knee pads and running shoes.

Surfaces (so the engine can tint / light them): RunnerCloth (jacket + pants, wet sheen), matte (skin, hair, gloves, shoes, pads),
metal (zip, buckles), RunnerAccent (tinted by the selected runner colour), RunnerGlow (emissive, tinted).
"""
from __future__ import annotations
import math
import numpy as np
from scipy.interpolate import PchipInterpolator

from .geo import Mesh, T, Rx, Ry, Rz, compose, loft as loft_arrays, vertex_normals
from .glb import GLBWriter, Mat, CLASS_MATS
from .kit import lin, align_y
from . import human_rig as rig

IDX = rig.IDX
NB = len(rig.BONES)
LX = rig.BONES[IDX['LeftUpperLeg']][2][0]          # 0.095


# ------------------------------------------------------------------------------------------------ palette (linear RGBA)
def C(r, g, b): return lin((r, g, b))


PAL = dict(
    jacket=C(24, 26, 33), jacket_hi=C(36, 40, 50), pants=C(28, 30, 37), hood=C(20, 22, 28), strap=C(34, 36, 42),
    skin=C(188, 136, 106), skin_shade=C(168, 116, 90), lips=C(152, 92, 86), hair=C(26, 18, 14), brow=C(24, 17, 13),
    eye_w=C(226, 224, 218), iris=C(78, 52, 34), glove=C(18, 18, 21), glove_hi=C(28, 28, 33),
    shoe_up=C(30, 32, 38), shoe_sole=C(226, 228, 230), shoe_out=C(16, 16, 18), pad=C(20, 21, 25), pack=C(40, 44, 52),
    metal=C(156, 158, 164), watch=C(24, 26, 30), white=(1.0, 1.0, 1.0, 1.0))


# ------------------------------------------------------------------------------------------------ skin weights helpers
def rigid(name):
    j = IDX[name]

    def f(pos):
        W = np.zeros((len(pos), NB)); W[:, j] = 1.0
        return W
    return f


def _smooth(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def chain(coord, bones, cuts, widths):
    """1-D skinning along a limb / spine.  coord(pos) -> (N,) increasing along the chain; bones has len(cuts)+1 names;
    each cut blends the neighbouring bones over +-width with a smoothstep."""
    def f(pos):
        s = coord(pos)
        n = len(s); W = np.zeros((n, NB)); prev = np.ones(n)
        for i, name in enumerate(bones):
            nxt = _smooth((s - (cuts[i] - widths[i])) / (2.0 * widths[i])) if i < len(cuts) else np.zeros(n)
            W[:, IDX[name]] += prev * (1.0 - nxt)
            prev = prev * nxt
        return W
    return f


def mix(wa, wb, t):
    """Blend two weight functions; t is a scalar or fn(pos)->(N,)."""
    def f(pos):
        tt = t(pos) if callable(t) else t
        tt = np.broadcast_to(np.asarray(tt, float), (len(pos),))[:, None]
        return wa(pos) * (1.0 - tt) + wb(pos) * tt
    return f


Y = lambda p: p[:, 1]
NY = lambda p: -p[:, 1]
Zc = lambda p: p[:, 2]


def top4(W):
    idx = np.argsort(-W, axis=1)[:, :4]
    w = np.take_along_axis(W, idx, axis=1)
    w = np.maximum(w, 0.0); s = w.sum(1, keepdims=True); s[s == 0] = 1.0
    return idx.astype(np.uint8), (w / s).astype(np.float32)


def fix_winding(pos, nrm, idx):
    """Flip triangles whose geometric normal disagrees with the vertex normals (keeps CCW-outward)."""
    idx = np.asarray(idx, int).reshape(-1, 3).copy()
    fn = np.cross(pos[idx[:, 1]] - pos[idx[:, 0]], pos[idx[:, 2]] - pos[idx[:, 0]])
    avg = nrm[idx[:, 0]] + nrm[idx[:, 1]] + nrm[idx[:, 2]]
    flip = (fn * avg).sum(1) < 0
    idx[flip] = idx[flip][:, [0, 2, 1]]
    return idx


# ------------------------------------------------------------------------------------------------ geometry helpers
def dense(sections, step=0.03, extra=(), keep=True):
    """Resample (y, rx, rz, cx, cz) sections with PCHIP at a regular step (plus 'extra' ys) -> smooth ring stack.
    keep=False drops the authored section heights and only uses the regular step (+ the first / last section and 'extra')."""
    a = np.array(sections, float)
    order = np.argsort(a[:, 0]); a = a[order]
    base = a[:, 0] if keep else np.array([a[0, 0], a[-1, 0]])
    ys = np.unique(np.round(np.concatenate([np.arange(a[0, 0], a[-1, 0], step), base, np.array(extra, float)]), 5))
    ys = ys[(ys >= a[0, 0] - 1e-9) & (ys <= a[-1, 0] + 1e-9)]
    cols = [PchipInterpolator(a[:, 0], a[:, k])(ys) for k in range(1, 5)]
    return [(float(y), float(r1), float(r2), float(c1), float(c2)) for y, r1, r2, c1, c2 in zip(ys, *cols)]


class Part:
    """Geometry arrays + the data needed to skin it."""
    def __init__(self, arrays, cls, color, weights):
        self.pos, self.nrm, self.uv, self.idx = arrays
        self.cls, self.color, self.weights = cls, color, weights


def tube(sections, seg=14, caps=(True, True), step=0.03, extra=(), xf=None, keep=True):
    secs = dense(sections, step, extra, keep)
    p, n, u, t = loft_arrays(secs, seg, caps)
    if xf is not None:
        p = (np.c_[p, np.ones(len(p))] @ xf.T)[:, :3]
        n = n @ np.linalg.inv(xf[:3, :3]); n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return p, n, u, np.asarray(t, int)


def tube_z(sections, seg=12, caps=(True, True), step=0.02, extra=(), keep=True):
    """Loft along +Z. sections: (z, rx, ry, cx, cy)."""
    conv = [(z, rx, ry, cx, -cy) for z, rx, ry, cx, cy in sections]
    return tube(conv, seg, caps, step, extra, xf=Rx(math.pi / 2), keep=keep)


def mesh_arrays(m: Mesh):
    ps, ns, us, ts, off = [], [], [], [], 0
    for mat in m.materials():
        p, n, u, t = m.arrays(mat)
        ps.append(p); ns.append(n); us.append(u); ts.append(t + off); off += len(p)
    return np.vstack(ps), np.vstack(ns), np.vstack(us), np.vstack(ts)


def ellip(radii, center=(0, 0, 0), xf=None, seg=10, rings=6):
    m = Mesh(); m.sphere('p', 1.0, seg, rings, center=center, xf=xf, scale=radii)
    return mesh_arrays(m)


def box(size, center=(0, 0, 0), bevel=0.0, xf=None):
    m = Mesh(); m.box('p', size, center=center, bevel=bevel, xf=xf)
    return mesh_arrays(m)


def shift(arrays, d):
    p, n, u, t = arrays
    return p + np.array(d, float), n, u, t


def mirror_x(arrays):
    p, n, u, t = arrays
    p = p * np.array([-1, 1, 1]); n = n * np.array([-1, 1, 1])
    return p, n, u, np.asarray(t, int)[:, [0, 2, 1]]


def ribbon(profile_fn, pts, half_w, offset, front=True):
    """Strip hugging an elliptical torso: pts = [(x_center, y), ...]; profile_fn(y) -> (rx, rz, cx, cz)."""
    P, N = [], []
    sgn = 1.0 if front else -1.0
    for xc, y in pts:
        rx, rz, cx, cz = profile_fn(y)
        for sx in (-1.0, 1.0):
            x = xc + sx * half_w
            q = np.clip((x - cx) / rx, -0.98, 0.98)
            z = cz + sgn * rz * math.sqrt(1.0 - q * q)
            n = np.array([(x - cx) / rx ** 2, 0.0, sgn * (z - cz) / rz ** 2]); n /= np.linalg.norm(n) + 1e-12
            P.append((x, y, z + sgn * offset)); N.append(n)
    P = np.array(P); N = np.array(N)
    idx = []
    for r in range(len(pts) - 1):
        a, b, c, d = 2 * r, 2 * r + 1, 2 * r + 2, 2 * r + 3
        idx += [[a, b, d], [a, d, c]]
    idx = fix_winding(P, N, idx)
    uv = np.zeros((len(P), 2))
    return P, N, uv, idx


# ------------------------------------------------------------------------------------------------ skinned model container
class SkinnedModel:
    def __init__(self):
        self.parts: list[Part] = []

    def add(self, arrays, cls, color, weights):
        self.parts.append(Part(arrays, cls, color, weights))

    # ---- flatten parts into per-class vertex arrays
    def classes(self):
        out = {}
        for pt in self.parts:
            n = len(pt.pos)
            col = pt.color(pt.pos) if callable(pt.color) else np.tile(np.array(pt.color, float), (n, 1))
            W = pt.weights(pt.pos) if callable(pt.weights) else pt.weights
            jnt, wgt = top4(W)
            g = out.setdefault(pt.cls, dict(pos=[], nrm=[], uv=[], idx=[], col=[], jnt=[], wgt=[], n=0))
            g['pos'].append(pt.pos); g['nrm'].append(pt.nrm); g['uv'].append(pt.uv)
            g['idx'].append(np.asarray(pt.idx, int) + g['n']); g['col'].append(col); g['jnt'].append(jnt); g['wgt'].append(wgt)
            g['n'] += n
        return {k: dict(pos=np.vstack(v['pos']), nrm=np.vstack(v['nrm']), uv=np.vstack(v['uv']), idx=np.vstack(v['idx']),
                        col=np.vstack(v['col']), jnt=np.vstack(v['jnt']), wgt=np.vstack(v['wgt'])) for k, v in out.items()}

    def tri_count(self):
        return sum(len(c['idx']) for c in self.classes().values())

    # ---- glTF
    def write(self, path, mats):
        cls = self.classes()
        w = GLBWriter(generator='NEXALANE procedural assets 0.5.0 (skinned human)')
        cloth = Mat('RunnerCloth', (1, 1, 1, 1), 0.0, 0.46)
        material = {'RunnerCloth': cloth, 'matte': CLASS_MATS['matte'], 'metal': CLASS_MATS['metal'],
                    'RunnerAccent': mats['RunnerAccent'], 'RunnerGlow': mats['RunnerGlow']}
        order = [k for k in ('RunnerCloth', 'matte', 'metal', 'RunnerAccent', 'RunnerGlow') if k in cls]
        prims = []
        for k in order:
            g = cls[k]
            attrs = {"POSITION": w._accessor(g['pos'].astype('<f4'), 5126, "VEC3", 34962, minmax=True),
                     "NORMAL": w._accessor(g['nrm'].astype('<f4'), 5126, "VEC3", 34962),
                     "TEXCOORD_0": w._accessor(g['uv'].astype('<f4'), 5126, "VEC2", 34962)}
            if k in ('RunnerCloth', 'matte', 'metal'):
                attrs["COLOR_0"] = w._accessor(g['col'].astype('<f4'), 5126, "VEC4", 34962)
            attrs["JOINTS_0"] = w._accessor(g['jnt'].astype('u1'), 5121, "VEC4", 34962)
            attrs["WEIGHTS_0"] = w._accessor(g['wgt'].astype('<f4'), 5126, "VEC4", 34962)
            flat = g['idx'].reshape(-1)
            a_idx = w._accessor(flat.astype('<u2') if flat.max() < 65535 else flat.astype('<u4'), 5123 if flat.max() < 65535 else 5125, "SCALAR", 34963)
            prims.append({"attributes": attrs, "indices": a_idx, "material": w.material(material[k]), "mode": 4})
        w.meshes.append({"name": "RunnerBody", "primitives": prims})
        # nodes: 0 = scene root, 1..NB = bones, NB+1 = skinned mesh
        nodes = [{"name": "Runner", "children": [1]}]
        for i, (name, parent, _) in enumerate(rig.BONES):
            n = {"name": name, "translation": [float(v) for v in rig.local_offset(i)]}
            nodes.append(n)
        for i, (_, parent, _) in enumerate(rig.BONES):
            if parent >= 0:
                nodes[parent + 1].setdefault("children", []).append(i + 1)
        nodes.append({"name": "RunnerBody", "mesh": 0, "skin": 0})
        nodes[0]["children"].append(NB + 1)
        ibm = np.zeros((NB, 16), '<f4')
        for i, (_, _, pos) in enumerate(rig.BONES):
            m = np.eye(4); m[:3, 3] = -np.array(pos)
            ibm[i] = m.T.reshape(-1)                       # glTF matrices are column-major
        a_ibm = w._accessor(ibm, 5126, "MAT4", None)
        skin = {"name": "RunnerRig", "inverseBindMatrices": a_ibm, "joints": list(range(1, NB + 1)), "skeleton": 1}
        js = {"asset": {"version": "2.0", "generator": w.generator}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": nodes,
              "skins": [skin], "meshes": w.meshes, "materials": w.materials, "accessors": w.accessors,
              "bufferViews": w.buffer_views, "buffers": [{"byteLength": len(w.bin)}]}
        import json, struct
        jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
        while len(jb) % 4: jb += b" "
        w._align()
        total = 12 + 8 + len(jb) + 8 + len(w.bin)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(jb), 0x4E4F534A)); f.write(jb)
            f.write(struct.pack("<II", len(w.bin), 0x004E4942)); f.write(bytes(w.bin))
        return total


# ------------------------------------------------------------------------------------------------ the runner
JACKET = [  # y, rx, rz, cx, cz
    (0.84, 0.184, 0.124, 0, -0.004), (0.90, 0.184, 0.122, 0, -0.004), (0.98, 0.174, 0.115, 0, -0.002),
    (1.06, 0.164, 0.108, 0, 0.000), (1.14, 0.166, 0.111, 0, 0.002), (1.22, 0.178, 0.119, 0, 0.005),
    (1.30, 0.190, 0.127, 0, 0.007), (1.37, 0.194, 0.125, 0, 0.004), (1.425, 0.176, 0.110, 0, -0.003),
    (1.465, 0.138, 0.094, 0, -0.008), (1.50, 0.094, 0.080, 0, -0.008), (1.52, 0.074, 0.070, 0, -0.006)]
PELVIS = [(0.80, 0.110, 0.092, 0, -0.012), (0.86, 0.160, 0.112, 0, -0.012), (0.92, 0.170, 0.118, 0, -0.012),
          (0.98, 0.166, 0.114, 0, -0.008), (1.04, 0.156, 0.106, 0, -0.002)]
LEG = [  # y, rx, rz, cx (rel. to the hip), cz
    (1.00, 0.100, 0.108, 0.000, -0.006), (0.92, 0.094, 0.102, 0.003, -0.004), (0.84, 0.089, 0.097, 0.003, -0.002),
    (0.76, 0.083, 0.090, 0.002, 0.000), (0.68, 0.076, 0.082, 0.001, 0.000), (0.60, 0.067, 0.073, 0.000, 0.001),
    (0.54, 0.062, 0.067, 0.000, 0.002), (0.50, 0.060, 0.066, 0.000, 0.003), (0.45, 0.059, 0.068, 0.000, -0.003),
    (0.38, 0.058, 0.071, 0.000, -0.012), (0.30, 0.054, 0.065, 0.000, -0.011), (0.22, 0.048, 0.055, 0.000, -0.006),
    (0.15, 0.044, 0.048, 0.000, -0.002), (0.11, 0.046, 0.050, 0.000, 0.000), (0.092, 0.048, 0.052, 0.000, 0.000)]
ARM = [  # y, rx, rz  (cx follows the bone axis)
    (1.455, 0.040, 0.042), (1.43, 0.054, 0.056), (1.39, 0.054, 0.056), (1.33, 0.051, 0.054), (1.26, 0.048, 0.051),
    (1.19, 0.045, 0.048), (1.13, 0.043, 0.046), (1.10, 0.042, 0.045), (1.05, 0.042, 0.045), (0.99, 0.040, 0.043),
    (0.93, 0.037, 0.040), (0.88, 0.034, 0.037), (0.845, 0.033, 0.035)]
HEAD = [  # y, rx, rz, cx, cz   (skull top 1.806 m)
    (1.560, 0.030, 0.034, 0, 0.054), (1.575, 0.052, 0.058, 0, 0.044), (1.598, 0.066, 0.076, 0, 0.030), (1.628, 0.073, 0.087, 0, 0.016),
    (1.660, 0.077, 0.095, 0, 0.007), (1.692, 0.079, 0.099, 0, 0.001), (1.725, 0.078, 0.099, 0, -0.003), (1.758, 0.072, 0.092, 0, -0.005),
    (1.783, 0.058, 0.076, 0, -0.005), (1.798, 0.038, 0.052, 0, -0.004), (1.806, 0.014, 0.024, 0, -0.003)]
NECK = [(1.43, 0.068, 0.066, 0, 0.000), (1.49, 0.056, 0.056, 0, 0.004), (1.55, 0.051, 0.053, 0, 0.009), (1.60, 0.051, 0.055, 0, 0.014)]


def _prof(sections):
    a = np.array(sorted(sections), float)
    fx = [PchipInterpolator(a[:, 0], a[:, k]) for k in range(1, 5)]
    return lambda y: tuple(float(f(np.clip(y, a[0, 0], a[-1, 0]))) for f in fx)


jacket_profile = _prof(JACKET)
head_profile = _prof(HEAD)
_arm_r = PchipInterpolator(np.array(sorted(ARM))[:, 0], np.array(sorted(ARM))[:, 1])


def arm_radius(y): return float(_arm_r(np.clip(y, 0.845, 1.455)))


def arm_axis_x(y, side):
    """x of the arm axis at height y (A-pose: shoulder 0.19 -> elbow 0.205 -> wrist 0.215)."""
    ys = [1.43, 1.11, 0.84]; xs = [0.190, 0.205, 0.215]
    return side * float(np.interp(-y, [-v for v in ys], xs))


def front_z(y):
    rx, rz, cx, cz = jacket_profile(y)
    return cz + rz


def face_z(y, x):
    rx, rz, cx, cz = head_profile(y)
    q = float(np.clip(x / rx, -0.97, 0.97))
    return cz + rz * math.sqrt(1.0 - q * q)


def _frame(d, n_out):
    """4x4 transform whose columns are (width, thickness, length) axes for a flat lock lying along d on a surface with normal n_out."""
    z = d / (np.linalg.norm(d) + 1e-12)
    y = n_out - z * (n_out @ z); y /= np.linalg.norm(y) + 1e-12
    x = np.cross(y, z)
    m = np.eye(4); m[:3, 0], m[:3, 1], m[:3, 2] = x, y, z
    return m


def build_runner() -> SkinnedModel:
    m = SkinnedModel()
    P = PAL

    # =========================================================================== torso / pelvis
    torso_w = chain(Y, ['Hips', 'Spine', 'Chest', 'Neck'], [1.00, 1.17, 1.50], [0.07, 0.07, 0.03])

    def jacket_col(pos):
        t = np.clip((pos[:, 1] - 0.9) / 0.6, 0, 1)[:, None]
        return np.array(P['jacket']) * (1 - t) + np.array(P['jacket_hi']) * t
    m.add(tube(JACKET, 14, (False, True), 0.07, extra=(1.40, 1.46), keep=False), 'RunnerCloth', jacket_col, torso_w)
    m.add(tube(PELVIS, 14, (True, False), 0.09, keep=False), 'RunnerCloth', P['pants'], chain(Y, ['Hips', 'Spine'], [1.02], [0.04]))
    m.add(tube([(1.488, 0.086, 0.082, 0, -0.008), (1.515, 0.082, 0.077, 0, -0.006), (1.545, 0.071, 0.068, 0, -0.002)], 14, (False, False), 0.03),
          'RunnerCloth', P['jacket_hi'], chain(Y, ['Chest', 'Neck'], [1.50], [0.03]))                       # collar rim
    m.add(ellip((0.100, 0.052, 0.056), (0, 1.462, -0.082), xf=Rx(-0.30), seg=10, rings=6), 'RunnerCloth', P['hood'],
          mix(rigid('Chest'), rigid('Hood'), 0.82))                                                         # hood bundle
    for sx in (-1, 1):
        m.add(ellip((0.036, 0.046, 0.048), (sx * 0.080, 1.452, -0.050), xf=Rz(-sx * 0.35), seg=8, rings=5), 'RunnerCloth', P['hood'],
              mix(rigid('Chest'), rigid('Hood'), 0.55))
    zip_pts = [(0.0, y) for y in np.arange(0.92, 1.50, 0.04)]
    m.add(ribbon(jacket_profile, zip_pts, 0.0065, 0.0025), 'metal', P['metal'], torso_w)
    m.add(box((0.014, 0.032, 0.008), (0.0, 1.44, front_z(1.44) + 0.004), 0.0), 'RunnerAccent', P['white'], torso_w)
    for sx in (-1, 1):                                                                                      # harness straps (webbing + accent piping)
        pts_f = [(sx * (0.098 + 0.012 * t), 1.47 - 0.30 * t) for t in np.linspace(0, 1, 9)]
        pts_b = [(sx * (0.092 + 0.020 * t), 1.47 - 0.26 * t) for t in np.linspace(0, 1, 9)]
        m.add(ribbon(jacket_profile, pts_f, 0.026, 0.003, True), 'RunnerCloth', P['strap'], torso_w)
        m.add(ribbon(jacket_profile, pts_f, 0.0085, 0.0045, True), 'RunnerAccent', P['white'], torso_w)
        m.add(ribbon(jacket_profile, pts_b, 0.026, 0.003, False), 'RunnerCloth', P['strap'], torso_w)
        m.add(ribbon(jacket_profile, pts_b, 0.0085, 0.0045, False), 'RunnerAccent', P['white'], torso_w)
    m.add(ribbon(jacket_profile, [(-0.108, 1.30), (-0.036, 1.30), (0.036, 1.30), (0.108, 1.30)], 0.012, 0.005, True), 'RunnerCloth', P['strap'], torso_w)
    m.add(box((0.026, 0.026, 0.010), (0.0, 1.30, front_z(1.30) + 0.007), 0.0), 'metal', P['metal'], torso_w)
    m.add(box((0.250, 0.330, 0.100), (0.0, 1.268, -0.184), 0.035), 'matte', P['pack'], rigid('Pack'))      # pack + glow strip
    m.add(box((0.022, 0.230, 0.008), (0.0, 1.268, -0.2365), 0.0), 'RunnerGlow', P['white'], rigid('Pack'))
    for sx in (-1, 1):
        m.add(box((0.018, 0.290, 0.010), (sx * 0.100, 1.268, -0.138), 0.0), 'RunnerAccent', P['white'], mix(rigid('Chest'), rigid('Pack'), 0.5))
    m.add(tube([(0.985, 0.176, 0.119, 0, -0.003), (1.015, 0.173, 0.117, 0, -0.003)], 14, (False, False), 0.03), 'RunnerCloth', P['strap'],
          chain(Y, ['Hips', 'Spine'], [1.00], [0.05]))                                                      # waist belt

    # =========================================================================== legs
    for side, nm in ((1, 'Left'), (-1, 'Right')):
        w_leg = chain(NY, ['Hips', nm + 'UpperLeg', nm + 'LowerLeg'], [-0.985, -0.50], [0.035, 0.07])
        secs = [(y, rx, rz, side * (LX + cx), cz) for y, rx, rz, cx, cz in LEG]
        m.add(tube(secs, 12, (False, True), 0.085, extra=(0.56, 0.53, 0.47, 0.44), keep=False), 'RunnerCloth', P['pants'], w_leg)
        m.add(ellip((0.047, 0.062, 0.030), (side * LX, 0.505, 0.060), xf=Rx(0.12), seg=10, rings=6), 'matte', P['pad'], w_leg)     # knee pad
        m.add(tube([(0.552, 0.047, 0.031, side * LX, 0.062), (0.560, 0.048, 0.032, side * LX, 0.060)], 10, (False, False), 0.02), 'RunnerAccent', P['white'], w_leg)
        m.add(box((0.012, 0.130, 0.092), (side * (LX + 0.084), 0.70, 0.0), 0.0), 'RunnerCloth', C(34, 36, 44), w_leg)             # cargo pocket
        m.add(ribbon_leg(side), 'RunnerAccent', P['white'], w_leg)                                                              # side piping
        shoe_w = chain(Zc, [nm + 'Foot', nm + 'Toes'], [0.148], [0.040])
        ax, ay = side * LX, rig.ANKLE_HEIGHT
        upper = tube_z([(-0.077, 0.030, 0.040, 0, -0.030), (-0.058, 0.040, 0.056, 0, -0.024), (-0.020, 0.044, 0.060, 0, -0.022),
                        (0.030, 0.045, 0.048, 0, -0.034), (0.085, 0.049, 0.036, 0, -0.045), (0.145, 0.051, 0.030, 0, -0.050),
                        (0.195, 0.045, 0.026, 0, -0.053), (0.226, 0.028, 0.021, 0, -0.056), (0.238, 0.010, 0.010, 0, -0.058)], 10, (True, True), 0.045, keep=True)
        sole = tube_z([(-0.080, 0.032, 0.0125, 0, -0.0675), (-0.045, 0.046, 0.0125, 0, -0.0675), (0.000, 0.049, 0.0125, 0, -0.0675),
                       (0.090, 0.052, 0.0125, 0, -0.0675), (0.170, 0.054, 0.0125, 0, -0.0675), (0.215, 0.046, 0.0125, 0, -0.0675),
                       (0.243, 0.026, 0.0125, 0, -0.0675)], 10, (True, True), 0.06, keep=True)
        m.add(shift(upper, (ax, ay, 0)), 'RunnerCloth', P['shoe_up'], shoe_w)
        m.add(shift(sole, (ax, ay, 0)), 'matte', P['shoe_sole'], shoe_w)
        m.add(box((0.012, 0.030, 0.020), (ax, ay + 0.032, -0.076), 0.0), 'RunnerAccent', P['white'], shoe_w)
        m.add(box((0.004, 0.018, 0.120), (ax + side * 0.0465, ay - 0.034, 0.075), 0.0), 'RunnerAccent', P['white'], shoe_w)

    # =========================================================================== arms
    for side, nm in ((1, 'Left'), (-1, 'Right')):
        w_arm = chain(NY, [nm + 'UpperArm', nm + 'LowerArm', nm + 'Hand'], [-1.11, -0.835], [0.06, 0.03])
        secs = [(y, rx, rz, arm_axis_x(y, side), 0.0) for y, rx, rz in ARM]
        m.add(tube(secs, 10, (False, False), 0.075, extra=(1.16, 1.08, 1.06), keep=False), 'RunnerCloth', P['jacket'], w_arm)
        cap_w = mix(rigid(nm + 'UpperArm'), chain(Y, [nm + 'UpperArm', nm + 'Shoulder'], [1.46], [0.05]), lambda p: np.clip((p[:, 1] - 1.40) / 0.08, 0, 0.7))
        m.add(ellip((0.056, 0.052, 0.056), (side * 0.190, 1.425, 0.0), seg=10, rings=6), 'RunnerCloth', P['jacket_hi'], cap_w)     # deltoid
        for yb in (1.265, 0.965):
            rr = arm_radius(yb) + 0.0015
            m.add(tube([(yb - 0.012, rr, rr + 0.002, arm_axis_x(yb, side), 0.0), (yb + 0.012, rr, rr + 0.002, arm_axis_x(yb, side), 0.0)], 10, (False, False), 0.02),
                  'RunnerAccent', P['white'], w_arm)
        m.add(tube([(0.835, 0.037, 0.038, arm_axis_x(0.84, side), 0.0), (0.875, 0.037, 0.039, arm_axis_x(0.875, side), 0.0)], 10, (False, False), 0.02),
              'RunnerCloth', P['strap'], rigid(nm + 'LowerArm'))                                            # cuff
        hx = side * 0.215                                                                                    # glove / loosely clenched fist
        hand_w = rigid(nm + 'Hand')
        m.add(box((0.032, 0.092, 0.086), (hx, 0.785, 0.0), 0.014), 'matte', P['glove'], hand_w)
        m.add(box((0.040, 0.046, 0.084), (hx - side * 0.024, 0.730, 0.0), 0.016), 'matte', P['glove_hi'], hand_w)
        m.add(ellip((0.016, 0.014, 0.026), (hx + side * 0.002, 0.768, 0.052), xf=Rx(0.5), seg=8, rings=4), 'matte', P['glove'], hand_w)
        m.add(ellip((0.011, 0.012, 0.020), (hx - side * 0.014, 0.738, 0.058), xf=Rx(0.9), seg=6, rings=4), 'matte', P['skin'], hand_w)
        for zi in (-0.020, 0.020):
            m.add(ellip((0.011, 0.012, 0.021), (hx - side * 0.044, 0.724, zi), seg=6, rings=4), 'matte', P['skin'], hand_w)         # fingertips
        m.add(box((0.020, 0.012, 0.070), (hx + side * 0.020, 0.800, 0.0), 0.0), 'RunnerAccent', P['white'], hand_w)
    wd = arm_axis_x(0.915, 1)                                                                                # wrist device (left)
    m.add(tube([(0.895, 0.039, 0.041, wd, 0.0), (0.935, 0.039, 0.041, wd, 0.0)], 10, (False, False), 0.02), 'RunnerAccent', P['white'], rigid('LeftLowerArm'))
    m.add(box((0.014, 0.046, 0.046), (wd + 0.042, 0.915, 0.0), 0.0), 'matte', P['watch'], rigid('LeftLowerArm'))
    m.add(box((0.004, 0.030, 0.030), (wd + 0.050, 0.915, 0.0), 0.0), 'RunnerGlow', P['white'], rigid('LeftLowerArm'))

    # =========================================================================== neck + head
    neck_w = chain(Y, ['Chest', 'Neck', 'Head'], [1.455, 1.56], [0.03, 0.03])
    m.add(tube(NECK, 12, (False, False), 0.045), 'matte', P['skin_shade'], neck_w)
    head_w = rigid('Head')
    m.add(tube(HEAD, 16, (True, True), 0.03, extra=(1.69, 1.71)), 'matte', P['skin'], head_w)
    for sx in (-1, 1):
        m.add(ellip((0.0075, 0.027, 0.0175), (sx * 0.0795, 1.678, -0.008), xf=Ry(sx * 0.2), seg=6, rings=4), 'matte', P['skin_shade'], head_w)   # ears
    ze = face_z(1.655, 0.0)                                                                                  # nose
    m.add(ellip((0.0105, 0.025, 0.016), (0, 1.668, ze + 0.007), xf=Rx(-0.38), seg=8, rings=5), 'matte', P['skin'], head_w)
    m.add(ellip((0.0125, 0.0095, 0.0125), (0, 1.642, ze + 0.013), seg=8, rings=4), 'matte', P['skin'], head_w)
    for sx in (-1, 1):
        m.add(ellip((0.0075, 0.0070, 0.0095), (sx * 0.0135, 1.643, ze + 0.008), seg=6, rings=4), 'matte', P['skin_shade'], head_w)
    for sx in (-1, 1):                                                                                       # eyes, lids, brows
        ex, ey = sx * 0.0345, 1.692
        zf = face_z(ey, ex)
        ez = zf - 0.0058
        m.add(ellip((0.0138, 0.0120, 0.0130), (ex, ey, ez), seg=8, rings=5), 'matte', P['eye_w'], head_w)
        m.add(ellip((0.0082, 0.0082, 0.0030), (ex, ey - 0.0005, ez + 0.0118), seg=8, rings=3), 'matte', P['iris'], head_w)
        m.add(ellip((0.0150, 0.0070, 0.0142), (ex, ey + 0.0078, ez + 0.0014), xf=Rz(-sx * 0.10), seg=8, rings=4), 'matte', P['skin_shade'], head_w)
        for k, (dx, dy, rot) in enumerate(((-0.014, -0.002, 0.30), (0.014, 0.003, -0.22))):                 # two-piece, slightly furrowed brow
            zb = face_z(1.722, ex + sx * dx)
            m.add(ellip((0.0155, 0.0052, 0.0075), (ex + sx * dx * 0.55, 1.7205 + dy, zb + 0.0005), xf=Rz(sx * rot) @ Rx(-0.12), seg=6, rings=3),
                  'matte', P['brow'], head_w)
    zm = face_z(1.603, 0.0)                                                                                  # mouth
    m.add(ellip((0.0215, 0.0048, 0.0105), (0, 1.6055, zm + 0.0015), xf=Rx(0.12), seg=8, rings=4), 'matte', P['lips'], head_w)
    m.add(ellip((0.0190, 0.0062, 0.0112), (0, 1.5935, zm + 0.0020), xf=Rx(-0.05), seg=8, rings=4), 'matte', P['lips'], head_w)
    m.add(box((0.040, 0.0035, 0.005), (0, 1.5992, zm + 0.0005), 0.0), 'matte', C(70, 40, 38), head_w)
    # hair: skull cap + overlapping swept-back locks (volume, not spikes)
    ctr = np.array([0.0, 1.735, -0.012]); rad = np.array([0.0838, 0.0800, 0.1040])
    cap = ellip(tuple(rad), tuple(ctr), xf=Rx(0.10), seg=12, rings=7)
    cp, cn, cu, ct = cap                                                    # trim the front of the cap: the fringe locks form the hairline
    cent = cp[ct].mean(1)
    keep = ~((cent[:, 2] > 0.030) & (cent[:, 1] < 1.776 + 0.9 * cent[:, 0] ** 2))
    cap = (cp, cn, cu, ct[keep])
    m.add(cap, 'matte', P['hair'], mix(rigid('Head'), rigid('HairBack'), lambda p: np.clip((-p[:, 2] - 0.05) / 0.07, 0, 0.55)))
    locks = [  # (azimuth from the front, elevation, length, width)
        (-0.55, 0.30, 0.085, 0.020), (-0.18, 0.28, 0.095, 0.021), (0.20, 0.28, 0.095, 0.021), (0.58, 0.30, 0.085, 0.020),
        (-0.70, 0.78, 0.095, 0.022), (-0.25, 0.78, 0.105, 0.023), (0.25, 0.78, 0.105, 0.023), (0.70, 0.78, 0.095, 0.022),
        (-0.95, 1.18, 0.095, 0.022), (0.0, 1.22, 0.105, 0.024), (0.95, 1.18, 0.095, 0.022),
        (-1.45, 0.32, 0.085, 0.020), (1.45, 0.32, 0.085, 0.020), (-1.95, 0.40, 0.085, 0.020), (1.95, 0.40, 0.085, 0.020),
        (-2.55, 0.34, 0.080, 0.020), (2.55, 0.34, 0.080, 0.020), (3.14, 0.40, 0.080, 0.022)]
    for th, el, ln, wd_ in locks:
        dirn = np.array([math.sin(th) * math.cos(el), math.sin(el), math.cos(th) * math.cos(el)])
        base = ctr + dirn * rad * 0.99
        tang = np.array([-math.sin(th) * math.sin(el) * rad[0], math.cos(el) * rad[1], -math.cos(th) * math.sin(el) * rad[2]])
        tang /= np.linalg.norm(tang) + 1e-12
        sweep = tang * 0.55 + np.array([0.0, 0.0, -1.0]) * 0.55 + np.array([0.0, -0.25, 0.0]) * (1.0 if abs(th) > 1.3 else 0.0)
        sweep /= np.linalg.norm(sweep)
        outn = dirn / (np.linalg.norm(dirn) + 1e-12)
        fr = _frame(sweep, outn * 0.85 + np.array([0, 0.15, 0]))
        cen = base + sweep * ln * 0.45 + outn * 0.006
        lock = ellip((wd_, 0.0095, ln * 0.55), (0, 0, 0), xf=fr, seg=6, rings=4)
        lock = shift(lock, cen)
        sec = 'HairFront' if dirn[2] > 0.0 else 'HairBack'

        def wfun(p, base=base, sweep=sweep, ln=ln, sec=sec):
            t = np.clip(((p - base) @ sweep) / ln, 0, 1) ** 1.2
            return mix(rigid('Head'), rigid(sec), t * 0.9)(p)
        m.add(lock, 'matte', P['hair'], wfun)
    return m


def ribbon_leg(side):
    """Orange piping down the outside of a trouser leg (follows the LEG profile)."""
    secs = [(y, rx, rz, side * (LX + cx), cz) for y, rx, rz, cx, cz in LEG]
    a = np.array(sorted(secs), float)
    f = [PchipInterpolator(a[:, 0], a[:, k]) for k in range(1, 5)]
    ys = np.linspace(0.12, 0.99, 22)
    Pp, Nn = [], []
    for y in ys:
        rx, rz, cx, cz = [float(g(y)) for g in f]
        for dz in (-0.0065, 0.0065):
            q = dz / rz
            x = cx + side * rx * math.sqrt(max(1e-6, 1 - q * q)) + side * 0.0025
            n = np.array([side * 1.0, 0.0, q * rz / rx * 0.5]); n /= np.linalg.norm(n)
            Pp.append((x, y, cz + dz)); Nn.append(n)
    Pp = np.array(Pp); Nn = np.array(Nn)
    idx = []
    for r in range(len(ys) - 1):
        a_, b_, c_, d_ = 2 * r, 2 * r + 1, 2 * r + 2, 2 * r + 3
        idx += [[a_, b_, d_], [a_, d_, c_]]
    idx = fix_winding(Pp, Nn, idx)
    return Pp, Nn, np.zeros((len(Pp), 2)), idx


if __name__ == '__main__':
    mdl = build_runner()
    print('triangles', mdl.tri_count())
    for k, v in mdl.classes().items():
        print(f'  {k:14s} verts={len(v["pos"]):5d} tris={len(v["idx"]):5d}')
