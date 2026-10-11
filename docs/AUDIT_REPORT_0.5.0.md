# NEXALANE 0.5.0 - human movement audit and rebuild

Scope: everything that makes the runner (and the ghost runners) look and move like a person. Verdict on 0.4.6: the movement code
was a placeholder - a rigid robot driven by sine waves. 0.5.0 replaces the character, the gait, the pose logic and the feedback
around it. Nothing in gameplay physics, tuning, scoring, saves or the track was changed.

**Honest status:** there is no Godot binary in the build container. Every claim below is marked *verified here* (run in the
container) or *needs the engine* (first-run checklist at the end).

## 1. Findings in 0.4.6

| # | Finding | Effect |
|---|---------|--------|
| M1 | `runner_base.glb` was ten rigid boxes/capsules with a helmet and visor (7,096 triangles, **23 surfaces**), not the bare-headed man in a hooded jacket of the reference art. | Looked like a robot; limbs cracked and intersected at every bent joint. |
| M2 | Cadence was `clamp(speed / 5, 2.4, 5.8)` cycles per second = 6.4 steps/s at 16 m/s and **11.6 steps/s at 31 m/s** (a human tops out near 5). | Legs blurred like a cartoon; no speed felt real. |
| M3 | Legs were sine waves: knee = `max(0, sin)`, no foot / ankle / toe, no stance and flight phases, bounce = `abs(sin) * 0.05` unrelated to ground contact. | Feet never planted; no weight. |
| M4 | Upper body was rigid: no pelvis rotation or drop, no counter-rotating shoulders, no head stabilisation, no shoulder girdle, fixed elbow angle. | Stiff, mannequin-like torso. |
| M5 | Posture ignored speed and acceleration; the run started at full speed with no drive phase; the countdown showed a upright idle. | No sense of effort or of a start. |
| M6 | Lane change only rolled the hips (`-vx * 0.02`). | No turn toward the direction of travel, no head lead, no banking about the feet. |
| M7 | Jump and slide were two static pose blends: no take-off drive, no flight phases, no landing preparation or absorption; the slide recline left the shins almost vertical. | Floaty jumps, no impact. |
| M8 | On a crash the runner froze, then eased to the standing idle pose at the crash point. If the run ended in the air, `_physics_process` stopped integrating gravity, so the runner **hovered** there (also on the results / revive screen). | Death looked like nothing happened. |
| M9 | Ghost runners were never animated (bind pose gliding along the recorded path). | Ghost mode looked broken. |
| M10 | Limb animation ran on physics ticks (60 Hz) while body and camera are interpolated. | Limb stepping on 90 / 120 Hz phones. |
| M11 | No footsteps, no splashes, no camera reaction to landings. | Locomotion was silent; landings weightless. |
| M12 | The runner was the heaviest object in the scene (23 draw calls). | Wasted GPU time on mid-range phones. |
| M13 | The model contract was tied to ten node names. | Real characters / motion capture could not be dropped in. |

## 2. What was built

### Character (`tools/assetgen/human.py`, `human_rig.py`, `skin_preview.py`)
* One **skinned human**, 1.836 m, 8,089 triangles, **5 surfaces** (RunnerCloth, matte, metal, RunnerAccent, RunnerGlow), 25 bones named
  like Godot's humanoid profile (Hips, Spine, Chest, Neck, Head, shoulders, arms, legs, feet, toes) plus four secondary bones
  (Pack, Hood, HairFront, HairBack). All rest rotations are identity.
* Anatomical proportions (Drillis-Contini), tapered muscle-shaped limbs, a real head (jaw, brow, nose, eyes with iris and lids,
  lips, ears, swept-back hair locks), hooded jacket with orange piping, harness, low pack with glow strip, fingerless gloves,
  wrist device, cargo trousers with knee pads, running shoes. Matches the hero in `assets/icon`.
* Skin weights are 1-D blends along each limb / the spine (smoothstep), shoulders blend into the clavicle, hair tips blend into
  spring bones. Import settings for the runner: no LOD / shadow-mesh rewrite, no vertex compression, no tangents.

### Gait (`tools/gait_reference.py` -> `gameplay/runner/gait_model.gd`)
* Joint curves follow published running kinematics. The **stance half of the cycle is solved with a planar two-bone IK**
  (`tools/gait_synth.py`): heel-to-ball roll-over of a planted foot and a spring-mass vertical path (high at touch-down and
  toe-off, lowest at mid-stance). The swing half keeps hand-keyed heel recovery.
* The ankle is derived from the **absolute foot pitch**, so the foot is flat at mid-stance whatever the hip and knee do.
* The pelvis height is computed from foot contact (lowest of heel / ball / toe on the floor) and follows a ballistic arc in the
  two flight phases: the feet can not sink into the ground by construction.
* Pelvis rotation and obliquity, counter-rotating thorax, head stabilisation, contralateral arm swing with elbow 85-109 deg,
  shoulder-girdle motion, toe roll-off.

| Game speed | Intensity | Cadence | Steps/s (old) | Stance | Flight | Vertical oscillation |
|---|---|---|---|---|---|---|
| 8 m/s | 0.40 | 1.69 c/s | 3.4 (4.8) | 32 % | 22 % | 4.0 cm |
| 16 m/s | 0.70 | 2.02 c/s | 4.0 (6.4) | 29 % | 34 % | 5.4 cm |
| 24 m/s | 1.00 | 2.35 c/s | 4.7 (9.6) | 25 % | 39 % | 8.0 cm |
| 31 m/s | 1.00 | 2.49 c/s | 5.0 (11.6) | 25 % | 38 % | 8.0 cm |

Game speeds (16-31 m/s) are beyond any human (record 12.4 m/s), so the legs run at flat-out sprint effort and only cadence, lean
and arm drive keep growing.

### Animator (`gameplay/runner/runner_animator.gd`)
Layers blended in this order: idle (breathing, weight shift, head drift) -> run -> countdown "get set" stance -> air (take-off
drive, hurdle-style leap with the leg that was swinging as lead leg, landing preparation timed from the vertical velocity) ->
slide (reclined, legs forward, whole body under the 0.95 m hit box) -> landing absorption (scaled by the fall speed) -> hit
(recoil, stumble, winded crouch, held until the run restarts). Plus: standing-start launch, acceleration / boost lean, lane-change
shoulder and head lead with outside-arm flare, spring-driven pack, hood and hair (hair swept back by the speed), and
`foot_strike(side, intensity)` events.

### Integration
* `runner_controller.gd`: body animation moved to `_process` (render rate); whole-body yaw and bank about the feet on physics
  ticks; footstep SFX (3 variants) and puddle splash at every foot strike; crash triggers the hit reaction; **a run that ends in
  the air now finishes its fall**; `reset_for_menu()` stands the runner up.
* `main.gd`: ghosts run with the same animator (speed, lane and flight derived from their recorded path); landing dips the camera.
* `chase_camera.gd`: `dip()`. `audio_service.gd`: `footstep_a/b/c` (generated, -17 dB, pitch-varied).

## 3. Verification

*Verified here*
* `tools/release_gate.py`: GDScript static check (51 scripts), production audit, performance budget (runner 8,089 tris / 5 surfaces,
  models 2.7 MB), smoke test, and the new `check_gait_port.py`: a translator that runs `gait_model.gd` as Python and compares
  every table, constant and pose with the reference on 60 random gait states - **identical**.
* GLB checks (`validate_skin`): 25 joints in the right order, node chain reproduces the rest positions, inverse-bind matrices,
  weights sum to 1, joint indices in range, soles on y = 0, height 1.836 m, triangle budget.
* Numerics: over 200 phases at 8 / 16 / 24 / 31 m/s no foot point is below the floor; no double support; vertical oscillation and
  cadence in the table above.
* `docs/previews/runner_pose_sheet.png` is rendered from the **shipped** `runner_base.glb` with the reference pose maths
  (run cycle side / back, jump, landing, slide, countdown, hit, idle, hero view).

*Needs the engine* (first run)
1. `godot --headless --path . --import`, then `godot --headless --path . -s tests/qa_harness.gd`. New tests: `_test_gait_model`
   (golden values) and `_test_runner_rig` (skeleton binds, height, surfaces, run / jump / slide / crash drive the bones without
   breaking them, foot strikes counted, slide under 0.95 m).
2. Run the game: check that the runner is upright (not mirrored or rotated), arms and legs bend the right way, the face points
   forward, the pack glows on the back, no flicker when leaping or sliding (culling margin is widened), ghosts run.
3. If the QA harness reports "no usable humanoid skeleton", open `runner_base.glb` in the editor's import dock: bone names must
   match `RunnerAnimator.BONE_NAMES` (the animator also matches names ignoring case and punctuation).
4. Frame time: the animator costs a few hundred microseconds per runner per frame in GDScript; profile on a low-end phone.

## 4. Tuning and extending
* Gait tables, cadence, bounce, poses: edit `tools/gait_reference.py`, run `python tools/gen_gait_model.py` and
  `python tools/check_gait_port.py`. Stance solution: `tools/gait_synth.py`. Preview: `python tools/render_runner_poses.py`.
* Lane-change bank / yaw: `_update_visual_motion` in the controller. Hair / pack / hood springs: `_update_secondary`.
* **Real motion capture later:** bone names equal Godot's humanoid profile, so a Mixamo / Rokoko run cycle can be retargeted with a
  `BoneMap`. Keep `RunnerAnimator` for the events and the non-run layers, or replace its run layer with an `AnimationPlayer`.
* Regenerate the model: `python tools/generate_procedural_assets.py --only models` (the other 40 models are byte-identical).

## 5. Known limits
* The legs cannot match the ground speed: the floor passes 2-3x faster than a planted human foot. Inherent to 16-31 m/s.
* Linear blend skinning loses a little volume at the hips in the slide and crouch poses.
* No finger or face animation (the face is modelled, not animated); the ghost's flight and slide are inferred from a 4 Hz path.

## 6. Files
New: `gameplay/runner/gait_model.gd`, `runner_animator.gd`; `tools/assetgen/human.py`, `human_rig.py`, `skin_preview.py`;
`tools/gait_reference.py`, `gait_synth.py`, `gen_gait_model.py`, `check_gait_port.py`, `plot_gait_sheet.py`,
`render_runner_poses.py`; `audio/sfx/footstep_a|b|c.wav(.import)`; `docs/previews/runner_pose_sheet.png`.
Changed: `assets/models/runner_base.glb(.import)`, `runner_controller.gd`, `ui/main.gd`, `chase_camera.gd`, `audio_service.gd`,
`tests/qa_harness.gd`, `tools/generate_procedural_assets.py`, `tools/assetgen/models_play.py`, `audiogen.py`, `release_gate.py`,
versions (`0.5.0`, Android version code 7), docs and registries.
