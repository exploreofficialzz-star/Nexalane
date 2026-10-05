# NEXALANE 0.4.3

Production hardening increment from 0.4.2.

## Fixed
- Reset revive, route and per-run state on every new session.
- Reset runner power multipliers and role modifiers on configuration.
- Reset pause state before a new run.
- Added Ghost and Challenge mode labels.
- Added a selectable Challenge Vault surface to Missions.
- Removed duplicate tutorial callback wiring.
- Added deterministic release smoke checks.

## Verification
- Static resource audit: PASS
- Asset/audio/model validation: PASS
- Performance budget: PASS
- Release smoke test: PASS
- Godot engine compile: external gate
- Android/iOS export and device certification: external gate
