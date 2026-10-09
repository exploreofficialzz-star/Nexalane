# NEXALANE 0.4.6

Reported problem: the 0.4.5 release APK installs, shows the app start, then a blank screen. It could not be reproduced
here (no engine or device available), so 0.4.6 removes the likely causes and makes any remaining failure visible.

## Changes
- Renderer switched to GL Compatibility (OpenGL ES 3) - `project.godot`.
- Staged boot, `_booted` guard and trail logging - `ui/main.gd`.
- Opening fade failsafe, trail logging, Settings -> VIEW STARTUP LOG - `ui/hud.gd`.
- New autoload `BootTrail` (loading screen, startup report, flight recorder, error capture) - `autoload/boot_trail.gd`.
- Phone graphics defaults without glow/MSAA; no 3D scaling call on the Compatibility renderer - `core/device_profile_service.gd`.
- CI: engine smoke test, engine QA harness, engine logs artifact, no-secrets debug APK artifact, version-aware gate check
  - `.github/workflows/build.yml`.
- README QA command corrected to `res://tests/QA.tscn`.
- Version 0.4.6 / code 6 in `project.godot`, `autoload/app_state.gd`, `export_presets.cfg`.

## Still unverified
First on-device run of this build, and the in-engine QA harness result. Both are produced by the new CI steps.
