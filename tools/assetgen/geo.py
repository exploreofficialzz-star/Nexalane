"""Tiny procedural-modelling toolkit that emits glTF-ready (CCW, outward-facing) triangle meshes.

Conventions: +Y up, +Z is the model's FRONT (the direction the runner travels), units are metres.
"""
from __future__ import annotations
import math
import numpy as np

# ---------------------------------------------------------------- transforms
def T(x=0.0, y=0.0, z=0.0):
    m = np.eye(4); m[:3, 3] = (x, y, z); return m

def S(x=1.0, y=None, z=None):
    y = x if y is None else y; z = x if z is None else z
    m = np.eye(4); m[0, 0], m[1, 1], m[2, 2] = x, y, z; return m

def Rx(a):
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4); m[1, 1], m[1, 2], m[2, 1], m[2, 2] = c, -s, s, c; return m

def Ry(a):
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4); m[0, 0], m[0, 2], m[2, 0], m[2, 2] = c, s, -s, c; return m

def Rz(a):
    c, s = math.cos(a), math.sin(a)
    m = np.eye(4); m[0, 0], m[0, 1], m[1, 0], m[1, 1] = c, -s, s, c; return m

def compose(*ms):
    out = np.eye(4)
    for m in ms: out = out @ m
    return out

def quat_from_euler(rx=0.0, ry=0.0, rz=0.0):
    """XYZ-order euler (radians) -> glTF quaternion [x,y,z,w]."""
    cx, sx = math.cos(rx / 2), math.sin(rx / 2)
    cy, sy = math.cos(ry / 2), math.sin(ry / 2)
    cz, sz = math.cos(rz / 2), math.sin(rz / 2)
    # q = qz * qy * qx  (apply X first, then Y, then Z)
    w = cx * cy * cz + sx * sy * sz
    x = sx * cy * cz - cx * sy * sz
    y = cx * sy * cz + sx * cy * sz
    z = cx * cy * sz - sx * sy * cz
    return [x, y, z, w]

def _apply(xf, pos, nrm):
    if xf is None: return pos, nrm
    p = (np.c_[pos, np.ones(len(pos))] @ xf.T)[:, :3]
    n = nrm @ np.linalg.inv(xf[:3, :3])      # row-vector form of the inverse-transpose rule
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return p, n

# ---------------------------------------------------------------- mesh container
class Mesh:
    """Collects geometry per material name. One Mesh -> one glTF mesh with one primitive per material."""
    def __init__(self):
        self.groups: dict[str, dict] = {}

    def add(self, mat: str, pos, nrm, uv, tris, xf=None):
        pos = np.asarray(pos, float); nrm = np.asarray(nrm, float); uv = np.asarray(uv, float)
        tris = np.asarray(tris, int).reshape(-1, 3)
        pos, nrm = _apply(xf, pos, nrm)
        g = self.groups.setdefault(mat, dict(pos=[], nrm=[], uv=[], idx=[], n=0))
        g['pos'].append(pos); g['nrm'].append(nrm); g['uv'].append(uv); g['idx'].append(tris + g['n']); g['n'] += len(pos)
        return self

    def merge(self, other: 'Mesh', xf=None):
        for mat, g in other.groups.items():
            pos = np.vstack(g['pos']); nrm = np.vstack(g['nrm']); uv = np.vstack(g['uv'])
            idx = np.vstack(g['idx'])
            self.add(mat, pos, nrm, uv, idx, xf)
        return self

    def arrays(self, mat):
        g = self.groups[mat]
        return (np.vstack(g['pos']), np.vstack(g['nrm']), np.vstack(g['uv']), np.vstack(g['idx']))

    def materials(self):
        return list(self.groups.keys())

    def tri_count(self):
        return sum(sum(len(i) for i in g['idx']) for g in self.groups.values())

    # ---- convenience wrappers -------------------------------------------------
    @staticmethod
    def _cx(center, xf):
        base = T(*center)
        return base if xf is None else base @ xf      # rotate/scale about the part's own centre, then move it

    def box(self, mat, size, center=(0, 0, 0), bevel=0.0, xf=None, uv=1.0, uv_off=(0.0, 0.0)):
        p, n, u, t = rounded_box(size, bevel, uv, uv_off)
        self.add(mat, p, n, u, t, self._cx(center, xf)); return self

    def cyl(self, mat, r_top, r_bot, h, seg=16, center=(0, 0, 0), xf=None, caps=True, uv=1.0, smooth=True):
        p, n, u, t = cylinder(r_top, r_bot, h, seg, caps, uv, smooth)
        self.add(mat, p, n, u, t, self._cx(center, xf)); return self

    def sphere(self, mat, r, seg=16, rings=10, center=(0, 0, 0), xf=None, scale=(1, 1, 1)):
        p, n, u, t = ellipsoid((r * scale[0], r * scale[1], r * scale[2]), seg, rings)
        self.add(mat, p, n, u, t, self._cx(center, xf)); return self

    def loft(self, mat, sections, seg=14, center=(0, 0, 0), xf=None, caps=(True, True), uv=1.0):
        p, n, u, t = loft(sections, seg, caps, uv)
        self.add(mat, p, n, u, t, self._cx(center, xf)); return self

    def disc(self, mat, r, y=0.0, up=True, seg=24, xf=None):
        p, n, u, t = disc(r, y, up, seg)
        self.add(mat, p, n, u, t, xf); return self

    def quad(self, mat, p0, p1, p2, p3, uvs=((0, 1), (1, 1), (1, 0), (0, 0)), xf=None, double=False):
        """Quad given CCW (as seen from the front). p0=bottom-left, p1=bottom-right, p2=top-right, p3=top-left."""
        P = np.array([p0, p1, p2, p3], float)
        nrm = np.cross(P[1] - P[0], P[3] - P[0]); nrm /= np.linalg.norm(nrm) + 1e-12
        N = np.tile(nrm, (4, 1)); UV = np.array(uvs, float)
        tris = [[0, 1, 2], [0, 2, 3]]
        self.add(mat, P, N, UV, tris, xf)
        if double:
            self.add(mat, P[::-1], -N, UV[::-1], tris, xf)
        return self

    def extrude(self, mat, poly_xy, depth, xf=None, uv=1.0):
        p, n, u, t = extrude_polygon(poly_xy, depth, uv)
        self.add(mat, p, n, u, t, xf); return self

# ---------------------------------------------------------------- primitives
_FACES = [  # (normal, right, up) right-handed, viewed from outside
    ((1, 0, 0), (0, 0, -1), (0, 1, 0)),
    ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
    ((0, 1, 0), (1, 0, 0), (0, 0, -1)),
    ((0, -1, 0), (1, 0, 0), (0, 0, 1)),
    ((0, 0, 1), (1, 0, 0), (0, 1, 0)),
    ((0, 0, -1), (-1, 0, 0), (0, 1, 0)),
]

def rounded_box(size, bevel=0.0, uv=1.0, uv_off=(0.0, 0.0)):
    su, sv = (uv if isinstance(uv, (tuple, list)) else (uv, uv))
    ou, ov = uv_off
    h = np.array(size, float) / 2.0
    b = min(bevel, float(h.min()) * 0.9)
    pos, nrm, uvs, idx = [], [], [], []
    for (n, r, u) in _FACES:
        n = np.array(n, float); r = np.array(r, float); u = np.array(u, float)
        hn = abs(n @ h); hr = abs(r @ h); hu = abs(u @ h)
        if b <= 1e-6:
            base = len(pos)
            for (sr, sgn_u) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = n * hn + r * hr * sr + u * hu * sgn_u
                pos.append(p); nrm.append(n); uvs.append((sr * hr * su + hr * su + ou, -(sgn_u * hu) * sv + ov))
            idx += [[base, base + 1, base + 2], [base, base + 2, base + 3]]
        else:
            rc = [-hr, -hr + b, hr - b, hr]; uc = [-hu, -hu + b, hu - b, hu]
            base = len(pos)
            for j in range(4):
                for i in range(4):
                    p0 = n * hn + r * rc[i] + u * uc[j]
                    inner = np.clip(p0, -(h - b), (h - b))
                    d = p0 - inner
                    nn = d / (np.linalg.norm(d) + 1e-12)
                    pos.append(inner + nn * b); nrm.append(nn)
                    uvs.append(((rc[i] + hr) * su + ou, -uc[j] * sv + ov))
            for j in range(3):
                for i in range(3):
                    a = base + j * 4 + i; bq = a + 1; c = a + 5; d_ = a + 4
                    idx += [[a, bq, c], [a, c, d_]]
    return np.array(pos), np.array(nrm), np.array(uvs), np.array(idx)

def cylinder(r_top, r_bot, h, seg=16, caps=True, uv=1.0, smooth=True):
    """Y-axis cylinder/cone frustum centred on the origin."""
    pos, nrm, uvs, idx = [], [], [], []
    slope = (r_bot - r_top) / h if h else 0.0
    for i in range(seg + 1):
        th = 2 * math.pi * i / seg
        c, s = math.cos(th), math.sin(th)
        n = np.array([c, slope, s]); n /= np.linalg.norm(n)
        for (y, r, v) in ((-h / 2, r_bot, 0.0), (h / 2, r_top, 1.0)):
            pos.append((r * c, y, r * s)); nrm.append(n)
            uvs.append((i / seg * (2 * math.pi * max(r_top, r_bot)) * uv, -(y) * uv))
    for i in range(seg):
        bl, tl = i * 2, i * 2 + 1
        br, tr = (i + 1) * 2, (i + 1) * 2 + 1
        # increasing theta is to the viewer's LEFT from outside -> CCW: BL(th_{i+1}) ... use (br,bl,tl,tr)
        idx += [[br, bl, tl], [br, tl, tr]]
    if caps:
        for (y, r, ny) in ((h / 2, r_top, 1.0), (-h / 2, r_bot, -1.0)):
            if r <= 1e-6: continue
            base = len(pos)
            pos.append((0, y, 0)); nrm.append((0, ny, 0)); uvs.append((0.5, 0.5))
            for i in range(seg + 1):
                th = 2 * math.pi * i / seg
                pos.append((r * math.cos(th), y, r * math.sin(th))); nrm.append((0, ny, 0))
                uvs.append((0.5 + 0.5 * math.cos(th), 0.5 + 0.5 * math.sin(th)))
            for i in range(seg):
                if ny > 0: idx.append([base, base + i + 2, base + i + 1])
                else: idx.append([base, base + i + 1, base + i + 2])
    return np.array(pos), np.array(nrm), np.array(uvs), np.array(idx)

def disc(r, y=0.0, up=True, seg=24, uv_scale=1.0):
    """Flat circular cap in the XZ plane at height y; UV maps the disc onto the unit square."""
    pos = [(0, y, 0)]; nrm = [(0, 1.0 if up else -1.0, 0)]; uvs = [(0.5, 0.5)]
    for i in range(seg + 1):
        th = 2 * math.pi * i / seg
        pos.append((r * math.cos(th), y, r * math.sin(th))); nrm.append((0, 1.0 if up else -1.0, 0))
        uvs.append((0.5 + 0.5 * math.cos(th), 0.5 + 0.5 * math.sin(th)))
    idx = [[0, i + 2, i + 1] if up else [0, i + 1, i + 2] for i in range(seg)]
    return np.array(pos), np.array(nrm), np.array(uvs), np.array(idx)

def vertex_normals(pos, tris):
    pos = np.asarray(pos, float); tris = np.asarray(tris, int)
    fn = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
    vn = np.zeros_like(pos)
    for k in range(3): np.add.at(vn, tris[:, k], fn)
    vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
    return vn

def loft(sections, seg=14, caps=(True, True), uv=1.0):
    """Lofted elliptical tube along +Y. sections: list of (y, rx, rz, cx, cz) bottom->top.
    Vertex order around the ring is such that triangles wind CCW when seen from outside."""
    pos, uvs = [], []
    n_s = len(sections)
    for si, (y, rx, rz, cx, cz) in enumerate(sections):
        for i in range(seg + 1):
            th = 2 * math.pi * i / seg
            pos.append((cx + rx * math.cos(th), y, cz + rz * math.sin(th)))
            uvs.append((i / seg, si / max(1, n_s - 1)))
    idx = []
    for si in range(n_s - 1):
        for i in range(seg):
            a = si * (seg + 1) + i; b = a + 1; c = a + (seg + 1) + 1; d = a + (seg + 1)
            idx += [[b, a, d], [b, d, c]]
    pos = np.array(pos)
    # smooth normals from geometry (ring wraps: merge the seam)
    nrm = vertex_normals(pos, idx)
    for si in range(n_s):
        a = si * (seg + 1); b = a + seg
        avg = nrm[a] + nrm[b]; avg /= np.linalg.norm(avg) + 1e-12
        nrm[a] = avg; nrm[b] = avg
    pos = list(map(tuple, pos)); nrm = list(map(tuple, nrm)); uvs = list(uvs); idx = [list(t) for t in idx]
    for (flag, si, ny) in ((caps[0], 0, -1.0), (caps[1], n_s - 1, 1.0)):
        if not flag: continue
        y, rx, rz, cx, cz = sections[si]
        if rx <= 1e-6 or rz <= 1e-6: continue
        base = len(pos)
        pos.append((cx, y, cz)); nrm.append((0, ny, 0)); uvs.append((0.5, 0.5))
        for i in range(seg + 1):
            th = 2 * math.pi * i / seg
            pos.append((cx + rx * math.cos(th), y, cz + rz * math.sin(th))); nrm.append((0, ny, 0))
            uvs.append((0.5 + 0.5 * math.cos(th), 0.5 + 0.5 * math.sin(th)))
        for i in range(seg):
            if ny > 0: idx.append([base, base + i + 2, base + i + 1])
            else: idx.append([base, base + i + 1, base + i + 2])
    return np.array(pos), np.array(nrm), np.array(uvs), np.array(idx)

def ellipsoid(radii, seg=16, rings=10):
    rx, ry, rz = radii
    secs = []
    for k in range(rings + 1):
        ph = math.pi * k / rings
        y = -ry * math.cos(ph)
        s = math.sin(ph)
        secs.append((y, max(rx * s, 1e-5), max(rz * s, 1e-5), 0.0, 0.0))
    p, n, u, t = loft(secs, seg, caps=(False, False))
    return p, n, u, t

def capsule_sections(length, r0, r1=None, rings=5, cx=0.0, cz=0.0):
    """Sections for a vertical tapered capsule spanning y in [0, length] (hemispherical ends).
    Use with loft(..., caps=(False, False)). Requires length >= r0 + r1."""
    r1 = r0 if r1 is None else r1
    secs = []
    for k in range(rings + 1):          # bottom hemisphere, pole -> equator
        a = (math.pi / 2) * (k / rings)
        secs.append((r0 - r0 * math.cos(a), max(r0 * math.sin(a), 1e-5), max(r0 * math.sin(a), 1e-5), cx, cz))
    for k in range(rings + 1):          # top hemisphere, equator -> pole
        a = (math.pi / 2) * (k / rings)
        secs.append((length - r1 + r1 * math.sin(a), max(r1 * math.cos(a), 1e-5), max(r1 * math.cos(a), 1e-5), cx, cz))
    return secs

def _ear_clip(poly):
    poly = list(range(len(poly))), np.array(poly, float)
    idxs, pts = poly
    def area2(a, b, c): return (pts[b][0]-pts[a][0])*(pts[c][1]-pts[a][1])-(pts[b][1]-pts[a][1])*(pts[c][0]-pts[a][0])
    # ensure CCW
    s = sum(pts[i][0]*pts[(i+1) % len(pts)][1]-pts[(i+1) % len(pts)][0]*pts[i][1] for i in range(len(pts)))
    if s < 0: idxs.reverse()
    tris = []
    guard = 0
    while len(idxs) > 3 and guard < 10000:
        guard += 1
        n = len(idxs); ear = False
        for k in range(n):
            a, b, c = idxs[(k - 1) % n], idxs[k], idxs[(k + 1) % n]
            if area2(a, b, c) <= 1e-12: continue
            ok = True
            for m in idxs:
                if m in (a, b, c): continue
                p = pts[m]
                d1 = area2(a, b, m); d2 = area2(b, c, m); d3 = area2(c, a, m)
                if d1 >= -1e-12 and d2 >= -1e-12 and d3 >= -1e-12: ok = False; break
            if ok:
                tris.append((a, b, c)); idxs.pop(k); ear = True; break
        if not ear: break
    if len(idxs) == 3: tris.append(tuple(idxs))
    return tris

def extrude_polygon(poly_xy, depth, uv=1.0):
    """Extrude a simple polygon (x,y) along Z from -depth/2..+depth/2. Front cap faces +Z."""
    poly = [tuple(p) for p in poly_xy]
    n = len(poly)
    pos, nrm, uvs, idx = [], [], [], []
    tris = _ear_clip(poly)
    for (z, nz) in ((depth / 2, 1.0), (-depth / 2, -1.0)):
        base = len(pos)
        for (x, y) in poly:
            pos.append((x, y, z)); nrm.append((0, 0, nz)); uvs.append((x * uv, -y * uv))
        for (a, b, c) in tris:
            idx.append([base + a, base + b, base + c] if nz > 0 else [base + a, base + c, base + b])
    # side walls (polygon assumed CCW after _ear_clip normalisation of orientation)
    pts = np.array(poly, float)
    s = sum(pts[i][0]*pts[(i+1) % n][1]-pts[(i+1) % n][0]*pts[i][1] for i in range(n))
    order = list(range(n)) if s > 0 else list(range(n))[::-1]
    for k in range(n):
        a = order[k]; b = order[(k + 1) % n]
        e = pts[b] - pts[a]; nn = np.array([e[1], -e[0], 0.0]); nn /= np.linalg.norm(nn) + 1e-12
        base = len(pos)
        for (x, y, z) in ((pts[a][0], pts[a][1], -depth / 2), (pts[b][0], pts[b][1], -depth / 2), (pts[b][0], pts[b][1], depth / 2), (pts[a][0], pts[a][1], depth / 2)):
            pos.append((x, y, z)); nrm.append(tuple(nn)); uvs.append((x * uv, -y * uv))
        idx += [[base, base + 1, base + 2], [base, base + 2, base + 3]]
    return np.array(pos), np.array(nrm), np.array(uvs), np.array(idx)

def check_winding(mesh: Mesh):
    """Return fraction of triangles whose geometric normal agrees with the stored vertex normals."""
    ok = tot = 0
    for mat in mesh.materials():
        p, n, _, t = mesh.arrays(mat)
        fn = np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]])
        area = np.linalg.norm(fn, axis=1)
        good = area > 1e-12
        avg = n[t[:, 0]] + n[t[:, 1]] + n[t[:, 2]]
        d = (fn * avg).sum(1)
        ok += int(((d > 0) & good).sum()); tot += int(good.sum())
    return ok / max(1, tot)
