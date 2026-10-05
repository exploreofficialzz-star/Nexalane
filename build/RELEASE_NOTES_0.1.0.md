# NEXALANE 0.1.1 — Release Candidate Notes

## Included

- Complete runnable endless-run core with mobile input and desktop simulation.
- Deterministic procedural route chunks and district progression.
- FLOW, scoring, collectibles, hazards and set-piece markers.
- Local-first persistence with save migration.
- Economy, progression, missions, achievements, shop and season systems.
- Social/competitive adapters for leaderboards and ghosts.
- Ads, billing, backend and remote config adapter surfaces.
- Accessibility/localization-ready configuration.
- Icon and procedural 3D runtime assets.
- Static QA harness and export configuration.

## Publisher configuration before production

- Inject Android signing / Play Console credentials.
- Configure live ads, billing, backend and analytics provider credentials.
- Add owned legal URLs.
- Run physical-device performance and certification tests.


## 0.1.1 engineering increment

- Added runtime InputMap action initialization for consistent keyboard/controller action routing.
- Preserved touch/swipe controls without duplicate keyboard input processing.
- Normalized run distance to start at 0 m for every run.
- Corrected procedural obstacle collision volumes to align with rendered obstacle geometry.
- Refreshed static verification and progress manifest.
