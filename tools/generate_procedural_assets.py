#!/usr/bin/env python3
"""NEXALANE asset pipeline (v0.4.5): regenerates every texture, UI/VFX sprite, GLB model and audio file.

    python tools/generate_procedural_assets.py            # everything
    python tools/generate_procedural_assets.py --skip-audio
    python tools/generate_procedural_assets.py --only models

Needs Python 3.10+, numpy, Pillow, scipy. FFmpeg (libvorbis) is only needed for the music loops.
All output is deterministic: running it twice yields identical files. Nothing is downloaded or copied
from third-party packs; the Poppins fonts under assets/fonts are the only bundled third-party files (OFL).
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from PIL import Image  # noqa: E402
from assetgen import tex_env as E, tex_ui as U, kit, models_play as MP, models_world as MW, validate as V  # noqa: E402
from assetgen.glb import write_model  # noqa: E402

VERSION = '0.4.5'
AS, AUD, DOC = ROOT / 'assets', ROOT / 'audio', ROOT / 'docs'


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save_png(img: Image.Image, path: Path, **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True, **kw)


def build_textures(log):
    T = AS / 'textures'
    for wet, name in ((False, 'env_asphalt_dry'), (True, 'env_asphalt_wet')):
        r = E.road_set(wet)
        save_png(r['albedo'], T / f'{name}.png'); save_png(r['normal'], T / f'{name}_n.png'); save_png(r['rough'], T / f'{name}_r.png')
        if 'emission' in r: save_png(r['emission'], T / f'{name}_e.png')
    save_png(E.concrete_tile(), T / 'env_concrete_city.png'); save_png(E.brushed_metal(), T / 'env_metal_brushed.png'); save_png(E.holo_grid(), T / 'env_neon_grid.png')
    for i, k in enumerate('abcd'):
        a, e, mr = E.facade(k, 51 + i)
        save_png(a, T / f'env_facade_{k}.png'); save_png(e, T / f'env_facade_{k}_e.png'); save_png(mr, T / f'env_facade_{k}_mr.png')
    save_png(E.skyline(2048, 512, 2, 61, 0.0), T / 'env_skyline_near.png'); save_png(E.skyline(2048, 512, 3, 62, 0.55), T / 'env_skyline_far.png')
    log('textures done')


def build_ui(log):
    for n, fn in (('icon_credit', U.icon_credit), ('icon_nova', U.icon_nova), ('icon_flow', U.icon_flow), ('icon_shield', U.icon_shield)):
        save_png(fn(256), AS / 'ui' / f'{n}.png')
    for n, fn in U.GLYPHS.items(): save_png(U._glyph(fn, 128), AS / 'ui' / f'{n}.png')
    save_png(U.logo(), AS / 'ui' / 'ui_logo.png')
    for k in U.ROUTE_STYLE: save_png(U.decal(k), AS / 'decals' / f'route_{k}.png')
    save_png(U.decal_spire(), AS / 'decals' / 'district_spire.png')
    for n, im in (('vfx_glow', U.vfx_glow()), ('vfx_spark', U.vfx_spark()), ('vfx_ring', U.vfx_ring()), ('vfx_streak', U.vfx_streak()), ('vfx_smoke', U.vfx_smoke()), ('vfx_light_pool', U.vfx_light_pool())):
        save_png(im, AS / 'vfx' / f'{n}.png')
    U.launcher_icons(str(AS / 'icon' / 'nexalane_icon_master.png'), str(AS / 'icon'))
    log('ui/vfx/decals/icons done')


def build_models(log):
    coin = U.icon_credit(256); bg = Image.new('RGBA', coin.size, (214, 140, 20, 255)); bg.alpha_composite(coin)
    mats = kit.make_mats(dict(hazard=kit.hazard_texture(), coin=bg.convert('RGB').resize((128, 128))))
    out = AS / 'models'; out.mkdir(parents=True, exist_ok=True)
    for old in out.glob('*.glb'): old.unlink()
    stats = {}
    for name, fn in {**MP.PLAY_BUILDERS, **MW.WORLD_BUILDERS}.items():
        p = out / f'{name}.glb'; write_model(str(p), fn(), mats)
        errs, st = V.validate(str(p))
        if errs: raise SystemExit(f'{name}.glb failed validation: {errs}')
        stats[name] = st
    log(f'{len(stats)} models validated ({sum(s["tris"] for s in stats.values())} tris total)')
    return stats


def build_audio(log):
    from assetgen import audiogen
    for old in list((AUD / 'sfx').glob('*.wav')) + list((AUD / 'generated').glob('*.wav')) + list((AUD / 'music_ogg').glob('*.ogg')): old.unlink()
    res = audiogen.generate_all(str(AUD), log=lambda *a: None)
    log(f'{len(res)} audio files written')


def write_registries(log):
    assets = []
    for p in sorted(AS.rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.png', '.glb', '.ttf'):
            assets.append(dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p), source='procedural (tools/assetgen)' if p.suffix != '.ttf' else 'Poppins, SIL OFL 1.1'))
    (DOC / 'ASSET_REGISTRY.json').write_text(json.dumps(dict(version=VERSION, asset_count=len(assets), assets=assets), indent=2))
    audio = []
    for p in sorted(AUD.rglob('*')):
        if p.is_file() and p.suffix.lower() in ('.wav', '.ogg'): audio.append(dict(path=p.relative_to(ROOT).as_posix(), bytes=p.stat().st_size, sha256=sha(p)))
    (DOC / 'AUDIO_REGISTRY.json').write_text(json.dumps(dict(version=VERSION, audio_count=len(audio), audio=audio), indent=2))
    log(f'registries: {len(assets)} assets, {len(audio)} audio')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--skip-audio', action='store_true'); ap.add_argument('--only', choices=['textures', 'ui', 'models', 'audio'])
    a = ap.parse_args(); t0 = time.time(); log = lambda m: print(f'[{time.time() - t0:5.1f}s] {m}')
    todo = [a.only] if a.only else ['textures', 'ui', 'models'] + ([] if a.skip_audio else ['audio'])
    if 'textures' in todo: build_textures(log)
    if 'ui' in todo: build_ui(log)
    if 'models' in todo: build_models(log)
    if 'audio' in todo: build_audio(log)
    write_registries(log)


if __name__ == '__main__':
    main()
