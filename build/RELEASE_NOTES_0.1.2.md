# NEXALANE v0.1.2

## Engineering increment
- Fixed obstacle construction ordering that could prevent script compilation.
- Corrected follow-camera yaw so the runner sees the forward track.
- Hardened save migration against malformed/missing nested sections.
- Synchronized runtime/project product version metadata to 0.1.2.
- Synchronized runner power state with the power service.
- Added/retained project InputMap actions for keyboard/controller consistency.

## Verification
- 73 project files
- 34 GDScript files
- 22 project resource references checked
- 0 missing project references
- 0 TODO/FIXME/TBD markers in GDScript
- Balanced-delimiter static scan passed

Engine import/export still requires a local Godot 4.7.x installation and platform SDKs.
