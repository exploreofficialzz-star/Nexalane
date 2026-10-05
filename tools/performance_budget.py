#!/usr/bin/env python3
"""Static asset budgets for a mid-range phone target. Source PNG size is not VRAM size: Godot recompresses
textures to ETC2/ASTC at import, so the texture budget is about repository / download size."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from assetgen import validate as V

BUDGETS = {"workspace_mb": 90.0, "models_mb": 6.0, "textures_mb": 24.0, "music_mb": 12.0, "sfx_mb": 3.0, "png_count": 120, "glb_count": 64,
           "max_tris_per_model": 9000, "max_surfaces_per_model": 24}

def mb(paths): return sum(p.stat().st_size for p in paths if p.is_file()) / 1024 / 1024

glbs = sorted((ROOT / 'assets/models').glob('*.glb'))
stats = {p.name: V.validate(str(p))[1] for p in glbs}
surfaces = {p.name: sum(len(m['primitives']) for m in V.read_glb(str(p))[0]['meshes']) for p in glbs}
checks = [
    ("workspace_mb", mb([p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts and '__pycache__' not in p.parts])),
    ("models_mb", mb(glbs)),
    ("textures_mb", mb(list((ROOT/'assets'/'textures').glob('*')) + list((ROOT/'assets'/'ui').glob('*')) + list((ROOT/'assets'/'vfx').glob('*')) + list((ROOT/'assets'/'decals').glob('*')))),
    ("music_mb", mb(list((ROOT/'audio'/'music_ogg').glob('*.ogg')))),
    ("sfx_mb", mb(list((ROOT/'audio'/'sfx').glob('*.wav')) + list((ROOT/'audio'/'generated').glob('*.wav')))),
    ("png_count", len(list((ROOT/'assets').rglob('*.png')))),
    ("glb_count", len(glbs)),
    ("max_tris_per_model", max(s['tris'] for s in stats.values())),
    ("max_surfaces_per_model", max(surfaces.values())),
]
print("NEXALANE PERFORMANCE BUDGET")
failed = False
for name, value in checks:
    ok = value <= BUDGETS[name]
    print(f"{name}: {value:.2f} / {BUDGETS[name]:.0f} {'PASS' if ok else 'FAIL'}")
    failed |= not ok
worst = max(surfaces, key=surfaces.get)
print(f"heaviest model by draw calls: {worst} ({surfaces[worst]} surfaces)")
if failed: sys.exit(1)
print("PASS: static asset/performance budget")
