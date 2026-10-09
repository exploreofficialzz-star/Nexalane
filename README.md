# NEXALANE: 3D Endless Runner

Version **0.4.6** - Godot 4.7.x, GL Compatibility renderer (OpenGL ES 3), portrait, Android first.

A rain-soaked night-city endless runner: three lanes, jump / slide / dodge, Flow multipliers, route forks, eight districts, daily / weekly / story / event / ghost modes, garage, season pass and live-ops hooks.

## Start here
1. `godot --headless --path . --import`
2. `godot --headless --path . res://tests/QA.tscn`  (expects `PASS: all checks`)
3. Open in the editor and press Play (`ui/Main.tscn`). Desktop controls: A/D or arrows (lane), W / Space (jump), S (slide), E (power), Esc (pause).

## Blank screen on a phone?
See `docs/DEBUG_BLANK_SCREEN.md` - install the debug APK from CI; it shows a startup report on screen and CI now prints the real engine errors.

## What changed in 0.4.6
See `build/RELEASE_NOTES_0.4.6.md` - renderer switched to Compatibility, staged boot with a loading screen and startup report, debug APK and engine smoke test in CI.

## What changed in 0.4.5
See `docs/AUDIT_REPORT_0.4.5.md` - 30+ defects fixed (the project could not compile) and the whole asset layer rebuilt.

## Layout
`autoload/ core/ services/ economy/ progression/ social/ liveops/` services and rules - `gameplay/` runner, camera, flow, powers - `world/` track planner / manager, props, environment, models - `ui/` HUD + theme - `assets/ audio/` generated content - `tools/` generators and static gates - `docs/` reports and specs.

## Quality gates (no engine needed)
`python tools/release_gate.py` runs the GDScript static checker, production audit, performance budget and smoke test.
