extends Node3D
class_name WorldEnvironmentController

## Sky, fog, lighting, bloom, far skyline and rain. Everything is created in code so the main scene stays tiny.
## Palettes come from ContentRegistry.districts() and are blended over 2.5 s whenever the runner enters a new district.

const TRANSITION_SECONDS := 2.5
const SKYLINE_NEAR_DISTANCE := 330.0
const SKYLINE_FAR_DISTANCE := 430.0

var environment: Environment
var world_env: WorldEnvironment
var sky_material: ProceduralSkyMaterial
var sun: DirectionalLight3D
var rain: GPUParticles3D
var rain_rig: Node3D
var skyline_rig: Node3D
var skyline_near: MeshInstance3D
var skyline_far: MeshInstance3D
var runner: Node3D
var current_district := ""
var time_variant := 0                      # 0 night, 1 blue hour, 2 late dusk
var _tween: Tween
var _storm := false
var _lightning_timer := 6.0
var _base_ambient := 0.9
var _base_sun := 0.9

func _ready() -> void:
	_build_environment()
	_build_sun()
	_build_skyline()
	_build_rain()
	DeviceProfileService.apply_to_viewport(get_viewport())
	DeviceProfileService.profile_changed.connect(_on_profile_changed)
	set_district("Old Quarter", true)

func setup(player: Node3D) -> void:
	runner = player

func _on_profile_changed(_profile: String) -> void:
	DeviceProfileService.apply_to_viewport(get_viewport())
	environment.glow_enabled = DeviceProfileService.glow_enabled
	sun.shadow_enabled = DeviceProfileService.shadows_enabled
	rain.amount = DeviceProfileService.particle_count(420)

# ---------------------------------------------------------------- construction
func _build_environment() -> void:
	environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	sky_material = ProceduralSkyMaterial.new()
	sky_material.sky_curve = 0.18
	sky_material.ground_curve = 0.06
	sky_material.sun_angle_max = 24.0
	sky_material.sun_curve = 0.2
	sky_material.use_debanding = true
	var sky := Sky.new()
	sky.sky_material = sky_material
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	environment.ambient_light_energy = _base_ambient
	environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.tonemap_exposure = 1.0
	environment.tonemap_white = 6.0
	environment.fog_enabled = true
	environment.fog_density = 0.011
	environment.fog_sky_affect = 0.3
	environment.glow_enabled = DeviceProfileService.glow_enabled
	environment.glow_intensity = 0.9
	environment.glow_strength = 1.0
	environment.glow_bloom = 0.06
	environment.glow_hdr_threshold = 1.0
	environment.glow_blend_mode = Environment.GLOW_BLEND_MODE_SCREEN
	environment.adjustment_enabled = true
	environment.adjustment_contrast = 1.06
	environment.adjustment_saturation = 1.1
	world_env = WorldEnvironment.new()
	world_env.name = "WorldEnvironment"
	world_env.environment = environment
	add_child(world_env)

func _build_sun() -> void:
	sun = DirectionalLight3D.new()
	sun.name = "Moonlight"
	sun.basis = Basis.looking_at(Vector3(0.35, -0.8, 0.5).normalized(), Vector3.UP)
	sun.light_energy = _base_sun
	sun.shadow_enabled = DeviceProfileService.shadows_enabled
	sun.directional_shadow_mode = DirectionalLight3D.SHADOW_PARALLEL_2_SPLITS
	sun.directional_shadow_max_distance = 60.0
	sun.shadow_blur = 1.4
	add_child(sun)

func _build_skyline() -> void:
	skyline_rig = Node3D.new()
	skyline_rig.name = "Skyline"
	add_child(skyline_rig)
	skyline_far = _skyline_plane("far", 1100.0, 275.0, SKYLINE_FAR_DISTANCE)
	skyline_near = _skyline_plane("near", 760.0, 190.0, SKYLINE_NEAR_DISTANCE)

func _skyline_plane(layer: String, width: float, height: float, distance: float) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(width, height)
	mi.mesh = quad
	mi.position = Vector3(0.0, height * 0.5 - 8.0, distance)
	mi.rotation.y = PI                          # front face looks back at the camera
	mi.material_override = MaterialLibrary.skyline(layer, Color(1.0, 1.0, 1.0, 1.0))
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	skyline_rig.add_child(mi)
	return mi

func _build_rain() -> void:
	rain_rig = Node3D.new()
	rain_rig.name = "RainRig"
	add_child(rain_rig)
	rain = GPUParticles3D.new()
	var process := ParticleProcessMaterial.new()
	process.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX
	process.emission_box_extents = Vector3(11.0, 0.5, 26.0)
	process.direction = Vector3(0.12, -1.0, 0.05)
	process.spread = 3.0
	process.initial_velocity_min = 22.0
	process.initial_velocity_max = 28.0
	process.gravity = Vector3(0.0, -10.0, 0.0)
	process.particle_flag_align_y = true
	rain.process_material = process
	var drop := BoxMesh.new()
	drop.size = Vector3(0.012, 0.5, 0.012)
	var drop_material := StandardMaterial3D.new()
	drop_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	drop_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	drop_material.albedo_color = Color(0.75, 0.86, 1.0, 0.32)
	drop.material = drop_material
	rain.draw_pass_1 = drop
	rain.amount = DeviceProfileService.particle_count(420)
	rain.lifetime = 0.7
	rain.preprocess = 0.7
	rain.local_coords = false
	rain.visibility_aabb = AABB(Vector3(-14.0, -14.0, -30.0), Vector3(28.0, 28.0, 60.0))
	rain.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	rain.emitting = false
	rain_rig.add_child(rain)

# ---------------------------------------------------------------- districts / time of day
func set_time_variant(run_seed: int) -> void:
	time_variant = absi(run_seed) % 3
	if current_district != "":
		set_district(current_district, true)

func set_district(district_name: String, immediate: bool = false) -> void:
	var d := ContentRegistry.district_by_name(district_name)
	current_district = str(d["name"])
	var weather := str(d["weather"])
	_storm = weather == "storm"
	rain.emitting = weather in ["rain", "storm"] and DeviceProfileService.particle_budget >= 100
	var palette := _palette_for(d)
	if _tween != null and _tween.is_valid():
		_tween.kill()
	if immediate:
		_apply_palette(palette)
		return
	_tween = create_tween()
	_tween.set_parallel(true)
	_tween.tween_property(environment, "fog_light_color", palette["fog_color"], TRANSITION_SECONDS)
	_tween.tween_property(environment, "fog_density", palette["fog"], TRANSITION_SECONDS)
	_tween.tween_property(sky_material, "sky_top_color", palette["sky_top"], TRANSITION_SECONDS)
	_tween.tween_property(sky_material, "sky_horizon_color", palette["sky_horizon"], TRANSITION_SECONDS)
	_tween.tween_property(sky_material, "ground_horizon_color", palette["fog_color"], TRANSITION_SECONDS)
	_tween.tween_property(sky_material, "ground_bottom_color", palette["ground"], TRANSITION_SECONDS)
	_tween.tween_property(sun, "light_color", palette["sun"], TRANSITION_SECONDS)
	_tween.tween_property(sun, "light_energy", palette["sun_energy"], TRANSITION_SECONDS)
	_tween.tween_property(environment, "ambient_light_energy", palette["ambient"], TRANSITION_SECONDS)
	_tween.tween_property(skyline_near.material_override, "albedo_color", palette["skyline_near"], TRANSITION_SECONDS)
	_tween.tween_property(skyline_far.material_override, "albedo_color", palette["skyline_far"], TRANSITION_SECONDS)
	_base_ambient = float(palette["ambient"])
	_base_sun = float(palette["sun_energy"])

func _palette_for(d: Dictionary) -> Dictionary:
	var sky_top: Color = d["sky_top"]
	var horizon: Color = d["sky_horizon"]
	var fog_color: Color = d["fog_color"]
	var sun_energy := float(d["sun_energy"])
	var ambient := 0.9
	match time_variant:
		1:    # blue hour: brighter, cooler sky
			sky_top = sky_top.lerp(Color(0.08, 0.16, 0.34), 0.45)
			ambient = 1.05
			sun_energy *= 1.1
		2:    # late dusk: warm horizon
			horizon = horizon.lerp(Color(0.95, 0.52, 0.26), 0.3)
			sun_energy *= 1.05
		_:
			ambient = 0.85
	return {
		"fog_color": fog_color, "fog": float(d["fog"]), "sky_top": sky_top, "sky_horizon": horizon,
		"ground": fog_color.darkened(0.45), "sun": d["sun"], "sun_energy": sun_energy, "ambient": ambient,
		"skyline_near": Color(0.80, 0.86, 1.0).lerp(horizon, 0.28), "skyline_far": Color(0.88, 0.92, 1.0).lerp(horizon, 0.42)
	}

func _apply_palette(p: Dictionary) -> void:
	environment.fog_light_color = p["fog_color"]
	environment.fog_density = p["fog"]
	sky_material.sky_top_color = p["sky_top"]
	sky_material.sky_horizon_color = p["sky_horizon"]
	sky_material.ground_horizon_color = p["fog_color"]
	sky_material.ground_bottom_color = p["ground"]
	sun.light_color = p["sun"]
	sun.light_energy = p["sun_energy"]
	environment.ambient_light_energy = p["ambient"]
	skyline_near.material_override.albedo_color = p["skyline_near"]
	skyline_far.material_override.albedo_color = p["skyline_far"]
	_base_ambient = float(p["ambient"])
	_base_sun = float(p["sun_energy"])

# ---------------------------------------------------------------- per frame
func _process(delta: float) -> void:
	if runner != null:
		var z := runner.global_position.z
		skyline_rig.position.z = z
		rain_rig.position = Vector3(runner.global_position.x, 13.0, z + 12.0)
	if _storm and AccessibilityService.flash_scale() > 0.0 and not AppState.paused:
		_lightning_timer -= delta
		if _lightning_timer <= 0.0:
			_lightning_timer = randf_range(4.0, 10.0)
			_flash_lightning()

func _flash_lightning() -> void:
	var flash := create_tween()
	flash.tween_property(environment, "ambient_light_energy", _base_ambient + 1.9, 0.05)
	flash.parallel().tween_property(sun, "light_energy", _base_sun * 2.4, 0.05)
	flash.tween_property(environment, "ambient_light_energy", _base_ambient + 0.5, 0.07)
	flash.tween_property(environment, "ambient_light_energy", _base_ambient + 1.5, 0.05)
	flash.tween_property(environment, "ambient_light_energy", _base_ambient, 0.35)
	flash.parallel().tween_property(sun, "light_energy", _base_sun, 0.35)
