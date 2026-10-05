# GODOT PRODUCTION ARCHITECTURE

## Engine
Godot 4.7.x stable branch.

## Rendering
Primary: Mobile renderer.
Fallback: Compatibility profile when required by a device class or hardware test.

## Project structure
```text
res://
  autoload/
  core/
  gameplay/
    runner/
    movement/
    flow/
    powers/
  world/
    districts/
    chunks/
    obstacles/
    events/
    environment/
  progression/
    missions/
    mastery/
    achievements/
  economy/
    currencies/
    shop/
    offers/
  social/
    leaderboards/
    ghosts/
  liveops/
    seasons/
    events/
  services/
    analytics/
    ads/
    billing/
    backend/
    remote_config/
  save/
  ui/
  audio/
  vfx/
  localization/
  tests/
  assets/
```

## Autoload candidates
- AppState
- SaveService
- AnalyticsService
- EconomyService
- ProgressionService
- RunDirector
- AudioService
- AdsService
- BillingService
- BackendService
- RemoteConfigService
- LiveOpsService
- AccessibilityService

Keep autoloads narrow; avoid global god objects.

## Core resources
Use Resources for:
- runner definitions;
- obstacle definitions;
- chunk metadata;
- reward tables;
- mission definitions;
- cosmetic definitions;
- offers;
- event definitions;
- district profiles.

## Deterministic generation
Every run receives a seed. A run can be reconstructed from:
`seed + content_version + tuning_version + player_difficulty_band`.

## Pooling
Pool:
- obstacles;
- collectibles;
- VFX emitters;
- route markers;
- environmental NPCs;
- common UI effects.

## Streaming
Only keep the active horizon plus a small prewarm window. Dispose or recycle far-behind chunks immediately.

## Collision
Use explicit runner colliders and obstacle interaction volumes. Prefer deterministic gameplay collision over full rigid-body simulation for core lane movement.

## Animation
Use AnimationTree/state-machine patterns for runner locomotion and separate gameplay-state tags from visual states.

## Service adapters
Game code must not directly depend on AppLovin, Play Billing, StoreKit, or a specific backend. Use interfaces and provider adapters.

## Error handling
Never crash on missing remote config. Use validated local defaults. Never block the run because analytics is offline.

## Save migrations
Every save version gets a migration path. Never silently discard data.

## Device tiers
Define Low / Mid / High profiles for:
- render scale;
- shadow quality;
- particle budget;
- world detail;
- post-processing;
- texture mip bias;
- FPS cap.

## Android release
Use Gradle export configuration when required for integrated plugins. Configure app icon, splash, package ID, version code/name, permissions and Play-specific settings. Keep signing material outside source control.

## iOS release
Use Godot's iOS export and StoreKit 2 adapter. Validate plugin versions carefully before release because the Godot StoreKit 2 integration may change.
