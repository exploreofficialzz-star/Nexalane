"""Reads the skinned runner GLB back, validates the rig data and renders posed previews with the tiny software renderer.

Used by tools/generate_procedural_assets.py (validation), tools/render_runner_poses.py (docs/previews/runner_pose_sheet.png) and the
release gate.  Nothing here is needed at game run time.
"""
from __future__ import annotations
import numpy as np
from .validate import read_glb, accessor, render
from . import human_rig as rig
_default_rig = rig


def load_skinned(path):
    js, b = read_glb(path)
    if not js.get('skins'):
        raise ValueError('no skin in ' + path)
    skin = js['skins'][0]
    ibm = accessor(js, b, skin['inverseBindMatrices']).astype(float).reshape(-1, 4, 4).transpose(0, 2, 1)   # column-major -> row-major
    joints = [j for j in skin['joints']]
    names = [js['nodes'][j]['name'] for j in joints]
    prims = []
    mesh_node = next(n for n in js['nodes'] if 'skin' in n)
    for p in js['meshes'][mesh_node['mesh']]['primitives']:
        at = p['attributes']
        m = js['materials'][p['material']]
        pbr = m.get('pbrMetallicRoughness', {})
        prims.append(dict(
            P=accessor(js, b, at['POSITION']).astype(float), N=accessor(js, b, at['NORMAL']).astype(float),
            uv=None, idx=accessor(js, b, p['indices']).reshape(-1, 3).astype(int),
            C=accessor(js, b, at['COLOR_0']).astype(float) if 'COLOR_0' in at else None,
            J=accessor(js, b, at['JOINTS_0']).astype(int), W=accessor(js, b, at['WEIGHTS_0']).astype(float),
            unlit=False, base=np.array(pbr.get('baseColorFactor', [1, 1, 1, 1])), metal=pbr.get('metallicFactor', 1.0),
            rough=pbr.get('roughnessFactor', 1.0), emi=np.array(m.get('emissiveFactor', [0, 0, 0])), alpha='OPAQUE',
            btex=None, etex=None, name=m.get('name', '')))
    return dict(js=js, prims=prims, ibm=ibm, names=names, joints=joints)


def validate_skin(path, max_tris=9000, rig_mod=None, height_range=(1.78, 1.86)):
    """Structural checks for the skinned runner.  Returns (errors, stats).
    rig_mod: the skeleton module the model was built on (default human_rig; the cartoon runner uses toon_rig).
    The unlit RunnerOutline shell (cartoon runner) counts for triangles and weights but not for height / feet."""
    rig = rig_mod or _default_rig
    errs = []
    try:
        sk = load_skinned(path)
    except Exception as e:
        return [f'unreadable skin: {e}'], {}
    js = sk['js']
    if sk['names'] != rig.NAMES:
        errs.append(f'joint names / order differ from tools/assetgen/{rig.__name__.split(".")[-1]}.py')
    # node hierarchy must reproduce the rest positions
    nodes = js['nodes']
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get('children', []): parent[c] = i
    for bi, j in enumerate(sk['joints']):
        pos = np.array(nodes[j].get('translation', [0, 0, 0]), float)
        k = j
        while k in parent and parent[k] in sk['joints']:
            k = parent[k]; pos = pos + np.array(nodes[k].get('translation', [0, 0, 0]), float)
        if not np.allclose(pos, rig.BONES[bi][2], atol=1e-5): errs.append(f'bone {sk["names"][bi]}: node chain {pos} != rest {rig.BONES[bi][2]}')
        if 'rotation' in nodes[j] or 'scale' in nodes[j]: errs.append(f'bone {sk["names"][bi]} has a rotation/scale (rest rotations must be identity)')
        if not np.allclose(sk['ibm'][bi][:3, 3], -np.array(rig.BONES[bi][2]), atol=1e-5): errs.append(f'bone {sk["names"][bi]}: inverse bind translation mismatch')
    tris = 0
    lo = np.full(3, 1e9); hi = np.full(3, -1e9)
    for p in sk['prims']:
        s = p['W'].sum(1)
        if not np.allclose(s, 1.0, atol=1e-3): errs.append(f'{p["name"]}: weights do not sum to 1 (min {s.min():.4f} max {s.max():.4f})')
        if p['J'].max() >= len(sk['joints']): errs.append(f'{p["name"]}: joint index out of range')
        tris += len(p['idx'])
        if p['name'] != 'RunnerOutline':
            lo = np.minimum(lo, p['P'].min(0)); hi = np.maximum(hi, p['P'].max(0))
    if tris > max_tris: errs.append(f'triangle budget exceeded: {tris} > {max_tris}')
    if abs(lo[1]) > 0.003: errs.append(f'feet are not on y=0 (min y {lo[1]:.4f})')
    if not (height_range[0] <= hi[1] <= height_range[1]): errs.append(f'standing height {hi[1]:.3f} outside {height_range[0]}..{height_range[1]} m')
    return errs, dict(tris=tris, prims=len(sk['prims']), bones=len(sk['joints']), min=lo.round(3).tolist(), max=hi.round(3).tolist())


def posed_prims(sk, wr, wp):
    """Linear-blend skinning with bone world rotations wr[i] (3x3) / positions wp[i] (3,) -> prims for validate.render."""
    M = np.zeros((len(wr), 4, 4))
    for i in range(len(wr)):
        M[i][:3, :3] = wr[i]; M[i][:3, 3] = wp[i]; M[i][3, 3] = 1.0
    skin_m = np.einsum('bij,bjk->bik', M, sk['ibm'])                     # world * inverse-bind
    out = []
    for p in sk['prims']:
        Ph = np.c_[p['P'], np.ones(len(p['P']))]
        P = np.zeros((len(Ph), 3)); N = np.zeros((len(Ph), 3))
        for k in range(4):
            w = p['W'][:, k]
            if not w.any(): continue
            m = skin_m[p['J'][:, k]]                                         # (n,4,4)
            P += w[:, None] * np.einsum('nij,nj->ni', m[:, :3, :], Ph)
            N += w[:, None] * np.einsum('nij,nj->ni', m[:, :3, :3], p['N'])
        N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
        q = dict(p); q['P'] = P; q['N'] = N
        out.append(q)
    return out


def render_posed(sk, wr, wp, size=(360, 560), yaw=30, pitch=8, center=(0.0, 0.92, 0.0), fit=1.18, **kw):
    return render(posed_prims(sk, wr, wp), size=size, yaw=yaw, pitch=pitch, center=center, fit=fit, **kw)
