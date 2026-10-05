"""GLB reader, structural validator and a tiny software renderer used for QA previews."""
from __future__ import annotations
import io, json, struct, sys
import numpy as np
from PIL import Image

COMP = {5120: ('b', 1), 5121: ('B', 1), 5122: ('h', 2), 5123: ('H', 2), 5125: ('I', 4), 5126: ('f', 4)}
NUMC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    data = open(path, 'rb').read()
    magic, version, length = struct.unpack('<III', data[:12])
    if magic != 0x46546C67: raise ValueError('bad magic')
    if version != 2: raise ValueError('not glTF 2.0')
    if length != len(data): raise ValueError(f'length mismatch {length} vs {len(data)}')
    off, js, binchunk = 12, None, b''
    while off < length:
        clen, ctype = struct.unpack('<II', data[off:off + 8]); off += 8
        chunk = data[off:off + clen]; off += clen
        if ctype == 0x4E4F534A: js = json.loads(chunk.decode('utf-8'))
        elif ctype == 0x004E4942: binchunk = chunk
    return js, binchunk


def accessor(js, binchunk, idx):
    a = js['accessors'][idx]
    bv = js['bufferViews'][a['bufferView']]
    fmt, size = COMP[a['componentType']]
    n = NUMC[a['type']]
    off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    return np.frombuffer(binchunk, dtype=np.dtype(fmt).newbyteorder('<'), count=a['count'] * n, offset=off).reshape(a['count'], n)


def validate(path, max_tris=None, require_winding=0.995):
    """Return (errors, stats). Empty errors list == structurally valid and consistently wound."""
    errs = []
    try:
        js, b = read_glb(path)
    except Exception as e:
        return [f'unreadable: {e}'], {}
    if js.get('asset', {}).get('version') != '2.0': errs.append('asset.version != 2.0')
    nb = len(b)
    if js['buffers'][0]['byteLength'] > nb: errs.append('buffer shorter than declared')
    for i, bv in enumerate(js.get('bufferViews', [])):
        if bv.get('byteOffset', 0) % 4: errs.append(f'bufferView {i} not 4-byte aligned')
        if bv.get('byteOffset', 0) + bv['byteLength'] > nb: errs.append(f'bufferView {i} out of range')
    tris = 0; verts = 0; bad_wind = 0; tot_wind = 0
    nmat = len(js.get('materials', [])); ntex = len(js.get('textures', [])); nimg = len(js.get('images', []))
    for mi, mesh in enumerate(js.get('meshes', [])):
        for pi, p in enumerate(mesh['primitives']):
            at = p['attributes']
            pos = accessor(js, b, at['POSITION']).astype(float)
            acc = js['accessors'][at['POSITION']]
            if 'min' not in acc or 'max' not in acc: errs.append(f'mesh {mi}/{pi}: POSITION missing min/max')
            elif not (np.allclose(pos.min(0), acc['min'], atol=1e-4) and np.allclose(pos.max(0), acc['max'], atol=1e-4)):
                errs.append(f'mesh {mi}/{pi}: POSITION min/max mismatch')
            nrm = accessor(js, b, at['NORMAL']).astype(float) if 'NORMAL' in at else None
            if nrm is not None:
                ln = np.linalg.norm(nrm, axis=1)
                if ln.min() < 0.98 or ln.max() > 1.02: errs.append(f'mesh {mi}/{pi}: non-unit normals ({ln.min():.3f}..{ln.max():.3f})')
            if 'TEXCOORD_0' in at:
                uv = accessor(js, b, at['TEXCOORD_0'])
                if not np.isfinite(uv).all(): errs.append(f'mesh {mi}/{pi}: non-finite UVs')
            if not np.isfinite(pos).all(): errs.append(f'mesh {mi}/{pi}: non-finite positions')
            idx = accessor(js, b, p['indices']).reshape(-1).astype(int)
            if len(idx) % 3: errs.append(f'mesh {mi}/{pi}: index count not multiple of 3')
            if idx.max() >= len(pos): errs.append(f'mesh {mi}/{pi}: index out of range')
            if 'material' in p and not (0 <= p['material'] < nmat): errs.append(f'mesh {mi}/{pi}: bad material index')
            t = idx.reshape(-1, 3)
            tris += len(t); verts += len(pos)
            if nrm is not None and len(t):
                fn = np.cross(pos[t[:, 1]] - pos[t[:, 0]], pos[t[:, 2]] - pos[t[:, 0]])
                good = np.linalg.norm(fn, axis=1) > 1e-12
                avg = nrm[t[:, 0]] + nrm[t[:, 1]] + nrm[t[:, 2]]
                d = (fn * avg).sum(1)
                bad_wind += int(((d <= 0) & good).sum()); tot_wind += int(good.sum())
    if tot_wind and (1 - bad_wind / tot_wind) < require_winding:
        errs.append(f'winding/normal disagreement on {bad_wind}/{tot_wind} triangles')
    for i, m in enumerate(js.get('materials', [])):
        for key in ('baseColorTexture', 'metallicRoughnessTexture'):
            t = m.get('pbrMetallicRoughness', {}).get(key)
            if t and not (0 <= t['index'] < ntex): errs.append(f'material {i}: bad {key}')
        for key in ('normalTexture', 'emissiveTexture'):
            t = m.get(key)
            if t and not (0 <= t['index'] < ntex): errs.append(f'material {i}: bad {key}')
    for i, im in enumerate(js.get('images', [])):
        bv = js['bufferViews'][im['bufferView']]
        raw = b[bv.get('byteOffset', 0): bv.get('byteOffset', 0) + bv['byteLength']]
        try: Image.open(io.BytesIO(raw)).verify()
        except Exception as e: errs.append(f'image {i} unreadable: {e}')
    nn = len(js.get('nodes', []))
    for i, n in enumerate(js.get('nodes', [])):
        for c in n.get('children', []):
            if not (0 <= c < nn): errs.append(f'node {i}: bad child {c}')
    for r in js['scenes'][js.get('scene', 0)]['nodes']:
        if not (0 <= r < nn): errs.append(f'scene root {r} out of range')
    if max_tris is not None and tris > max_tris: errs.append(f'triangle budget exceeded: {tris} > {max_tris}')
    stats = dict(nodes=nn, meshes=len(js.get('meshes', [])), materials=nmat, images=nimg, verts=verts, tris=tris,
                 bytes=len(open(path, 'rb').read()))
    return errs, stats


# ---------------------------------------------------------------------------- preview renderer
def _node_matrix(node):
    if 'matrix' in node: return np.array(node['matrix'], float).reshape(4, 4).T
    t = np.array(node.get('translation', [0, 0, 0]), float)
    x, y, z, w = node.get('rotation', [0, 0, 0, 1])
    s = np.array(node.get('scale', [1, 1, 1]), float)
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * s; M[:3, 3] = t
    return M


def collect(js, b, node_xf=None, overrides=None):
    """Flatten the scene to world-space primitives. node_xf: optional {node_name: 4x4} extra transforms."""
    out, imgs = [], {}

    def img(i):
        if i in imgs: return imgs[i]
        bv = js['bufferViews'][js['images'][i]['bufferView']]
        raw = b[bv.get('byteOffset', 0): bv.get('byteOffset', 0) + bv['byteLength']]
        imgs[i] = np.asarray(Image.open(io.BytesIO(raw)).convert('RGB'))
        return imgs[i]

    def tex(m, path):
        t = m
        for k in path:
            t = t.get(k) if isinstance(t, dict) else None
            if t is None: return None
        return img(js['textures'][t['index']]['source'])

    def visit(ni, parent):
        node = js['nodes'][ni]
        M = parent @ _node_matrix(node)
        if node_xf and node.get('name') in node_xf: M = parent @ node_xf[node['name']] @ _node_matrix(node)
        if 'mesh' in node:
            for p in js['meshes'][node['mesh']]['primitives']:
                at = p['attributes']
                pos = accessor(js, b, at['POSITION']).astype(float)
                nrm = accessor(js, b, at['NORMAL']).astype(float)
                uv = accessor(js, b, at['TEXCOORD_0']).astype(float) if 'TEXCOORD_0' in at else None
                idx = accessor(js, b, p['indices']).reshape(-1, 3).astype(int)
                C = accessor(js, b, at['COLOR_0']).astype(float) if 'COLOR_0' in at else None
                P = (np.c_[pos, np.ones(len(pos))] @ M.T)[:, :3]
                N = nrm @ np.linalg.inv(M[:3, :3])
                N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
                m = js['materials'][p['material']]
                pbr = m.get('pbrMetallicRoughness', {})
                ov = (overrides or {}).get(m.get('name', ''), {})
                out.append(dict(P=P, N=N, uv=uv, idx=idx, C=C, unlit='KHR_materials_unlit' in m.get('extensions', {}), base=np.array(pbr.get('baseColorFactor', [1, 1, 1, 1])),
                                metal=pbr.get('metallicFactor', 1.0), rough=pbr.get('roughnessFactor', 1.0),
                                emi=np.array(m.get('emissiveFactor', [0, 0, 0])), alpha=m.get('alphaMode', 'OPAQUE'),
                                btex=ov.get('btex', tex(m, ['pbrMetallicRoughness', 'baseColorTexture'])), etex=ov.get('etex', tex(m, ['emissiveTexture'])),
                                name=m.get('name', '')))
        for c in node.get('children', []): visit(c, M)

    for r in js['scenes'][js.get('scene', 0)]['nodes']: visit(r, np.eye(4))
    return out


def render(prims, size=(640, 640), yaw=35, pitch=16, bg=(30, 34, 44), light=(0.4, 0.8, 0.5), fit=None, center=None, ortho=True):
    W, H = size
    allp = np.vstack([p['P'] for p in prims])
    lo, hi = allp.min(0), allp.max(0)
    center = (lo + hi) / 2 if center is None else np.array(center)
    radius = np.linalg.norm(hi - lo) / 2 if fit is None else fit
    ya, pa = np.radians(yaw), np.radians(pitch)
    Ry = np.array([[np.cos(ya), 0, np.sin(ya)], [0, 1, 0], [-np.sin(ya), 0, np.cos(ya)]])
    Rx = np.array([[1, 0, 0], [0, np.cos(pa), -np.sin(pa)], [0, np.sin(pa), np.cos(pa)]])
    R = Rx @ Ry
    img = np.zeros((H, W, 3), float)
    for y in range(H): img[y] = np.array(bg) * (0.65 + 0.55 * y / H)
    zbuf = np.full((H, W), 1e18)
    scale = 0.46 * min(W, H) / radius
    L = np.array(light, float); L /= np.linalg.norm(L); Lc = L @ R.T
    for pr in prims:
        Pc = (pr['P'] - center) @ R.T
        sx = W / 2 + Pc[:, 0] * scale; sy = H / 2 - Pc[:, 1] * scale; sz = -Pc[:, 2]
        Nc = pr['N'] @ R.T
        base = pr['base'][:3]; metal = pr['metal']; rough = pr['rough']; emi = pr['emi']
        for tri in pr['idx']:
            a, b_, c = tri
            a_ = a
            x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b_], sy[b_], sx[c], sy[c]
            minx = int(max(0, np.floor(min(x0, x1, x2)))); maxx = int(min(W - 1, np.ceil(max(x0, x1, x2))))
            miny = int(max(0, np.floor(min(y0, y1, y2)))); maxy = int(min(H - 1, np.ceil(max(y0, y1, y2))))
            if minx > maxx or miny > maxy: continue
            den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
            if abs(den) < 1e-9: continue
            xs, ys = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
            w0 = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / den
            w1 = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / den
            w2 = 1 - w0 - w1
            m = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not m.any(): continue
            z = w0 * sz[a] + w1 * sz[b_] + w2 * sz[c]
            sub = zbuf[miny:maxy + 1, minx:maxx + 1]
            upd = m & (z < sub)
            if not upd.any(): continue
            nrm = w0[..., None] * Nc[a] + w1[..., None] * Nc[b_] + w2[..., None] * Nc[c]
            nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True) + 1e-12
            col = np.broadcast_to(base, (*w0.shape, 3)).copy()
            e = np.broadcast_to(emi, (*w0.shape, 3)).copy()
            if pr['C'] is not None:
                vc = w0[..., None] * pr['C'][a_, :3] + w1[..., None] * pr['C'][b_, :3] + w2[..., None] * pr['C'][c, :3]
                if pr['unlit']: e = e + vc; col = col * 0.0
                else: col = col * vc
            if pr['uv'] is not None and (pr['btex'] is not None or pr['etex'] is not None):
                u = w0 * pr['uv'][a, 0] + w1 * pr['uv'][b_, 0] + w2 * pr['uv'][c, 0]
                v = w0 * pr['uv'][a, 1] + w1 * pr['uv'][b_, 1] + w2 * pr['uv'][c, 1]
                if pr['btex'] is not None:
                    th, tw = pr['btex'].shape[:2]
                    col = col * (pr['btex'][(np.mod(v, 1.0) * (th - 1)).astype(int), (np.mod(u, 1.0) * (tw - 1)).astype(int)] / 255.0) ** 2.2
                if pr['etex'] is not None:
                    th, tw = pr['etex'].shape[:2]
                    e = e * (pr['etex'][(np.mod(v, 1.0) * (th - 1)).astype(int), (np.mod(u, 1.0) * (tw - 1)).astype(int)] / 255.0) ** 2.2
            diff = np.clip((nrm * Lc).sum(-1), 0, 1)[..., None]
            hemi = 0.5 + 0.5 * nrm[..., 1:2]
            amb = np.array([0.20, 0.24, 0.32]) * hemi
            hv = Lc + np.array([0, 0, 1.0]); hv /= np.linalg.norm(hv)
            spec = np.clip((nrm * hv).sum(-1), 0, 1)[..., None] ** (6 + 90 * (1 - rough) ** 2)
            colr = col * (amb + 0.95 * diff) * (1 - 0.7 * metal) + spec * (0.10 + 0.9 * metal * (1 - 0.5 * rough)) + e * 1.6
            colr = np.clip(colr, 0, 1) ** (1 / 2.2)
            region = img[miny:maxy + 1, minx:maxx + 1]
            region[upd] = colr[upd] * 255
            sub[upd] = z[upd]
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))


if __name__ == '__main__':
    bad = 0
    for p in sys.argv[1:]:
        errs, st = validate(p)
        print(('OK   ' if not errs else 'FAIL ') + p, st)
        for e in errs: print('   -', e)
        bad += bool(errs)
    sys.exit(1 if bad else 0)
