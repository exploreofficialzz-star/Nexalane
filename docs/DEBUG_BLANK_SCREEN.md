# If the game shows a blank screen

Release APKs hide GDScript runtime errors, so a failed start looks like a blank screen. 0.4.6 adds three ways to see
what actually happened. Use whichever is easiest.

## 1. On the phone: debug APK (no cable, no PC)
1. GitHub -> Actions -> the latest run -> Artifacts -> `nexalane-debug-apk-<commit>` -> unzip -> `nexalane_debug.apk`.
2. Uninstall the release build first (the debug build is signed with a different key), then install the debug APK.
3. Launch. Normal start: `NEXALANE / Loading...` for a second or two, then the menu.
4. If the game has not started after 8 seconds the screen turns into a **STARTUP REPORT** (device, GPU, renderer, every
   boot step, captured engine errors). Tap **COPY LOG** and paste it into the chat. **CLOSE** hides it if the game is
   actually running behind it.
5. Later: Settings -> **VIEW STARTUP LOG** reopens the report. On debug builds an **ERR n** badge appears at the top
   whenever the engine logged an error.
6. If the app was killed or froze, the next launch says "The last launch did not finish starting" and the report starts
   with that launch's last steps.

## 2. In CI: no phone needed
Open the run -> step **Engine smoke test** (the real game is booted headless inside Godot; the step prints the first 150
lines of engine output and every line that looks like an error). `nexalane-engine-logs-<commit>` holds the full logs,
including the **QA harness** result. These steps never block an APK; they only report.

## 3. With adb (optional)
```
adb logcat -s godot            # boot trail lines start with [NEXALANE-BOOT]
adb logcat | grep -E "NEXALANE-BOOT|SCRIPT ERROR|ERROR"
```
From Termux: `pkg install android-tools`, then pair with Wireless debugging (`adb pair`, `adb connect`).

## What 0.4.6 changed (and why)
- **Renderer: Vulkan "Mobile" -> OpenGL ES 3 "Compatibility".** Vulkan drivers on many phones are the usual cause of a
  blank screen. To go back, set both `rendering_method` lines in `project.godot` to `"mobile"` and use `"Mobile"`
  instead of `"GL Compatibility"` in `config/features`.
- **Staged boot** (`ui/main.gd`): the menu is built first, the 3D world over the next frames, so something is on screen
  immediately instead of nothing until everything is generated.
- **Loading screen + startup report** (`autoload/boot_trail.gd`).
- **Opening black fade can no longer get stuck** (`ui/hud.gd`).
- **Phone graphics defaults**: no glow and no MSAA unless Quality is set to HIGH (`core/device_profile_service.gd`).
