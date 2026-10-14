# NEXALANE 0.6.0 - a big cartoon runner, a camera that holds still, a street that is alive

Status: **statically verified only** (GDScript static checker, production audit, performance budget, smoke test, gait port check,
pose renders). There is still no Godot binary in the build container, so nothing below has been seen running in the engine - see
"Verify on your phone first".

## 1. The camera no longer shakes
Why the picture looked unsteady (all found in the 0.5.0 camera code):
* the camera was **rigidly bolted to the runner** - no smoothing at all - and **re-aimed at him every physics tick** (`look_at`), so every bob, jump, ramp bump and lane change went
  straight into the picture (it even followed half of every jump's height);
* a **9-12 Hz positional shake** (`h_offset` / `v_offset`) on every hit, shield hit and **every near miss**, and a sudden **20 cm landing dip**;
* the **FOV swung 62 -> 74 degrees** with speed, stepping once per physics tick;
* separately, rain, skyline, ghost runner and coin spin were moved from `_process` while physics interpolation was still on for them (they can stutter against the interpolated runner).

Now (`gameplay/camera/chase_camera.gd`), inspired by how the classic 3-lane runners frame the action (my own tuning, not their numbers):
* fixed yaw and pitch: the camera looks straight down the track, 13 degrees down, 7.2 m back, 3.35 m up; only the **sideways** (72 % of the
  runner's offset) and **vertical** (30 % of a jump) follow move, with frame-rate independent damping;
* it runs every rendered frame on the runner's **interpolated** transform, with physics interpolation switched off for the camera itself
  (the documented Godot recipe for cameras that follow physics bodies); everything else that moves in `_process` (rain, skyline, ghost, coin spin, ambient life) has it off too;
* **no shake at all**: a hit gives one soft zoom-and-tilt punch, a landing a small settle (`kick()` / `dip()` keep their names);
* FOV 58 degrees with only +3.5 degrees at top speed / boost (smoothed), a little extra distance while accelerating; the menu "hero" framing still glides into the gameplay framing;
* the runner is now about **21 % of the screen height** (13 % before) in the lower half of a portrait phone, horizon at 30 % from the top, all three lanes visible 30 m ahead.

Measured with `python tools/camera_sim.py` (a simulation of both cameras at 60 Hz physics / 90 Hz display - not a phone): shake energy of the runner on screen while running
straight with one near miss = **0.002** vs 0.323 before (about 160 times calmer); in a stretch with a landing, two near misses and a shield hit = 0.32 vs 1.28 (4 times calmer - what is
left is the deliberate hit punch and the smooth camera settle after a jump). Light taps (near misses) no longer touch the camera at all. The runner now slides across the screen in a
lane change (about 70 % of the screen width from lane to lane) instead of the whole picture swinging.

## 2. A big cartoon runner (replaces the dark realistic human, the "bot")
* new model `assets/models/runner_base.glb`: chunky street runner - big head with eyes and a grin, cap, hoodie, backpack, baggy jeans,
  huge sneakers; 25 bones (same names as before), 8 484 triangles including a dark **outline shell**; hoodie, cap, toe caps and glow strips take the
  runner colour (cyan for Kade). Generator: `tools/assetgen/toon.py` (`python tools/build_toon_runner.py`).
* new animation `gameplay/runner/toon_gait.gd`: bouncy sprint (high knees, heel kicks, wide arm pumps, forward lean), springy hop in the flight phases,
  big jump, slide on the backpack, landing, crash recoil / crouch, "get set" stance, idle with look-around, plus **squash and stretch** on take-off and landing.
  The old biomechanical `gait_model.gd` is untouched (its Python port check still passes). Pose sheet: `docs/previews/toon_pose_sheet.png`.
* new **app icon** (all sizes + adaptive layers) rendered from the same 3D character: `python tools/make_icon.py`.

## 3. A living street (`world/props/ambient_life.gd`, no new assets)
Bunting across the street with every flag swaying - a cheering crowd of little bean people (bouncing, waving) - pigeons that sit on the pavement and burst into the air
as you approach - balloons bobbing between the buildings - steam venting from the road - a patrolling drone - neon / lamp halos that breathe and occasionally
stutter (steady glow when "reduced flashes" is on) - windows whose glow breathes out of step. Batched with MultiMesh, only animated within ~175 m ahead of the runner.
The district palettes are lifted from near-black night to a more saturated dusk so the characters and the street read clearly.

## 4. Switched off (not deleted) - `core/feature_flags.gd`
Route forks; the STORY / WEEKLY / EVENT / GHOST / CHALLENGE mode chips (ENDLESS, DAILY, TRAINING remain); the SEASON, TROPHIES and RANKS buttons.
Everything stays in the code, tests and saves: add a name to a list or flip `ROUTE_FORKS` to bring a feature back. Tell me if you want any of these gone for good, or
something else removed (flow bar, powers, objective bar, shop sections ...).

## 5. Not done, on purpose
* **Curved-world shader** (the classic horizon bend). It needs every material converted to a custom shader and, in Godot 4, special handling for shadows; I did not want to ship that
  untested. It is the next step if you want the full effect.
* No audio changes. Ghost runner keeps the old translucent treatment (the mode is hidden).

## Verify on your phone first
1. Build the debug APK as usual. The first frame to check: menu hero (cartoon runner, idle) -> START -> countdown -> run.
2. Watch for: runner colours (hoodie follows the selected runner), outline visible, no pink/black materials, bunting and crowd visible in the first chunks, camera steady in lane changes.
3. If the picture is too dark / bright: `world/environment/world_environment_controller.gd` (`_palette_for`). Camera feel: constants at the top of `chase_camera.gd`.
4. `godot --headless --path . res://tests/QA.tscn` should print `PASS: all checks` (new tests: `_test_toon_gait`, updated `_test_runner_rig`).

## Tooling
`tools/build_toon_runner.py`, `tools/preview_toon_poses.py` (runs the real `toon_gait.gd` through the GDScript translator), `tools/make_icon.py`;
`tools/generate_procedural_assets.py` now builds the cartoon runner and the icon. All 40 other models regenerate byte-identical to 0.5.0.
