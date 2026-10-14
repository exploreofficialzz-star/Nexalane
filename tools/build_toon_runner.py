#!/usr/bin/env python3
"""Builds assets/models/runner_base.glb - the cartoon runner (tools/assetgen/toon.py) - and validates it.

    python tools/build_toon_runner.py

The old realistic runner generator (assetgen/human.py + human_rig.py) is kept for reference; generate_procedural_assets.py
calls this builder instead.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from assetgen import toon, validate as V  # noqa: E402


def build(path=None):
    path = Path(path or ROOT / 'assets' / 'models' / 'runner_base.glb')
    model = toon.build_runner()
    size = model.write(str(path))
    errs, stats = V.validate(str(path))
    return path, size, errs, stats


if __name__ == '__main__':
    p, size, errs, stats = build()
    print(f'{p.relative_to(ROOT)}  {size / 1024:.0f} KB  {stats}')
    for e in errs:
        print('  -', e)
    sys.exit(1 if errs else 0)
