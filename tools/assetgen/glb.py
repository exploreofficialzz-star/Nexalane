"""Minimal glTF 2.0 binary (.glb) writer with embedded PNG textures."""
from __future__ import annotations
import io, json, struct
import numpy as np
from PIL import Image
from .geo import Mesh


class Mat:
    def __init__(self, name, base=(0.8, 0.8, 0.8, 1.0), metal=0.0, rough=0.8, emissive=(0.0, 0.0, 0.0),
                 alpha='OPAQUE', double=False, base_tex=None, emissive_tex=None, normal_tex=None, mr_tex=None,
                 unlit=False):
        self.name = name
        self.base = tuple(base) if len(base) == 4 else tuple(base) + (1.0,)
        self.metal, self.rough = float(metal), float(rough)
        self.emissive = tuple(emissive)
        self.alpha, self.double, self.unlit = alpha, double, unlit
        self.base_tex, self.emissive_tex, self.normal_tex, self.mr_tex = base_tex, emissive_tex, normal_tex, mr_tex


class Node:
    def __init__(self, name, mesh=None, t=(0, 0, 0), r=None, s=None, children=None, extras=None):
        self.name, self.mesh, self.t, self.r, self.s = name, mesh, t, r, s
        self.children = children or []
        self.extras = extras

    def add(self, child):
        self.children.append(child); return child


KEEP_SEPARATE_PREFIXES = ('RunnerAccent', 'RunnerGlow', 'facade_', 'coin_', 'nova_')
CLASS_MATS = {
    'matte': Mat('matte', (1, 1, 1, 1), 0.05, 0.62),
    'metal': Mat('metal', (1, 1, 1, 1), 0.90, 0.40),
    'glow': Mat('glow', (1, 1, 1, 1), 0.0, 0.5, unlit=True),
}


def classify(name, m: 'Mat'):
    """-> (class name, vertex colour RGBA or None when the material must stay a standalone material)."""
    if name.startswith(KEEP_SEPARATE_PREFIXES) or m.base_tex is not None or m.emissive_tex is not None or m.alpha != 'OPAQUE':
        return name, None
    if any(m.emissive): return 'glow', (*m.emissive, 1.0)
    return ('metal' if m.metal >= 0.5 else 'matte'), tuple(m.base)


class GLBWriter:
    def __init__(self, generator="NEXALANE procedural assets 0.4.5"):
        self.generator = generator
        self.bin = bytearray()
        self.buffer_views, self.accessors = [], []
        self.materials, self.mat_cache = [], {}
        self.images, self.textures, self.tex_cache = [], [], {}
        self.meshes, self.nodes = [], []
        self.samplers = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
        self.uses_unlit = False

    # ---- buffers ---------------------------------------------------------
    def _align(self):
        while len(self.bin) % 4:
            self.bin.append(0)

    def _view(self, data: bytes, target=None) -> int:
        self._align()
        bv = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target: bv["target"] = target
        self.bin += data
        self.buffer_views.append(bv)
        return len(self.buffer_views) - 1

    def _accessor(self, arr, comp, typ, target, minmax=False) -> int:
        arr = np.ascontiguousarray(arr)
        bv = self._view(arr.tobytes(), target)
        acc = {"bufferView": bv, "componentType": comp, "count": int(arr.shape[0]), "type": typ}
        if minmax:
            acc["min"] = [float(x) for x in arr.min(axis=0)]
            acc["max"] = [float(x) for x in arr.max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # ---- textures / materials -------------------------------------------
    def texture(self, img: Image.Image) -> int:
        key = id(img)
        if key in self.tex_cache: return self.tex_cache[key]
        buf = io.BytesIO(); img.save(buf, format="PNG", optimize=True)
        bv = self._view(buf.getvalue())
        self.images.append({"bufferView": bv, "mimeType": "image/png"})
        self.textures.append({"sampler": 0, "source": len(self.images) - 1})
        self.tex_cache[key] = len(self.textures) - 1
        return self.tex_cache[key]

    def material(self, m: Mat) -> int:
        if m.name in self.mat_cache: return self.mat_cache[m.name]
        pbr = {"baseColorFactor": [float(x) for x in m.base], "metallicFactor": m.metal, "roughnessFactor": m.rough}
        out = {"name": m.name, "pbrMetallicRoughness": pbr}
        if m.base_tex is not None: pbr["baseColorTexture"] = {"index": self.texture(m.base_tex)}
        if m.mr_tex is not None: pbr["metallicRoughnessTexture"] = {"index": self.texture(m.mr_tex)}
        if m.normal_tex is not None: out["normalTexture"] = {"index": self.texture(m.normal_tex)}
        if m.emissive_tex is not None:
            out["emissiveTexture"] = {"index": self.texture(m.emissive_tex)}
            out["emissiveFactor"] = [1.0, 1.0, 1.0]
        elif any(m.emissive):
            out["emissiveFactor"] = [float(x) for x in m.emissive]
        if m.alpha != 'OPAQUE': out["alphaMode"] = m.alpha
        if m.double: out["doubleSided"] = True
        if m.unlit:
            out["extensions"] = {"KHR_materials_unlit": {}}; self.uses_unlit = True
        self.materials.append(out)
        self.mat_cache[m.name] = len(self.materials) - 1
        return self.mat_cache[m.name]

    # ---- meshes / nodes ----------------------------------------------------
    def add_mesh(self, mesh: Mesh, mats: dict, name="mesh") -> int:
        """Writes one glTF mesh. Plain (untextured, opaque) materials are merged into a few classes
        (matte / metal / glow) with the albedo carried in COLOR_0, so a model costs 2-4 draw calls
        instead of one per material."""
        merged: dict = {}
        order = []
        for mat_name in mesh.materials():
            pos, nrm, uv, idx = mesh.arrays(mat_name)
            if len(pos) == 0: continue
            cls, color = classify(mat_name, mats[mat_name])
            g = merged.get(cls)
            if g is None:
                g = merged[cls] = dict(pos=[], nrm=[], uv=[], idx=[], col=[], n=0, color=color is not None, mat=mats[mat_name] if color is None else CLASS_MATS[cls])
                order.append(cls)
            g['pos'].append(pos); g['nrm'].append(nrm); g['uv'].append(uv); g['idx'].append(idx + g['n']); g['n'] += len(pos)
            if color is not None: g['col'].append(np.tile(np.array(color, float), (len(pos), 1)))
        prims = []
        for cls in order:
            g = merged[cls]
            pos = np.vstack(g['pos']).astype('<f4'); nrm = np.vstack(g['nrm']).astype('<f4'); uv = np.vstack(g['uv']).astype('<f4')
            idx = np.vstack(g['idx'])
            attrs = {"POSITION": self._accessor(pos, 5126, "VEC3", 34962, minmax=True),
                     "NORMAL": self._accessor(nrm, 5126, "VEC3", 34962),
                     "TEXCOORD_0": self._accessor(uv, 5126, "VEC2", 34962)}
            if g['color']: attrs["COLOR_0"] = self._accessor(np.vstack(g['col']).astype('<f4'), 5126, "VEC4", 34962)
            flat = idx.reshape(-1)
            if flat.max() < 65535: a_idx = self._accessor(flat.astype('<u2'), 5123, "SCALAR", 34963)
            else: a_idx = self._accessor(flat.astype('<u4'), 5125, "SCALAR", 34963)
            prims.append({"attributes": attrs, "indices": a_idx, "material": self.material(g['mat']), "mode": 4})
        self.meshes.append({"name": name, "primitives": prims})
        return len(self.meshes) - 1

    def add_node(self, node: Node, mats: dict) -> int:
        d = {"name": node.name}
        if node.mesh is not None and node.mesh.materials():
            d["mesh"] = self.add_mesh(node.mesh, mats, node.name)
        if node.t and any(abs(v) > 1e-9 for v in node.t): d["translation"] = [float(v) for v in node.t]
        if node.r is not None: d["rotation"] = [float(v) for v in node.r]
        if node.s is not None: d["scale"] = [float(v) for v in node.s]
        if node.extras: d["extras"] = node.extras
        kids = [self.add_node(c, mats) for c in node.children]
        if kids: d["children"] = kids
        self.nodes.append(d)
        return len(self.nodes) - 1

    def write(self, path, roots, mats: dict):
        root_ids = [self.add_node(r, mats) for r in roots]
        js = {"asset": {"version": "2.0", "generator": self.generator},
              "scene": 0, "scenes": [{"nodes": root_ids}], "nodes": self.nodes,
              "meshes": self.meshes, "materials": self.materials, "accessors": self.accessors,
              "bufferViews": self.buffer_views, "buffers": [{"byteLength": len(self.bin)}]}
        if self.images:
            js["images"], js["textures"], js["samplers"] = self.images, self.textures, self.samplers
        if self.uses_unlit: js["extensionsUsed"] = ["KHR_materials_unlit"]
        jb = json.dumps(js, separators=(",", ":")).encode("utf-8")
        while len(jb) % 4: jb += b" "
        self._align()
        total = 12 + 8 + len(jb) + 8 + len(self.bin)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, total))
            f.write(struct.pack("<II", len(jb), 0x4E4F534A)); f.write(jb)
            f.write(struct.pack("<II", len(self.bin), 0x004E4942)); f.write(bytes(self.bin))
        return total


def write_model(path, roots, mats: dict):
    """roots: list[Node]; mats: {material_name: Mat}. Returns file size in bytes."""
    return GLBWriter().write(path, roots, mats)
