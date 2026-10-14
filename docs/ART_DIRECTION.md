# Art direction and asset contracts (0.5.0)

**Look:** rain-slicked night city. Dark navy sky with a warm orange horizon, cool cyan fills, orange / cyan / magenta neon, wet asphalt, gold orbs, a bare-headed young athlete in a black hooded tech jacket with orange piping, pack, fingerless gloves and knee pads (matches `assets/icon/nexalane_icon_master.png`).

## Regenerating
`python tools/generate_procedural_assets.py [--only textures|ui|models|audio] [--skip-audio]` - deterministic, needs numpy + Pillow + scipy (+ ffmpeg for music). Source lives in `tools/assetgen/`.

## Model contract (so hand-made models can replace the generated ones)
* glTF 2.0 binary in `assets/models/<id>.glb`, metres, +Y up, origin on the ground.
* Runner / coin / nova face **+Z** (travel direction). Obstacles and street props face **-Z**: their "front" looks back at the oncoming player; the level code rotates props by +/-90 degrees so the -Z side faces the road.
* `runner_base.glb` (0.6.0: the CARTOON runner) is ONE skinned mesh on the 25-bone skeleton of `tools/assetgen/toon_rig.py` (same bone names and order as the old human rig: Hips, Spine, Chest, Neck, Head, Left/RightShoulder, UpperArm, LowerArm, Hand, UpperLeg, LowerLeg, Foot, Toes, plus the spring bones Pack, Hood, HairFront, HairBack). Identity rest rotations, faces +Z, feet on y = 0, 1.93 m with the cap. Four surfaces: `matte` (vertex-coloured skin / jeans / shoes / pack), `RunnerAccent` (hoodie, cap, toe caps - grey vertex colours, tinted at run time by the runner colour), `RunnerGlow` (emissive strips, tinted too) and `RunnerOutline` (unlit dark inverted-hull shell = the cartoon outline, skinned with the same weights). Budget 9000 triangles including the shell (8484 now). Pose preview: `python tools/preview_toon_poses.py` -> `docs/previews/toon_pose_sheet.png`. The old realistic human (`human.py`, `human_rig.py`, `gait_model.gd`) is kept for reference and still passes its own port check.
* Materials named `glow` become shared unshaded HDR (bloom) materials; `facade_a..d` are replaced with the shared textured facade materials (`MaterialLibrary`).
* Obstacle sizes / kinds are defined in `world/obstacles/obstacle_catalog.gd` (collider size, hover height, JUMP / SLIDE / DODGE). Keep a model's silhouette inside its collider.
* Budgets: <= 9000 triangles and <= 24 surfaces per model (`tools/performance_budget.py`).

## Textures
Road tile = 18 m x 9 m (sidewalks, curbs, lane paint baked in), facade tile = 12.8 m x 25.6 m (4 bays x 8 floors). Normal maps are OpenGL (+Y) style; roughness is the red channel (`_r`), facade roughness / metal live in the green / blue channels of `_mr`.

## Audio
All loops are 120 BPM, 16 bars (32 s). The `chase` and `overdrive` stems are rhythmic only, so they fit every district key.
