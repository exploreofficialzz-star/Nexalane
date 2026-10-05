# NEXALANE 0.3.0 — Production Candidate

## Included
- Expanded procedural 3D prop library: buildings, street lights, neon signs, route rails and route signage.
- District-aware wet/dry road textures and brushed-metal obstacle materials.
- 15 obstacle family geometries represented across the 60-ID catalog.
- 16 runner IDs with procedural visual/role variants, shield ring and Flow feedback.
- 18 PNG assets, 16 WAV audio assets and 13 compressed OGG music tracks.
- District music routing plus chase/overdrive intensity layers.
- Garage, Missions, Shop and Settings surfaces backed by persistence/services.
- Consent-gated analytics/ads while retaining offline play.
- Mission persistence, purchase idempotency, remote-config bounds and atomic saves.
- App-background autosave/analytics flush and pause/resume state.
- Deterministic procedural asset/audio generation and a standalone production audit.

## Verification
- Resource references: PASS.
- PNG/WAV/OGG validation: PASS.
- Content-count and data/service checks: PASS.
- Static GDScript hygiene: PASS.
- ZIP integrity: PASS after packaging.

## External gates
- Godot 4.7.2 import/compile/export.
- Android/iOS SDK and signing.
- Physical-device FPS/memory/load testing.
- Production backend, billing, ads and analytics credentials.
- Final authored art-direction approval and store captures.
