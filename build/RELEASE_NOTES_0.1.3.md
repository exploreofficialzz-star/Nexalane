# NEXALANE v0.1.3

## Gameplay/state hardening
- Added a unified pause/resume flow for the HUD and desktop `ui_cancel` input.
- Paused runs now stop runner physics while preserving run state.
- Centralized runner power requests through `PowerSystem` instead of allowing the runner to independently activate powers.
- Added explicit power deactivation and expiration events.
- Shield consumption now notifies `PowerSystem`, preventing stale active-power state after a hit.
- Reset pause state automatically when a new run begins or a run ends.

## Verification
- 74 project files
- 34 GDScript files
- 22 project resource references checked
- 0 missing project references
- 0 TODO/FIXME/TBD markers in GDScript
- Balanced-delimiter scan passed
- Version metadata aligned to 0.1.3
- Pause/power synchronization references verified statically

Engine import/export still requires a local Godot 4.7.x installation and platform SDKs.
