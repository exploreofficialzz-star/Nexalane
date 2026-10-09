# NEXALANE 0.4.6 - startup audit (blank screen after installing the APK)

## Scope and method
No Godot engine, Android SDK or device was available for this audit, so everything below is static analysis.
- Read the whole startup path: all 25 autoloads, `ui/main.gd`, `ui/hud.gd`, `ui/ui_theme.gd`, world / track / props /
  models / materials, runner, camera, player session, flow / power / score systems.
- Mechanical checks on every script: brackets, strings and indentation; every call into a project class or autoload
  (member exists, argument count); `class_name` versus autoload-name collisions; `:=` inference from untyped values;
  overrides of engine methods; all 108 literal `res://` paths resolve; import metadata present.
- Repo gates `python tools/release_gate.py`: 4/4 PASS before and after the changes (49 scripts, 0 errors, 0 warnings).

## Findings
1. No compile-level defect found by static review. The checks are heuristic; only an in-engine run is conclusive.
2. The project had never run inside Godot before the first phone install (see `AUDIT_REPORT_0.4.5.md`), and release
   exports do not report GDScript runtime errors, so any startup error looks like a blank screen.
3. Nothing is drawn until the whole world is generated inside `ui/main.gd` `_ready()` (6 chunks, props, models, HUD).
   On a slow phone that is indistinguishable from a hang.
4. The HUD starts under a fully opaque black fade rectangle that is only removed at the very end of the HUD's startup.
   If anything aborts earlier the screen stays black.
5. The Vulkan "Mobile" renderer with MSAA and glow on by default is the riskiest combination on weaker or older phones.
6. CI built and signed the APK but never started the game, so no engine error could surface before a device test.
7. Minor: README QA command used `-s` on a script that is not a MainLoop; the workflow validated a hard-coded
   `RELEASE_GATE_0.4.5.json`; `docs/SHA256_MANIFEST.json` was already out of date for `docs/ASSET_REGISTRY.json`,
   `docs/BUILD_COMMANDS.md` and `tests/qa_harness.gd`.

The root cause of the blank screen is NOT confirmed. 0.4.6 removes items 3 to 6 and makes any remaining failure visible.

## Changed files (repo paths)
- `project.godot` - GL Compatibility renderer, `BootTrail` autoload first, version 0.4.6.
- `autoload/boot_trail.gd` (new) - loading screen, startup report, flight recorder, debug error capture.
- `ui/main.gd` - staged boot, `_booted` guard, trail logging.
- `ui/hud.gd` - opening-fade failsafe, trail logging, Settings -> VIEW STARTUP LOG.
- `core/device_profile_service.gd` - no glow / MSAA by default on phones, no 3D scaling call on Compatibility.
- `.github/workflows/build.yml` - engine smoke test, engine QA harness, engine logs artifact, debug APK artifact.
- `autoload/app_state.gd`, `export_presets.cfg` - version 0.4.6 / code 6.
- `README.md`, `docs/BUILD_COMMANDS.md`, `docs/DEBUG_BLANK_SCREEN.md`, `build/RELEASE_NOTES_0.4.6.md`,
  `docs/AUDIT_REPORT_0.4.6.md`, `docs/SHA256_MANIFEST.json`, `docs/RELEASE_GATE_0.4.6.json` - docs and manifests.

## Still to verify (needs the engine or a device)
1. Output of the CI step "Engine smoke test" (first real in-engine boot of the project).
2. Result of the CI step "Engine QA harness".
3. First run of the debug APK on a phone; then the release APK.
