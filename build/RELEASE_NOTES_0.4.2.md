# NEXALANE 0.4.2

Full-game production hardening increment.

- Registered authored runner model in runtime model library.
- Fixed HUD indentation/parse blocker.
- Added concrete Challenge objectives and modifier effects.
- Added Ghost objective contract.
- Expanded route forks to include Secret and Chaos routes.
- Restored persisted remove-ads entitlement on launch.
- Added reproducible release-gate audit.
- Updated version metadata and checksums.

## External release gates

Godot 4.7.2 engine import/compile, Android/iOS export, physical-device QA, production signing, store services, and production ad/IAP/backend providers require external SDKs, credentials, and devices. They are explicitly not represented as passed by this package.
