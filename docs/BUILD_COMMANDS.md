# Build Commands

Target editor: Godot 4.7.x (Mobile renderer). The project settings assume portrait phones.

First time on a machine (imports textures, models, fonts, audio):

    godot --headless --path . --import

Engine regression harness (autoload-safe, never touches your save):

    godot --headless --path . -s tests/qa_harness.gd

Open / run:

    godot --editor --path .
    godot --path .

Android (SDK + export templates configured; presets live in `export_presets.cfg` in the project root):

    godot --headless --path . --export-debug "Android Debug" build/nexalane_debug.apk
    godot --headless --path . --export-release "Android Release (AAB)" build/nexalane_release.aab

The AAB needs the Android build template (Project > Install Android Build Template, once) and your keystore, which must be
supplied in the Export dialog or via environment variables - never commit it.

iOS: use the "iOS" preset on a macOS host, then sign in Xcode / App Store Connect.

Static gates (Python 3.10+, numpy, Pillow, scipy; ffmpeg for audio checks):

    python tools/gd_static_check.py --warn     # stand-in compiler checks for all GDScript
    python tools/production_audit.py
    python tools/performance_budget.py
    python tools/release_gate.py               # everything, writes docs/RELEASE_GATE_<version>.json

Regenerate every texture, model and audio file:

    python tools/generate_procedural_assets.py            # all
    python tools/generate_procedural_assets.py --only models
    python tools/generate_procedural_assets.py --skip-audio
