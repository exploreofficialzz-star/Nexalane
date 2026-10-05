#!/usr/bin/env python3
"""Runs every static gate and writes docs/RELEASE_GATE_<version>.json. Engine/device checks stay explicitly NOT_RUN."""
from pathlib import Path
import json, re, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
version = re.search(r'product_version="([^"]+)"', (ROOT / 'project.godot').read_text()).group(1)
gates = {'gdscript_static_check': 'tools/gd_static_check.py', 'production_audit': 'tools/production_audit.py',
         'performance_budget': 'tools/performance_budget.py', 'release_smoke_test': 'tools/release_smoke_test.py'}
results = {}
for name, script in gates.items():
    r = subprocess.run([sys.executable, str(ROOT / script)], capture_output=True, text=True, cwd=ROOT)
    results[name] = 'PASS' if r.returncode == 0 else 'FAIL'
    if r.returncode != 0: print(r.stdout[-2500:], r.stderr[-1500:])
report = {'version': version, 'gates': results,
          'engine_compile': 'NOT_RUN_GODOT_BINARY_UNAVAILABLE (run: godot --headless --path . --import, then godot --headless --path . -s tests/qa_harness.gd)',
          'device_export': 'NOT_RUN_NO_ANDROID_IOS_SDK_OR_SIGNING_ENVIRONMENT'}
(ROOT / f'docs/RELEASE_GATE_{version}.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
sys.exit(0 if all(v == 'PASS' for v in results.values()) else 1)
