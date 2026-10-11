# Build Commands

Target editor: Godot 4.7.x (GL Compatibility renderer since 0.4.6). The project settings assume portrait phones.

First time on a machine (imports textures, models, fonts, audio):

    godot --headless --path . --import

Engine regression harness (autoload-safe, never touches your save):

    godot --headless --path . tests/QA.tscn

Open / run:

    godot --editor --path .
    godot --path .

Android (SDK + export templates configured; presets live in `export_presets.cfg` in the project root):

    godot --headless --path . --export-debug "Android Debug" build/nexalane_debug.apk     # startup report on screen, see docs/DEBUG_BLANK_SCREEN.md
    godot --headless --path . --export-release "Android Release APK" build/nexalane_release.apk
    godot --headless --path . --export-release "Android Release (AAB)" build/nexalane_release.aab

The Android package ID is `com.chastech.nexalane`. The AAB needs the Android build template and a production keystore.
The GitHub Actions workflow reads these repository Actions secrets (never commit the keystore or passwords):

    ANDROID_KEYSTORE_BASE64       # base64-encoded .keystore/.jks file, one line
    ANDROID_KEYSTORE_PASSWORD     # keystore password; use the same password for the signing alias
    ANDROID_KEY_ALIAS             # production signing alias

It uploads the signed `nexalane_release.apk` and `nexalane_release.aab` as the `nexalane-android-<commit>` workflow artifact.
For a local signed export, set `GODOT_ANDROID_KEYSTORE_RELEASE_PATH`, `GODOT_ANDROID_KEYSTORE_RELEASE_USER`, and
`GODOT_ANDROID_KEYSTORE_RELEASE_PASSWORD`. Never commit the keystore or passwords.

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

## Human movement tools (0.5.0)
```
python tools/check_gait_port.py            # gait_model.gd must equal tools/gait_reference.py (part of tools/release_gate.py)
python tools/gen_gait_model.py             # regenerate gameplay/runner/gait_model.gd after editing tools/gait_reference.py
python tools/generate_procedural_assets.py --only models   # rebuild runner_base.glb (other models stay byte-identical)
python tools/render_runner_poses.py        # docs/previews/runner_pose_sheet.png from the shipped GLB
```
