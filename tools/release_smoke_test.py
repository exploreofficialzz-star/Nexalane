#!/usr/bin/env python3
"""Fast source-level smoke checks (no engine). Complements tools/production_audit.py."""
from pathlib import Path
import json, re, sys
ROOT = Path(__file__).resolve().parents[1]
failures = []
def need(cond, msg):
    if not cond: failures.append(msg)

project = (ROOT / 'project.godot').read_text()
for m in re.finditer(r'=\"\*res://([^\"]+)\"', project):
    need((ROOT / m.group(1)).exists(), f'missing autoload: {m.group(1)}')
main_scene = re.search(r'run/main_scene="res://([^"]+)"', project)
need(bool(main_scene) and (ROOT / main_scene.group(1)).exists(), 'main scene missing')
for needle, label in (
    ('func request_jump', 'runner jump request API'), ('_execute_jump', 'jump executed after the floor-stick velocity'),
    ('grant_invulnerability', 'invulnerability frames'), ('func _shatter', 'shield removes the obstacle it absorbed')):
    need(needle in (ROOT / 'gameplay/runner/runner_controller.gd').read_text(), f'runner: {label} missing')
sess = (ROOT / 'core/player_session.gd').read_text()
need('if finished:' in sess and 'finished = true' in sess, 'player_session: finish guard missing (decline-revive softlock)')
need('revive_countdown' in sess and 'REVIVE_WINDOW' in sess, 'player_session: revive timeout missing')
save = (ROOT / 'save/save_service.gd').read_text()
need('_coerce' in save and 'TYPE_FLOAT' in save, 'save_service: JSON float->int coercion missing')
need('TMP_PATH' in save and 'BACKUP_PATH' in save, 'save_service: atomic write / backup missing')
tm = (ROOT / 'world/chunks/track_manager.gd').read_text()
need('length * 0.5' in tm and 'Chunk_' in tm, 'track_manager: chunk tiling contract missing')
mode = (ROOT / 'core/game_mode_service.gd').read_text()
need('stable_hash' in mode and 'get_date_dict_from_system(true)' in mode, 'game_mode_service: stable seeds / UTC keys missing')
for mode_name in ('ENDLESS', 'STORY', 'DAILY', 'WEEKLY', 'EVENT', 'TRAINING', 'GHOST', 'CHALLENGE'):
    need(mode_name in mode, f'mode contract missing: {mode_name}')
for path in ('docs/FEATURE_MATRIX.json', 'docs/PROGRESS_MANIFEST.json', 'docs/ASSET_REGISTRY.json', 'docs/AUDIO_REGISTRY.json'):
    try: json.loads((ROOT / path).read_text())
    except Exception as exc: failures.append(f'{path} is not valid JSON: {exc}')
need((ROOT / 'tests/qa_harness.gd').read_text().count('func _initialize()') == 1, 'qa_harness must use _initialize() (autoloads do not exist yet in _init)')
if failures:
    print('FAIL: source-level release smoke checks')
    for f in failures: print(' -', f)
    sys.exit(1)
print('PASS: source-level release smoke checks')
