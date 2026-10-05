# NEXALANE Production Readiness — 0.3.0

## Status
The workspace is a release-candidate foundation rather than a bare prototype. Core gameplay, deterministic generation, progression, monetization adapters, live-ops structure, procedural 3D content, generated audio, localization scaffolding, accessibility settings, consent handling and release configuration are implemented and statically audited.

## Verified in-container
- 18 PNG assets, including supplied master/512/1024 icons plus generated environment, route, UI and VFX assets.
- 16 WAV assets for SFX/source material and 13 compressed OGG music tracks.
- 8 district music tracks plus menu, event, reward, chase and overdrive layers.
- Procedural environment props, district materials, route signage and Spire imagery.
- 15 obstacle geometry families mapped across the 60-ID obstacle catalog.
- 16 runner IDs with visible procedural role variants and lightweight animation.
- Garage, Missions, Shop and Settings surfaces connected to real services.
- Flow, shield and collectible visual/audio feedback.
- Mission progress persistence and save migrations.
- Consent-gated analytics and advertising with offline play preserved.
- Non-consumable/entitlement purchase idempotency in test mode.
- Remote-config type validation and tuning bounds.
- Atomic save writes, focus-out autosave and analytics flush.
- Resource reference, PNG, WAV, OGG, content-count and GDScript hygiene audits: PASS.

## External production gates
### Engine gate
Import and run under Godot 4.7.2 stable, then perform a real project compile/import check and gameplay smoke run. The engine executable is not installed in this container.

### Device gate
Validate startup, controls, suspend/resume, frame pacing, memory, thermals and low-end Android behavior on representative physical devices; repeat for iOS if that target ships.

### Platform gate
Install Android/iOS export templates and SDKs, configure signing, and produce signed release artifacts.

### Provider gate
Inject production ad, billing, backend, analytics and remote-config credentials and exercise purchase restoration, reconnect and failure flows.

### Art-direction gate
The current art layer is deterministic/procedural and cohesive for the RC. A premium commercial launch still needs a human art-direction approval pass for authored character/environment models, hero materials, final UI brand treatment, animation/VFX polish and store captures.

## Release recommendation
Treat this archive as the **production-candidate workspace**, not a signed store binary, until the external gates above are executed and attached to the release checklist. No engine/device/provider result is being represented as passed without evidence.
