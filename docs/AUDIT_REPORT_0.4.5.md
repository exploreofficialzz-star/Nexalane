# NEXALANE 0.4.4 -> 0.4.5: audit, fixes and asset rebuild

**Read this first - what was and was not verified.** The Godot binary was not available where this work was done
(no network, no engine). Everything below was verified *statically*: a purpose-built GDScript checker
(`tools/gd_static_check.py`), structural validation of every 3D model, decoding of every audio file, and
software-rendered previews of the assets. **Nothing has been run inside Godot yet.** The 0.4.4 audit also never
ran the engine, and it reported PASS on a project that could not compile. Please do the "first run" steps at the
bottom and send me anything the editor prints - I will fix it.

## 1. Project-breaking defects (the game could not start)

| # | Where | Problem | Fix |
|---|-------|---------|-----|
| 1 | `world/chunks/track_manager.gd` `_create_collectible` | Indentation break (parse error). `TrackManager` could not load, so `Main` failed. | `TrackManager` rewritten. |
| 2 | 7 autoload scripts (`MissionService`, `AchievementService`, `LeaderboardService`, `GhostService`, `ShopService`, `SeasonEngine`, `EventEngine`) | `class_name` equal to the autoload name -> "Class hides an autoload singleton" (parse error). | `class_name` is now `<Name>Impl`. |
| 3 | `player_session.gd` x3, `runner_controller.gd`, `live_ops_service.gd`, `ghost_service.gd`, `track_manager.gd` x2 | `var x := <Variant expression>` - `INFERENCE_ON_VARIANT` is an **error** by default in Godot 4. | Explicit types. The static checker now blocks this class of bug. |
| 4 | `tests/qa_harness.gd` | Tests ran in `_init()`, where autoload singletons do not exist yet. | Uses `_initialize()`. |
| 5 | Project / export | `export_presets.cfg` sat in `build/` (Godot only reads the project root); no ETC2/ASTC import (Android export fails); portrait orientation not set (Android starts in landscape); Back button quits the app (`quit_on_go_back` default); no VIBRATE permission (haptics fail); `docs/`, `tools/` and the spec prompts would ship in the APK. | Fixed in `project.godot` + root `export_presets.cfg` with `exclude_filter`. |

## 2. Gameplay-breaking defects

| # | Problem | Fix |
|---|---------|-----|
| 6 | **Jumping was impossible**: the jump impulse was applied, then overwritten by the "stick to floor" velocity in the same frame. | Impulse applied after the floor logic, plus coyote time (0.10 s), jump buffering (0.14 s), fast-fall + queued slide. |
| 7 | **Declining a revive froze the game**: `_finish_run` returned early because `active` was already false. No timeout either. | `finished` flag, 6 s countdown, ad-hold, results screen. |
| 8 | **Phase Shield was useless**: the shield was consumed, the runner kept pushing into the same obstacle and died one frame later. | The absorbed obstacle is removed; 1.2 s invulnerability (touched obstacles are phased through). |
| 9 | Revive respawned 18 m ahead, possibly inside an obstacle, with no protection. | 2.4 s invulnerability and obstacles in the landing zone are cleared. |
| 10 | **Invisible pits**: the ground box was centred on the chunk origin while chunks advanced by their full length -> gaps up to 6 m (or overlaps) between chunks. | Chunks are positioned at their start; ground tiles exactly; 1 m collider overlap. Covered by a harness test. |
| 11 | Magnet power never collected anything (the metadata it looks for was never set). | Coins carry `collectible_value`; collected coins now fly to the runner. |
| 12 | Role / event / challenge speed bonuses vanished after ~90 m and `max_speed` was never used. | Permanent `speed_bonus`, `target_speed()` and `max_speed`. Challenge multipliers no longer reset when a power ends. |
| 13 | Powers had no cooldown -> an infinite free shield. | Per-power recharge (18-34 s) with a HUD ring. |
| 14 | Near-miss never fired (only when a shield absorbed a hit), so Flow stages 3-4 were almost unreachable. | Real detection: late lane-dodge (< 0.5 s) and clutch jump/slide clears. |
| 15 | Obstacles were random lane picks with spacing shorter than a lane change; every obstacle sat on the ground, so **Slide was never needed**; the "drone" rested on the road. | New `TrackPlanner`: fairness rules, jump / slide / dodge kinds, full-width rows, pairs, per-district families. Overhead obstacles hover at 1.05 m. Invariants fuzz-tested in the harness. |
| 16 | District change fired when a chunk was *spawned* (~250 m early, wrong district at start); each chunk picked a random district for its colours. | Chunks follow their district; announcement when the runner reaches it; music / fog / sky follow. |
| 17 | Seeds not reproducible: previous run's difficulty leaked into the new track, difficulty was read at spawn time, `hash()` differs across engine versions, daily keys used local time. | Difficulty is a pure function of distance; FNV-1a seeds; UTC daily/weekly keys; separate RNG for scenery so graphics settings never change the track. |
| 18 | Live-event modifier never rotated; "Hazard Storm" etc. did nothing. | `EventEngine` rotates daily (UTC); the four modifiers are implemented. |
| 19 | Daily "collect 80" counted 10 per orb (8 orbs). | Counts orbs. |
| 20 | Touch devices double-fired swipes (touch + emulated mouse); swipes only fired on release; the camera rolled with the runner lean. | De-duplicated, fires on drag, camera is independent. |
| 21 | Season: only the *current* tier could be claimed - skipped tiers were lost. | "Claim all". |
| 22 | Billing: a real provider could never grant anything; starter / event / elite bundles granted nothing; "Remove Ads" buyers lost revive and double-reward. | `complete_purchase()` / `fail_purchase()` adapter contract, idempotent per transaction, real bundle contents, rewarded perks free for ad-free players. |

## 3. Data-loss and robustness

* **Progress reset on every launch.** `JSON.parse_string` returns every number as float, and the loader dropped any value whose type differed from the default - credits, level, XP, season XP were all reset. Values are now coerced back to the default's type (harness-tested).
* Save writes had a delete-then-rename gap; now temp file + backup + crash recovery.
* Local remote-config overrides worked in release builds (cheat vector) and ignored ints; debug-only now, with bounds.
* Analytics file grew without limit; now capped and flushed on pause / quit.
* Nova outfits cost 5000+ nova (credit pricing); now 120-420.
* Ghost raced at the *same distance* as the player (could never lead or trail); now a real time-based race.

## 4. UI and audio

* Main menu was positioned off-screen (`position` used with anchors), the top bar overflowed the screen (pause/power buttons pushed out), the consent card was off-screen, only 10/24 outfits were reachable, settings toggles (camera shake, left-handed, reduced flashes) did nothing, fades cancelled each other. The HUD is rewritten with containers, safe-area handling, a theme, 3-2-1 start and resume countdowns, results screen, revive timer, garage outfit equipping.
* Music intensity layers were effectively silent and never turned off; disabling music did not stop the layer. Rewritten (buses, polyphony, cross-fade, layers start on the playhead).
* World: the sun light was never found (auto-generated node name), rain and skyline were fixed at the world origin (gone after the first seconds), one `OmniLight3D` per street light would exceed the Mobile renderer's 8-lights-per-object limit. Now: procedural sky + fog + bloom + tonemapping, additive light pools instead of lights, rain and skyline follow the runner.

## 5. Assets recreated (all original, generated by `tools/generate_procedural_assets.py`)

| Before (0.4.4) | After (0.4.5) |
|----------------|---------------|
| 18 PNGs: flat noise tiles, text-label decals, basic icons | 62 PNGs: tileable PBR road (dry + wet: albedo / normal / roughness, wet reflection map), 4 building facades with lit-window emission maps, 2 skyline silhouettes, holographic route signs with real typography, 4 HUD icons + 15 glyph icons, logo, 6 VFX sprites, launcher / adaptive icons |
| 10 GLBs, 2-9 KB each (boxes, spheres, cylinders) | 41 GLBs, 47k triangles total: articulated runner (23 draw calls, accent colour tintable), 15 obstacle families, 8 buildings (near + far tiers), street light, 3 neon signs, 9 district props and set pieces, coin, nova shard |
| Synth beeps | 21 layered SFX + 13 music loops (120 BPM, 16 bars, seamless; chase / overdrive stems share the grid) |

Poppins (SIL OFL) is bundled for the UI - see `assets/fonts/FONTS.md`. Software-rendered previews are in `docs/previews/`; they are **not** engine screenshots (no engine lighting, fog or bloom).

Art direction follows your key art: rain-slicked night city, black tactical runner with orange accents, orange / cyan neon, gold orbs. Contracts for swapping in hand-made assets are in `docs/ART_DIRECTION.md`.

## 6. Decisions I made that you may want to change

Daily / weekly keys are UTC (weeks start Monday); revive / double-reward are free for "Remove Ads" owners; the season pass gives +50 % tier credits; bundle contents (`BillingService.PRODUCTS`); power cooldowns (`PowerSystem.COOLDOWNS`); nova outfit prices; the colour-blind toggle was removed from Settings because it never did anything.

## 7. Not done / known limits

No in-engine run, so physics feel, camera tuning, performance, shader / import behaviour and the exact look under Godot's lighting are unverified. Ad, billing and backend providers are still adapter stubs (test mode in debug builds). Boards / trails / badges are listed in the catalogue but have no visual effect yet.

## 8. First run (about 5 minutes)

1. `godot --headless --path . --import` (imports the new textures, models, fonts, audio)
2. `godot --headless --path . -s tests/qa_harness.gd` - should print `PASS: all checks`
3. Open the project and press Play. Check the editor's Debugger > Errors panel and send me anything red.
4. `python tools/release_gate.py` for the static gates (no engine needed).
