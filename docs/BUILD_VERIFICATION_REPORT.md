# NEXALANE 0.4.5 - build verification

## Verified in the authoring container (no Godot binary available)
- GDScript static check: 0 errors / 0 warnings over all scripts (it finds all 14 compile errors in 0.4.4 when run against it)
- 41 GLB models structurally valid (accessors, bounds, indices, normals, winding, textures), <= 7096 triangles each
- 62 PNG files valid; 34 audio files decode, no clipping, none silent; registries match the files and hashes
- Project settings that break Android exports are correct; export presets are in the project root
- Version numbers agree between project.godot, autoload/app_state.gd and the export presets

## NOT verified (needs the engine / devices)
Editor import, script compilation inside Godot, tests/qa_harness.gd, rendering under Godot's lighting, physics feel, performance on devices, store builds.
Run the "first run" steps in docs/AUDIT_REPORT_0.4.5.md and report any editor errors.
