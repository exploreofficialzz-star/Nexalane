extends Node

## Headless QA harness:   godot --headless --path . -s tests/qa_harness.gd
## (run `godot --headless --path . --import` once first so models/textures are imported)
## It never writes your save file: only in-memory state is touched.

var failures: Array[String] = []
var checks := 0

# `godot -s` parses this script before project autoload identifiers are injected.
# Keep typed handles so the harness works both as a standalone script and in-editor.
var AppState: AppStateService
var AudioService: AudioServiceImpl
var BackendService: BackendServiceImpl
var EconomyService: EconomyServiceImpl
var GameModeService: GameModeServiceImpl
var GhostService: GhostServiceImpl
var RemoteConfigService: RemoteConfigServiceImpl
var BillingService: BillingServiceImpl
var SaveService: SaveServiceImpl

func _initialize() -> void:
	await get_tree().process_frame # let every autoload finish _ready()
	AppState = get_tree().root.get_node("AppState")
	AudioService = get_tree().root.get_node("AudioService")
	BackendService = get_tree().root.get_node("BackendService")
	EconomyService = get_tree().root.get_node("EconomyService")
	GameModeService = get_tree().root.get_node("GameModeService")
	GhostService = get_tree().root.get_node("GhostService")
	RemoteConfigService = get_tree().root.get_node("RemoteConfigService")
	BillingService = get_tree().root.get_node("BillingService")
	SaveService = get_tree().root.get_node("SaveService")
	_test_project_files()
	_test_content_counts()
	_test_deterministic_registry()
	_test_save_roundtrip_and_coercion()
	_test_stable_hash()
	_test_mode_contracts()
	_test_obstacle_catalog()
	_test_planner_determinism_and_fairness()
	_test_track_tiling()
	_test_power_cooldown()
	_test_flow_stages()
	_test_ghost_interpolation()
	_test_asset_pack()
	_test_audio_pack()
	_test_version_metadata()
	_test_services_contracts()
	print("NEXALANE QA HARNESS  (%d checks)" % checks)
	if failures.is_empty():
		print("PASS: all checks")
		get_tree().quit(0)
	else:
		for failure in failures:
			push_error(failure)
			print("FAIL: ", failure)
		get_tree().quit(1)

func check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)

# ---------------------------------------------------------------- project / content
func _test_project_files() -> void:
	for path in ["res://project.godot", "res://export_presets.cfg", "res://ui/Main.tscn", "res://ui/main.gd", "res://ui/hud.gd", "res://gameplay/runner/runner_controller.gd", "res://world/chunks/track_manager.gd", "res://world/chunks/track_planner.gd"]:
		check(FileAccess.file_exists(path), "Missing required project file: %s" % path)

func _test_content_counts() -> void:
	check(RunnerCatalog.all().size() == 16, "Runner catalog count != 16")
	check(ContentRegistry.districts().size() == 8, "District count != 8")
	check(ContentRegistry.obstacle_families().size() == 60, "Obstacle family count != 60")
	check(ContentRegistry.cosmetics().size() == 24, "Cosmetic count != 24")
	check(ContentRegistry.boards().size() == 12, "Board count != 12")
	check(ContentRegistry.trails().size() == 24, "Trail count != 24")
	check(ContentRegistry.badges().size() == 36, "Badge count != 36")
	check(ContentRegistry.challenges().size() == 40, "Challenge count != 40")
	check(ContentRegistry.achievements().size() == 60, "Achievement count != 60")
	check(ContentRegistry.event_themes().size() == 12, "Event theme count != 12")
	check(ContentRegistry.story().size() == 12, "Story chapter count != 12")
	check(ContentRegistry.event_shop().size() == 6, "Event shop count != 6")
	for item in ContentRegistry.cosmetics():
		if item["currency"] == "nova":
			check(int(item["cost"]) <= 600, "Nova outfit %s costs %d nova (priced like credits?)" % [item["id"], int(item["cost"])])

func _test_deterministic_registry() -> void:
	var a := ChunkRegistry.build(40)
	var b := ChunkRegistry.build(40)
	check(a.size() == b.size(), "Chunk registry build size is unstable")
	for i in a.size():
		if a[i].chunk_id != b[i].chunk_id or a[i].length != b[i].length:
			failures.append("Chunk registry mismatch at %d" % i)
			break

# ---------------------------------------------------------------- save
func _test_save_roundtrip_and_coercion() -> void:
	var original := SaveService.default_save()
	original["currencies"]["credits"] = 777
	original["profile"]["level"] = 9
	original["profile"]["xp"] = 4321
	original["daily"]["best_score"] = 12345
	original["season"]["claimed"] = [1, 2, 3]
	var text := JSON.stringify(original)
	var parsed: Variant = JSON.parse_string(text)
	check(typeof(parsed) == TYPE_DICTIONARY, "Save JSON does not parse")
	var migrated: Dictionary = SaveService._migrate(parsed)
	check(typeof(migrated["currencies"]["credits"]) == TYPE_INT and int(migrated["currencies"]["credits"]) == 777, "Credits lost/changed type across a save round-trip")
	check(typeof(migrated["profile"]["level"]) == TYPE_INT and int(migrated["profile"]["level"]) == 9, "Level lost across a save round-trip (JSON floats must be coerced)")
	check(int(migrated["profile"]["xp"]) == 4321, "XP lost across a save round-trip")
	check(int(migrated["daily"]["best_score"]) == 12345, "Daily best score lost across a save round-trip")
	check(typeof(migrated["season"]["claimed"][0]) == TYPE_INT, "Season claimed tiers are not ints")
	check(SaveServiceImpl._coerce(5.0, 0) == 5 and typeof(SaveServiceImpl._coerce(5.0, 0)) == TYPE_INT, "_coerce float->int failed")
	check(typeof(SaveServiceImpl._coerce("x", 0)) == TYPE_INT, "_coerce must fall back to the default for mismatched types")
	var broken := {"currencies": "oops", "profile": {"level": "high"}}
	var repaired: Dictionary = SaveService._migrate(broken)
	check(typeof(repaired["currencies"]) == TYPE_DICTIONARY and int(repaired["profile"]["level"]) == 1, "Corrupted sections must be repaired from defaults")

func _test_stable_hash() -> void:
	check(GameModeServiceImpl.stable_hash("") == 2166136261, "FNV-1a of empty string")
	check(GameModeServiceImpl.stable_hash("a") == 0xE40C292C, "FNV-1a('a') must be 0xE40C292C")
	check(GameModeServiceImpl.stable_hash("foobar") == 0xBF9CF968, "FNV-1a('foobar') must be 0xBF9CF968")

func _test_mode_contracts() -> void:
	for mode in ["ENDLESS", "STORY", "DAILY", "WEEKLY", "EVENT", "TRAINING", "GHOST", "CHALLENGE"]:
		GameModeService.set_mode(mode)
		check(GameModeService.mode_enum() != AppStateService.GameMode.MENU, "Mode %s maps to MENU" % mode)
		if mode != "ENDLESS":
			check(GameModeService.mode_enum() != AppStateService.GameMode.ENDLESS, "Mode enum fallback for %s" % mode)
		var objective := GameModeService.objective()
		check(objective.has("kind") and objective.has("target"), "Missing objective for mode %s" % mode)
		check(GameModeService.seed_for_selected_mode() > 0, "Seed for %s must be positive" % mode)
	GameModeService.set_mode("DAILY")
	check(GameModeService.seed_for_selected_mode() == GameModeService.seed_for_selected_mode(), "Daily seed is not stable")
	GameModeService.set_mode("ENDLESS")

# ---------------------------------------------------------------- obstacles / planner / track
func _test_obstacle_catalog() -> void:
	var apex := RunnerController.JUMP_VELOCITY * RunnerController.JUMP_VELOCITY / (2.0 * RunnerController.GRAVITY)
	check(apex > 1.9, "Jump apex %.2f m is too low for the tallest JUMP obstacle" % apex)
	for family in ObstacleCatalog.FAMILY_ORDER:
		var def := ObstacleCatalog.definition(family)
		var size: Vector3 = def["size"]
		var y := float(def["y"])
		check(FileAccess.file_exists("res://assets/models/%s.glb" % def["model"]), "Missing obstacle model for %s" % family)
		match int(def["kind"]):
			ObstacleCatalog.Kind.JUMP:
				check(y + size.y <= 1.15, "%s is JUMP but %.2f m tall" % [family, y + size.y])
			ObstacleCatalog.Kind.SLIDE:
				check(y > RunnerController.SLIDE_HEIGHT + 0.05 and y < RunnerController.RUNNER_HEIGHT, "%s SLIDE clearance %.2f m is not between slide and stand height" % [family, y])
			ObstacleCatalog.Kind.DODGE:
				check(size.y >= 1.4 or size.z >= 3.0, "%s is DODGE but small enough to jump" % family)
	for obstacle_id in ContentRegistry.obstacle_families():
		check(ObstacleCatalog.FAMILIES.has(ObstacleCatalog.family_of(obstacle_id)), "Obstacle id %s has no catalog family" % obstacle_id)
	check(ObstacleCatalog.obstacle_id("wet_bridge", 0) == "wet_bridge_13", "obstacle_id numbering")

func _plan_signature(seed_value: int, chunks: int, district: String) -> String:
	var random := RandomNumberGenerator.new()
	random.seed = seed_value
	var planner := TrackPlanner.new()
	var start := 0.0
	var parts: PackedStringArray = []
	for i in chunks:
		var d := float(i) / float(chunks)
		var length := 42.0 + float((i * 7) % 13)
		parts.append(JSON.stringify(planner.plan_chunk(random, district, start, length, d, 18.0 + d * 12.0, 9)))
		start += length
	return "|".join(parts)

func _test_planner_determinism_and_fairness() -> void:
	for seed_value in [1, 7, 42, 1337, 987654, 20260101]:
		check(_plan_signature(seed_value, 24, "transit_core") == _plan_signature(seed_value, 24, "transit_core"), "Planner not deterministic for seed %d" % seed_value)
	check(_plan_signature(1, 24, "transit_core") != _plan_signature(2, 24, "transit_core"), "Different seeds produced identical tracks")
	for seed_value in range(1, 41):
		var random := RandomNumberGenerator.new()
		random.seed = seed_value
		var planner := TrackPlanner.new()
		var start := 0.0
		var prev_end := -1000.0
		var prev_vertical := false
		for i in 30:
			var d := clampf(float(i) / 30.0, 0.0, 1.0)
			var speed := 18.0 + d * 12.0
			var length := 42.0 + float((i * 7) % 13)
			var plan := planner.plan_chunk(random, "harbor_arc", start, length, d, speed, 9)
			var groups := {}
			for o in plan["obstacles"]:
				var z := float(o["z"])
				check(z - float(o["depth"]) * 0.5 >= -0.01 and z + float(o["depth"]) * 0.5 <= length + 0.01, "Seed %d chunk %d: obstacle outside the chunk" % [seed_value, i])
				check(int(o["lane"]) >= 0 and int(o["lane"]) <= 2, "Lane out of range")
				var key := snappedf(z, 0.01)
				if not groups.has(key):
					groups[key] = []
				groups[key].append(o)
			var keys: Array = groups.keys()
			keys.sort()
			for key in keys:
				var group: Array = groups[key]
				var depth := 0.0
				var vertical := false
				var lanes := {}
				for o in group:
					depth = maxf(depth, float(o["depth"]))
					vertical = vertical or int(o["kind"]) != ObstacleCatalog.Kind.DODGE
					check(not lanes.has(int(o["lane"])), "Two obstacles share a lane in one slot")
					lanes[int(o["lane"])] = true
				var start_abs := start + float(key) - depth * 0.5
				var gap := start_abs - prev_end
				check(gap >= 7.9, "Seed %d chunk %d: gap %.1f m between slots is below the minimum" % [seed_value, i, gap])
				if vertical and prev_vertical:
					check(gap >= speed * TrackPlanner.AIR_TIME - 0.5, "Seed %d chunk %d: jump/slide slots only %.1f m apart (need %.1f)" % [seed_value, i, gap, speed * TrackPlanner.AIR_TIME])
				prev_end = start + float(key) + depth * 0.5
				prev_vertical = vertical
			start += length

func _test_track_tiling() -> void:
	var runner := RunnerController.new()
	var track := TrackManager.new()
	get_tree().root.add_child(track)
	get_tree().root.add_child(runner)
	runner.position = Vector3(0.0, 0.05, TrackManager.RUN_START_Z)
	track.setup(runner, 4242)
	check(track.active_chunk_count() == TrackManager.INITIAL_CHUNKS, "Track did not spawn the initial chunks")
	var expected_start := 0.0
	for chunk in track.active_chunks:
		check(is_equal_approx(chunk.position.z, expected_start), "Chunk %s starts at %.2f, expected %.2f (gap or overlap)" % [chunk.name, chunk.position.z, expected_start])
		expected_start = float(chunk.get_meta("end_z"))
	check(is_equal_approx(track.next_z, expected_start), "next_z does not continue the last chunk")
	var a := track.next_z
	track.setup(runner, 4242)
	check(is_equal_approx(track.next_z, a), "Re-running setup with the same seed changed the track length")
	track.queue_free()
	runner.queue_free()

# ---------------------------------------------------------------- gameplay systems
func _test_power_cooldown() -> void:
	var power := PowerSystem.new()
	check(power.activate("phase_shield"), "Power did not activate")
	check(not power.activate("phase_shield"), "Active power must not re-activate")
	power.tick(10.0)
	check(not power.active, "Power did not expire")
	check(not power.is_ready(), "Power has no cooldown (infinite shield)")
	check(not power.activate("phase_shield"), "Power activated during cooldown")
	power.tick(60.0)
	check(power.is_ready() and power.activate("phase_shield"), "Power did not recharge")
	power.free()

func _test_flow_stages() -> void:
	var flow := FlowSystem.new()
	flow.add_precision(0.7, "test")
	check(flow.stage == 3 and is_equal_approx(flow.multiplier, 2.0), "Flow 0.7 should be stage 3 (x2.0)")
	flow.break_flow("test")
	check(flow.stage == 0 and is_equal_approx(flow.multiplier, 1.0), "Flow break should return to stage 0")
	flow.free()

func _test_ghost_interpolation() -> void:
	var samples := [{"t": 0.0, "x": 0.0, "y": 0.0, "z": 0.0}, {"t": 1.0, "x": 3.2, "y": 1.0, "z": 20.0}, {"t": 2.0, "x": 3.2, "y": 0.0, "z": 40.0}]
	var mid: Vector3 = GhostService.position_at_time(0.5, samples)
	check(is_equal_approx(mid.x, 1.6) and is_equal_approx(mid.z, 10.0), "Ghost time interpolation")
	var at_dist: Vector3 = GhostService.position_at_distance(30.0, samples)
	check(is_equal_approx(at_dist.z, 30.0) and is_equal_approx(at_dist.x, 3.2), "Ghost distance interpolation")
	check(is_equal_approx(GhostService.end_time(samples), 2.0), "Ghost end time")

# ---------------------------------------------------------------- assets / services
func _test_asset_pack() -> void:
	var required := [
		"res://assets/textures/env_asphalt_wet.png", "res://assets/textures/env_asphalt_wet_n.png", "res://assets/textures/env_asphalt_wet_r.png",
		"res://assets/textures/env_asphalt_dry.png", "res://assets/textures/env_asphalt_dry_n.png", "res://assets/textures/env_asphalt_dry_r.png",
		"res://assets/textures/env_facade_a.png", "res://assets/textures/env_facade_b.png", "res://assets/textures/env_facade_c.png", "res://assets/textures/env_facade_d.png",
		"res://assets/textures/env_skyline_near.png", "res://assets/textures/env_skyline_far.png",
		"res://assets/ui/icon_credit.png", "res://assets/ui/icon_nova.png", "res://assets/ui/icon_flow.png", "res://assets/ui/icon_shield.png", "res://assets/ui/ui_logo.png",
		"res://assets/vfx/vfx_glow.png", "res://assets/vfx/vfx_streak.png", "res://assets/vfx/vfx_light_pool.png",
		"res://assets/fonts/Poppins-Bold.ttf", "res://assets/fonts/Poppins-Medium.ttf",
		"res://assets/models/runner_base.glb", "res://assets/models/collectible_coin.glb", "res://assets/models/street_light.glb",
		"res://assets/models/building_a.glb", "res://assets/models/building_b.glb", "res://assets/models/building_c.glb", "res://assets/models/building_d.glb"
	]
	for path in required:
		check(FileAccess.file_exists(path), "Missing production asset: %s" % path)
	for route in ["safe", "fast", "reward", "secret", "chaos"]:
		check(FileAccess.file_exists("res://assets/decals/route_%s.png" % route), "Missing route decal %s" % route)

func _test_audio_pack() -> void:
	for id in AudioService.CLIPS.keys():
		check(FileAccess.file_exists(str(AudioService.CLIPS[id])), "Missing SFX file for '%s'" % id)
	for id in AudioService.MUSIC.keys():
		check(FileAccess.file_exists(str(AudioService.MUSIC[id])), "Missing music file for '%s'" % id)
	for id in AudioService.MUSIC_LAYERS.keys():
		check(FileAccess.file_exists(str(AudioService.MUSIC_LAYERS[id])), "Missing intensity layer '%s'" % id)

func _test_version_metadata() -> void:
	var project_text := FileAccess.get_file_as_string("res://project.godot")
	check(project_text.contains('product_version="%s"' % AppState.PRODUCT_VERSION), "project.godot product_version != AppState.PRODUCT_VERSION")
	check(project_text.contains('content_version="%s"' % AppState.CONTENT_VERSION), "project.godot content_version != AppState.CONTENT_VERSION")
	check(project_text.contains('tuning_version="%d"' % AppState.TUNING_VERSION), "project.godot tuning_version != AppState.TUNING_VERSION")
	check(project_text.contains("window/handheld/orientation=1"), "Portrait orientation is not set (Android would launch in landscape)")
	check(project_text.contains("config/quit_on_go_back=false"), "Android back button would quit the game mid-run")
	check(project_text.contains("import_etc2_astc=true"), "ETC2/ASTC import disabled: Android export would fail")

func _test_services_contracts() -> void:
	check(EconomyService.balance("credits") >= 0, "Economy balance contract")
	var before := EconomyService.balance("credits")
	EconomyService.grant("credits", 10, "qa")
	check(EconomyService.balance("credits") == before + 10, "Economy grant")
	EconomyService.grant("credits", -10, "qa_revert")
	check(BackendService.validate_run(12345, 1000, 500.0, AppState.CONTENT_VERSION, "12345:1000:500:%s" % AppState.CONTENT_VERSION), "Valid run was rejected")
	check(not BackendService.validate_run(12345, 999999, 100.0, AppState.CONTENT_VERSION, "12345:999999:100:%s" % AppState.CONTENT_VERSION), "Impossible score accepted")
	check(RemoteConfigService.get_number("max_speed", 0.0) >= RemoteConfigService.get_number("base_speed", 99.0), "max_speed < base_speed")
	for product_id in BillingService.PRODUCTS.keys():
		check(BillingService.PRODUCTS[product_id].has("type"), "Product %s has no type" % product_id)
