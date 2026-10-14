"""Tiny software renderer for the skinned cartoon runner: loads runner_base.glb, poses it with linear-blend skinning and
rasterises it with back-face culling (so the inverted-hull outline behaves exactly like in the engine), cel-style shading,
optional supersampling and a transparent background.  Used for docs/previews and for the app icon; not needed at run time.
"""
from __future__ import annotations
import numpy as np
from PIL import Image
from .validate import read_glb, accessor
from . import toon_rig as rig


def load(path):
    js, b = read_glb(path)
    skin = js['skins'][0]
    ibm = accessor(js, b, skin['inverseBindMatrices']).astype(float).reshape(-1, 4, 4).transpose(0, 2, 1)
    names = [js['nodes'][j]['name'] for j in skin['joints']]
    mesh_node = next(n for n in js['nodes'] if 'skin' in n)
    prims = []
    for p in js['meshes'][mesh_node['mesh']]['primitives']:
        at = p['attributes']
        m = js['materials'][p['material']]
        pbr = m.get('pbrMetallicRoughness', {})
        prims.append(dict(
            P=accessor(js, b, at['POSITION']).astype(float), N=accessor(js, b, at['NORMAL']).astype(float),
            idx=accessor(js, b, p['indices']).reshape(-1, 3).astype(int),
            C=accessor(js, b, at['COLOR_0']).astype(float) if 'COLOR_0' in at else None,
            J=accessor(js, b, at['JOINTS_0']).astype(int), W=accessor(js, b, at['WEIGHTS_0']).astype(float),
            unlit='KHR_materials_unlit' in m.get('extensions', {}), base=np.array(pbr.get('baseColorFactor', [1, 1, 1, 1]), float),
            emi=np.array(m.get('emissiveFactor', [0, 0, 0]), float), rough=pbr.get('roughnessFactor', 1.0), name=m.get('name', '')))
    return dict(js=js, prims=prims, ibm=ibm, names=names)


def posed(sk, wr, wp):
    M = np.zeros((len(wr), 4, 4))
    for i in range(len(wr)):
        M[i][:3, :3] = wr[i]; M[i][:3, 3] = wp[i]; M[i][3, 3] = 1.0
    skin_m = np.einsum('bij,bjk->bik', M, sk['ibm'])
    out = []
    for p in sk['prims']:
        Ph = np.c_[p['P'], np.ones(len(p['P']))]
        P = np.zeros((len(Ph), 3)); N = np.zeros((len(Ph), 3))
        for k in range(4):
            w = p['W'][:, k]
            if not w.any():
                continue
            m = skin_m[p['J'][:, k]]
            P += w[:, None] * np.einsum('nij,nj->ni', m[:, :3, :], Ph)
            N += w[:, None] * np.einsum('nij,nj->ni', m[:, :3, :3], p['N'])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        q = dict(p); q['P'] = P; q['N'] = N
        out.append(q)
    return out


def rest_pose():
    wr = [np.eye(3) for _ in rig.BONES]
    wp = [np.array(b[2], float) for b in rig.BONES]
    return wr, wp


def _basis(yaw, pitch):
    ya, pa = np.radians(yaw), np.radians(pitch)
    Ry = np.array([[np.cos(ya), 0, np.sin(ya)], [0, 1, 0], [-np.sin(ya), 0, np.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(pa), -np.sin(pa)], [0, np.sin(pa), np.cos(pa)]])
    return Rx @ Ry


def render(prims, size=(480, 640), yaw=30, pitch=8, center=(0.0, 0.95, 0.0), fit=1.15, ssaa=2, light=(0.45, 0.75, 0.55),
           bg=None, cam_dist=7.0, cull=True, bands=True, tint=None, exposure=1.0):
    """fit = half of the visible world height at the centre.  Returns an RGBA PIL image (transparent where nothing is drawn
    unless bg=(r, g, b) is given).  tint: optional (r, g, b) 0..1 multiplier applied to RunnerAccent surfaces."""
    W0, H0 = size
    W, H = W0 * ssaa, H0 * ssaa
    R = _basis(yaw, pitch)
    center = np.array(center, float)
    f = 0.5 * H * cam_dist / fit                                  # focal length in pixels so that `fit` metres span half the image
    L = np.array(light, float); L /= np.linalg.norm(L); Lc = L @ R.T
    rgb = np.zeros((H, W, 3)); alpha = np.zeros((H, W))
    zbuf = np.full((H, W), 1e18)
    for pr in prims:
        Pc = (pr['P'] - center) @ R.T
        depth = cam_dist - Pc[:, 2]
        sx = W / 2 + f * Pc[:, 0] / depth; sy = H / 2 - f * Pc[:, 1] / depth
        Nc = pr['N'] @ R.T
        base = pr['base'][:3].copy()
        emi = pr['emi']
        accent = pr['name'] == 'RunnerAccent'
        if accent and tint is not None:
            base = np.array(tint, float)
        idx = pr['idx']
        if cull:
            e1 = Pc[idx[:, 1]] - Pc[idx[:, 0]]; e2 = Pc[idx[:, 2]] - Pc[idx[:, 0]]
            front = (e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) > 0
            idx = idx[front]
        for a, b_, c in idx:
            x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b_], sy[b_], sx[c], sy[c]
            minx = int(max(0, np.floor(min(x0, x1, x2)))); maxx = int(min(W - 1, np.ceil(max(x0, x1, x2))))
            miny = int(max(0, np.floor(min(y0, y1, y2)))); maxy = int(min(H - 1, np.ceil(max(y0, y1, y2))))
            if minx > maxx or miny > maxy:
                continue
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9:
                continue
            xs, ys = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            w0 = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / den
            w1 = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any():
                continue
            z = w0 * depth[a] + w1 * depth[b_] + w2 * depth[c]
            sub = zbuf[miny:maxy + 1, minx:maxx + 1]
            upd = m & (z < sub)
            if not upd.any():
                continue
            if pr['unlit']:
                col = np.broadcast_to(base, (*w0.shape, 3))
            else:
                nrm = w0[..., None] * Nc[a] + w1[..., None] * Nc[b_] + w2[..., None] * Nc[c]
                nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-12
                col = np.broadcast_to(base, (*w0.shape, 3)).copy()
                if pr['C'] is not None:
                    vc = w0[..., None] * pr['C'][a, :3] + w1[..., None] * pr['C'][b_, :3] + w2[..., None] * pr['C'][c, :3]
                    col = col * vc
                d = np.clip((nrm * Lc).sum(-1), 0, 1)
                if bands:
                    d = np.where(d > 0.62, 1.0, np.where(d > 0.28, 0.72, 0.46)) * 0.6 + d * 0.4
                hemi = (0.5 + 0.5 * nrm[..., 1:2])
                amb = np.array([0.34, 0.37, 0.46]) * hemi + np.array([0.10, 0.09, 0.08])
                rim = np.clip(1.0 - nrm[..., 2:3], 0, 1) ** 3 * 0.28
                col = col * (amb + 0.80 * d[..., None]) * exposure + rim * np.array([0.5, 0.6, 0.8])
                if emi.any():
                    col = col + emi * 1.5
            region = rgb[miny:maxy + 1, minx:maxx + 1]
            region[upd] = col[upd]
            alpha[miny:maxy + 1, minx:maxx + 1][upd] = 1.0
            sub[upd] = z[upd]
    out = np.clip(rgb, 0, 1) ** (1 / 2.2)
    if bg is not None:
        bgc = np.array(bg, float) / 255.0
        out = out * alpha[..., None] + bgc * (1 - alpha[..., None])
        img = Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8)).convert('RGB')
        return img.resize((W0, H0), Image.LANCZOS) if ssaa > 1 else img
    rgba = np.dstack([out, alpha])
    img = Image.fromarray((np.clip(rgba, 0, 1) * 255).astype(np.uint8), 'RGBA').convert('RGBa')
    img = img.resize((W0, H0), Image.LANCZOS) if ssaa > 1 else img
    return img.convert('RGBA')
