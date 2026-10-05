# Art direction and asset contracts (0.4.5)

**Look:** rain-slicked night city. Dark navy sky with a warm orange horizon, cool cyan fills, orange / cyan / magenta neon, wet asphalt, gold orbs, a black tactical runner with orange accents (matches `assets/icon/nexalane_icon_master.png`).

## Regenerating
`python tools/generate_procedural_assets.py [--only textures|ui|models|audio] [--skip-audio]` - deterministic, needs numpy + Pillow + scipy (+ ffmpeg for music). Source lives in `tools/assetgen/`.

## Model contract (so hand-made models can replace the generated ones)
* glTF 2.0 binary in `assets/models/<id>.glb`, metres, +Y up, origin on the ground.
* Runner / coin / nova face **+Z** (travel direction). Obstacles and street props face **-Z**: their "front" looks back at the oncoming player; the level code rotates props by +/-90 degrees so the -Z side faces the road.
* `runner_base.glb` must contain nodes named `Hips, Torso, ArmL, ArmR, ForearmL, ForearmR, LegL, LegR, ShinL, ShinR` with pivots at the joints - the controller animates them. Materials named `RunnerAccent*` / `RunnerGlow*` are tinted per runner / outfit.
* Materials named `glow` become shared unshaded HDR (bloom) materials; `facade_a..d` are replaced with the shared textured facade materials (`MaterialLibrary`).
* Obstacle sizes / kinds are defined in `world/obstacles/obstacle_catalog.gd` (collider size, hover height, JUMP / SLIDE / DODGE). Keep a model's silhouette inside its collider.
* Budgets: <= 9000 triangles and <= 24 surfaces per model (`tools/performance_budget.py`).

## Textures
Road tile = 18 m x 9 m (sidewalks, curbs, lane paint baked in), facade tile = 12.8 m x 25.6 m (4 bays x 8 floors). Normal maps are OpenGL (+Y) style; roughness is the red channel (`_r`), facade roughness / metal live in the green / blue channels of `_mr`.

## Audio
All loops are 120 BPM, 16 bars (32 s). The `chase` and `overdrive` stems are rhythmic only, so they fit every district key.
