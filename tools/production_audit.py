#!/usr/bin/env python3
"""NEXALANE static production audit (v0.4.5).

Replaces the 0.4.4 audit, which reported PASS while the project could not even compile. It now runs the
GDScript static checker, validates every GLB structurally, decodes every audio file, verifies project / export
settings that break mobile builds, and cross-checks the registries and version numbers.
Run:  python tools/production_audit.py        (needs numpy, Pillow; ffmpeg for audio)
"""
from __future__ import annotations
import hashlib, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
failures: list[str] = []
notes: list[str] = []


def need(cond: bool, msg: str):
    if not cond: failures.append(msg)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ---------------------------------------------------------------- GDScript static analysis
import gd_static_check
errors, warnings = gd_static_check.check()
failures += [f'gdscript: {e}' for e in errors]
failures += [f'gdscript (review): {w}' for w in warnings]
notes.append(f'GDScript static check: {len(errors)} errors, {len(warnings)} warnings')

# ---------------------------------------------------------------- versions
project = (ROOT / 'project.godot').read_text()
app = (ROOT / 'autoload/app_state.gd').read_text()
version = (re.search(r'product_version="([^"]+)"', project) or [None, None])[1]
need(version is not None, 'project.godot: product_version missing')
for key, const in (('product_version', 'PRODUCT_VERSION'), ('content_version', 'CONTENT_VERSION')):
    pv = re.search(rf'{key}="([^"]+)"', project); av = re.search(rf'{const} := "([^"]+)"', app)
    need(bool(pv and av and pv.group(1) == av.group(1)), f'{key} differs between project.godot and autoload/app_state.gd')
tv = re.search(r'tuning_version="(\d+)"', project); at = re.search(r'TUNING_VERSION := (\d+)', app)
need(bool(tv and at and tv.group(1) == at.group(1)), 'tuning_version differs between project.godot and app_state.gd')
notes.append(f'version {version}')

# ---------------------------------------------------------------- project + export settings that break mobile builds
need('window/handheld/orientation=1' in project, 'project.godot: portrait orientation missing (Android would start in landscape)')
need('config/quit_on_go_back=false' in project, 'project.godot: quit_on_go_back must be false (Back button would kill the run)')
need('import_etc2_astc=true' in project, 'project.godot: textures/vram_compression/import_etc2_astc must be true for Android export')
need('window/stretch/aspect="expand"' in project, 'project.godot: stretch aspect should be "expand" for tall phones')
presets = ROOT / 'export_presets.cfg'
need(presets.exists(), 'export_presets.cfg must be in the project root (Godot ignores build/export_presets.cfg)')
if presets.exists():
    txt = presets.read_text()
    need('platform="Android"' in txt and 'platform="iOS"' in txt, 'export presets: Android and iOS expected')
    need('exclude_filter="docs/*' in txt, 'export presets: exclude docs/tools/tests from the shipped pack')
    need('permissions/vibrate=true' in txt, 'export presets: VIBRATE permission missing (haptics would fail)')
    need(re.search(r'keystore/release_password="[^"]+"', txt) is None, 'export presets: a keystore password is committed')
    need(f'version/name="{version}"' in txt, 'export presets: version/name differs from product_version')
need(not (ROOT / 'build/export_presets.cfg').exists(), 'stale build/export_presets.cfg (Godot never reads it)')

# ---------------------------------------------------------------- images
try:
    from PIL import Image
    pngs = sorted((ROOT / 'assets').rglob('*.png'))
    for p in pngs:
        try:
            with Image.open(p) as im: im.verify()
        except Exception as exc:
            failures.append(f'bad PNG {p.relative_to(ROOT)}: {exc}')
    notes.append(f'{len(pngs)} PNG files verified')
except ImportError:
    notes.append('Pillow missing: PNG verification skipped')

# ---------------------------------------------------------------- 3D models
from assetgen import validate as V
glbs = sorted((ROOT / 'assets/models').glob('*.glb'))
total_tris = 0
for p in glbs:
    errs, st = V.validate(str(p), max_tris=9000)
    failures += [f'GLB {p.name}: {e}' for e in errs]
    total_tris += st.get('tris', 0)
notes.append(f'{len(glbs)} GLB models valid, {total_tris} triangles total')
used = set()
for p in ROOT.rglob('*.gd'):
    used.update(re.findall(r'ModelLibrary\.instantiate\("([A-Za-z0-9_]+)"', p.read_text(errors='ignore')))
    used.update(re.findall(r'"model":\s*"([A-Za-z0-9_]+)"', p.read_text(errors='ignore')))
    used.update(re.findall(r'_place\([^,]+,\s*"([A-Za-z0-9_]+)"', p.read_text(errors='ignore')))
for model_id in sorted(used):
    need((ROOT / f'assets/models/{model_id}.glb').exists(), f'code references missing model: {model_id}')

# ---------------------------------------------------------------- audio
try:
    import numpy as np
    audio_files = sorted(list((ROOT / 'audio').rglob('*.wav')) + list((ROOT / 'audio').rglob('*.ogg')))
    for p in audio_files:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(p), '-f', 'f32le', '-ac', '1', '-ar', '22050', '-'], capture_output=True)
        if r.returncode != 0 or not r.stdout:
            failures.append(f'bad audio {p.relative_to(ROOT)}'); continue
        x = np.frombuffer(r.stdout, '<f4')
        if not np.isfinite(x).all(): failures.append(f'audio contains NaN/inf: {p.name}')
        if np.abs(x).max() > 1.0: failures.append(f'audio clips (>0 dBFS): {p.name}')
        if np.sqrt((x ** 2).mean()) < 0.005: failures.append(f'audio is (nearly) silent: {p.name}')
    notes.append(f'{len(audio_files)} audio files decoded')
except FileNotFoundError:
    notes.append('ffmpeg missing: audio decode skipped')

# ---------------------------------------------------------------- registries
asset_registry = json.loads((ROOT / 'docs/ASSET_REGISTRY.json').read_text())
audio_registry = json.loads((ROOT / 'docs/AUDIO_REGISTRY.json').read_text())
real_assets = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'assets').rglob('*') if p.is_file() and p.suffix.lower() in ('.png', '.glb', '.ttf')}
listed = {a['path']: a for a in asset_registry['assets']}
need(set(listed) == real_assets, f'asset registry out of date (run tools/generate_procedural_assets.py): {len(real_assets ^ set(listed))} differences')
for path, entry in listed.items():
    if (ROOT / path).exists() and sha(ROOT / path) != entry['sha256']: failures.append(f'asset registry hash mismatch: {path}'); break
real_audio = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'audio').rglob('*') if p.is_file() and p.suffix in ('.wav', '.ogg')}
need({a['path'] for a in audio_registry['audio']} == real_audio, 'audio registry out of date')

# ---------------------------------------------------------------- hygiene
for p in ROOT.rglob('*.gd'):
    for i, line in enumerate(p.read_text(errors='ignore').splitlines(), 1):
        if re.search(r'\bTODO\b|\bFIXME\b|\bTBD\b', line): failures.append(f'placeholder marker in {p.relative_to(ROOT)}:{i}')

print('NEXALANE production audit')
for n in notes: print('  ' + n)
if failures:
    print(f'FAIL: {len(failures)}')
    for f in failures: print(' -', f)
    sys.exit(1)
print('PASS: static production audit')
