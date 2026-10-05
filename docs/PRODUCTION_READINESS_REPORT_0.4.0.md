# NEXALANE Production Readiness — 0.4.0

## Product state
NEXALANE is frozen here as the **Full Game Candidate**. The planned launch experience is implemented as a complete offline-safe game with production service adapters. This is not an MVP or prototype build.

## Implemented game content
- 8 districts and deterministic streaming track generation
- 84 reusable chunk definitions, 5 route classes, 60 obstacle IDs / 15 geometry families
- 16 runner catalog entries with role modifiers and visual variants
- Endless, 12-chapter Story, Daily, Weekly, Event, Training, Ghost and Challenge modes
- Flow, scoring, powers, collectibles, collision/revive, route rewards and set pieces
- Garage, missions, shop, season, achievements, leaderboards and settings surfaces
- Save schema v6 with migration and nested default normalization
- Deterministic seeds, replay tokens, local ghost recording/playback and run validation adapter
- Consent-gated analytics/ads, billing adapter, backend/cloud-save adapter and live-ops fallback
- Accessibility controls, haptics, reduced flashes, graphics/FPS profile and localization-ready strings
- 18 PNG assets, 10 importable GLB models, 16 WAV SFX and 13 OGG music tracks
- Weather/time variants, Flow audio intensity, route decals, shield/Flow/collectible/scanner feedback

## Verified in the execution environment
- Full `res://` reference audit
- PNG, GLB, WAV and OGG integrity validation
- Static GDScript hygiene and structural checks
- Performance/static asset budget
- Mode/objective contracts for all advertised modes
- Save migration and nested default normalization
- Deterministic registry and replay token contracts
- Production tooling Python syntax
- Release metadata consistency

## External gates that cannot be executed here
1. Godot 4.7.2 engine import, script compilation and scene execution.
2. Android/iOS export template installation and platform SDK builds.
3. Physical-device FPS, memory, thermal, touch and suspend/resume certification.
4. Real ad, IAP, backend, StoreKit/Play Billing and cloud credentials.
5. Publisher signing certificates/keystore, store registration and legal URLs.
6. Final human art direction, localization review and store compliance review.

These are not hidden or fabricated as complete. They are the only remaining gates because they require engine binaries, physical hardware, publisher accounts, or publisher-owned credentials outside this workspace.
