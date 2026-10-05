extends CharacterBody3D
class_name RunnerController

signal lane_changed(lane: int)
signal jumped
signal slid
signal landed
signal collided(obstacle_id: String)
signal collectible_collected(value: int)
signal near_miss
signal power_requested
signal power_consumed(power_id: String)

const LANE_X := [-3.2, 0.0, 3.2]
const GRAVITY := 30.0
const JUMP_VELOCITY := 10.8
const LANE_SPEED := 18.0
const RUNNER_HEIGHT := 1.85
const RUNNER_WIDTH := 0.80
const SLIDE_HEIGHT := 0.95
const SLIDE_TIME := 0.65
const COYOTE_TIME := 0.10
const JUMP_BUFFER_TIME := 0.14
const FAST_FALL_SPEED := 24.0
const SWIPE_THRESHOLD := 52.0              # viewport units (the UI design is 1080 wide)
const STARTING_SPEED_RAMP := 5.0           # m/s^2 towards the target speed

var lane := 1
var speed := 16.0
var max_speed := 31.0
var speed_bonus := 0.0                      # permanent bonus from runner role / modifiers
var lane_speed := LANE_SPEED
var jump_velocity := JUMP_VELOCITY
var jumping := false
var sliding := false
var slide_timer := 0.0
var slide_queued := false
var coyote_timer := 0.0
var jump_buffer := 0.0
var invulnerable_time := 0.0
var boost_time := 0.0
var active_power := "phase_shield"
var shielded := false
var power_remaining := 0.0
var power_speed_bonus := 0.0
var power_speed_multiplier := 1.0
var credit_multiplier := 1.0
var base_credit_multiplier := 1.0           # from challenge modifiers; powers layer on top of these
var base_speed_multiplier := 1.0
var route_scanner_active := false
var recovery_ready := false
var flow_stage := 0
var was_grounded := true
var run_active := false
var hold_idle := false                      # countdown: stand and breathe while the run is paused
var animation_time := 0.0

var visual_root: Node3D
var model: Node3D
var collider: CollisionShape3D
var shield_bubble: MeshInstance3D
var scanner_ring: MeshInstance3D
var flow_trail: MeshInstance3D
var magnet_area: Area3D
var slide_sparks: CPUParticles3D
var landing_puff: CPUParticles3D

var _hips: Node3D
var _torso: Node3D
var _leg_l: Node3D
var _leg_r: Node3D
var _shin_l: Node3D
var _shin_r: Node3D
var _arm_l: Node3D
var _arm_r: Node3D
var _forearm_l: Node3D
var _forearm_r: Node3D
var _hips_base_y := 0.94
var _rig_ready := false
var _skip_land_fx := true
var _phase := 0.0
var _pose_air := 0.0
var _pose_slide := 0.0
var _pending_clears: Array[Node3D] = []
var _touch_index := -1
var _mouse_down := false
var _swipe_origin := Vector2.ZERO
var _trail_material: StandardMaterial3D

func _ready() -> void:
	_ensure_input_actions()
	collision_layer = 1
	collision_mask = 2
	floor_snap_length = 0.3
	_add_collider()
	_add_body()
	_add_effects()
	refresh_appearance()
	add_to_group("runner")

# ---------------------------------------------------------------- setup
func _ensure_input_actions() -> void:
	var actions := {
		"runner_left": [KEY_A, KEY_LEFT],
		"runner_right": [KEY_D, KEY_RIGHT],
		"runner_jump": [KEY_W, KEY_UP, KEY_SPACE],
		"runner_slide": [KEY_S, KEY_DOWN],
		"runner_power": [KEY_E, KEY_F]
	}
	for action in actions.keys():
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for keycode in actions[action]:
			var exists := false
			for existing in InputMap.action_get_events(action):
				if existing is InputEventKey and (existing as InputEventKey).keycode == keycode:
					exists = true
					break
			if not exists:
				var event := InputEventKey.new()
				event.keycode = keycode
				InputMap.action_add_event(action, event)

func _add_collider() -> void:
	collider = CollisionShape3D.new()
	var shape := BoxShape3D.new()
	shape.size = Vector3(RUNNER_WIDTH, RUNNER_HEIGHT, RUNNER_WIDTH)
	collider.shape = shape
	collider.position.y = RUNNER_HEIGHT * 0.5
	add_child(collider)

func _add_body() -> void:
	visual_root = Node3D.new()
	visual_root.name = "Visual"
	add_child(visual_root)
	model = ModelLibrary.instantiate("runner_base", true)
	if model != null:
		model.name = "RunnerModel"
		visual_root.add_child(model)
		_hips = model.find_child("Hips", true, false) as Node3D
		_torso = model.find_child("Torso", true, false) as Node3D
		_leg_l = model.find_child("LegL", true, false) as Node3D
		_leg_r = model.find_child("LegR", true, false) as Node3D
		_shin_l = model.find_child("ShinL", true, false) as Node3D
		_shin_r = model.find_child("ShinR", true, false) as Node3D
		_arm_l = model.find_child("ArmL", true, false) as Node3D
		_arm_r = model.find_child("ArmR", true, false) as Node3D
		_forearm_l = model.find_child("ForearmL", true, false) as Node3D
		_forearm_r = model.find_child("ForearmR", true, false) as Node3D
		_rig_ready = _hips != null and _torso != null and _leg_l != null and _leg_r != null and _shin_l != null and _shin_r != null and _arm_l != null and _arm_r != null and _forearm_l != null and _forearm_r != null
		if _hips != null:
			_hips_base_y = _hips.position.y
	else:
		var fallback := MeshInstance3D.new()      # keeps the game playable if the model is missing
		var capsule := CapsuleMesh.new()
		capsule.radius = 0.4
		capsule.height = 1.7
		fallback.mesh = capsule
		fallback.position.y = 0.85
		visual_root.add_child(fallback)

func _add_effects() -> void:
	shield_bubble = MeshInstance3D.new()
	var bubble := SphereMesh.new()
	bubble.radius = 1.12
	bubble.height = 2.24
	bubble.radial_segments = 24
	bubble.rings = 12
	shield_bubble.mesh = bubble
	shield_bubble.position.y = 0.95
	var bubble_material := StandardMaterial3D.new()
	bubble_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	bubble_material.albedo_color = Color(0.2, 0.85, 1.0, 0.16)
	bubble_material.emission_enabled = true
	bubble_material.emission = Color(0.1, 0.7, 1.0)
	bubble_material.emission_energy_multiplier = 1.4
	bubble_material.rim_enabled = true
	bubble_material.rim = 1.0
	bubble_material.rim_tint = 0.2
	bubble_material.roughness = 0.1
	bubble_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	bubble_material.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	shield_bubble.material_override = bubble_material
	shield_bubble.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	shield_bubble.visible = false
	add_child(shield_bubble)

	scanner_ring = MeshInstance3D.new()
	var ring := TorusMesh.new()
	ring.inner_radius = 1.5
	ring.outer_radius = 1.62
	scanner_ring.mesh = ring
	scanner_ring.position.y = 0.06
	var ring_material := StandardMaterial3D.new()
	ring_material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	ring_material.albedo_color = Color(0.4, 1.0, 0.7)
	scanner_ring.material_override = ring_material
	scanner_ring.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	scanner_ring.visible = false
	add_child(scanner_ring)

	magnet_area = Area3D.new()
	magnet_area.name = "MagnetField"
	magnet_area.collision_layer = 0
	magnet_area.collision_mask = 4
	magnet_area.monitoring = false
	var magnet_shape := CollisionShape3D.new()
	var magnet_sphere := SphereShape3D.new()
	magnet_sphere.radius = 4.5
	magnet_shape.shape = magnet_sphere
	magnet_shape.position.y = 1.0
	magnet_area.add_child(magnet_shape)
	magnet_area.area_entered.connect(_on_magnet_area_entered)
	add_child(magnet_area)

	flow_trail = MeshInstance3D.new()
	var trail := PlaneMesh.new()
	trail.size = Vector2(4.4, 1.1)                  # x = length (rotated onto z), y = width
	flow_trail.mesh = trail
	flow_trail.rotation.y = -PI / 2.0                # local +x -> world +z (the bright end of the streak faces the runner)
	flow_trail.position = Vector3(0.0, 0.07, -2.4)
	_trail_material = MaterialLibrary.additive_sprite(Color(1.0, 0.45, 0.9, 0.9), "res://assets/vfx/vfx_streak.png", false)
	flow_trail.material_override = _trail_material
	flow_trail.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	flow_trail.visible = false
	add_child(flow_trail)

	var fill := OmniLight3D.new()
	fill.name = "RunnerLight"
	fill.light_color = Color(0.55, 0.85, 1.0)
	fill.light_energy = 0.9
	fill.omni_range = 9.0
	fill.position = Vector3(0.0, 2.6, -1.4)
	fill.shadow_enabled = false
	add_child(fill)

	slide_sparks = _make_burst(Color(1.0, 0.62, 0.2), 22, 0.35, false)
	slide_sparks.position = Vector3(0.0, 0.1, 0.2)
	add_child(slide_sparks)
	landing_puff = _make_burst(Color(0.75, 0.85, 1.0, 0.55), 14, 0.45, true)
	landing_puff.position = Vector3(0.0, 0.05, 0.0)
	add_child(landing_puff)

func _make_burst(color: Color, amount: int, life: float, one_shot: bool) -> CPUParticles3D:
	var p := CPUParticles3D.new()
	p.amount = DeviceProfileService.particle_count(amount)
	p.lifetime = life
	p.one_shot = one_shot
	p.explosiveness = 0.9 if one_shot else 0.0
	p.emitting = false
	p.direction = Vector3(0.0, 0.7, -1.0)
	p.spread = 35.0
	p.initial_velocity_min = 2.0
	p.initial_velocity_max = 5.0
	p.gravity = Vector3(0.0, -9.0, 0.0)
	p.local_coords = false
	var spark := BoxMesh.new()
	spark.size = Vector3(0.05, 0.05, 0.05)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.albedo_color = color
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA if color.a < 1.0 else BaseMaterial3D.TRANSPARENCY_DISABLED
	spark.material = m
	p.mesh = spark
	p.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return p

## Re-tints the runner's accent materials (runner colour, or the equipped outfit colour).
func refresh_appearance() -> void:
	if model == null:
		return
	var profile := RunnerCatalog.get_runner(AppState.selected_runner)
	var accent: Color = profile["color"]
	var outfit := ContentRegistry.cosmetic_by_id(ShopService.equipped())
	if not outfit.is_empty():
		accent = outfit["color"]
	_tint_accents(model, accent)

func _tint_accents(root: Node, accent: Color) -> void:
	for child in root.get_children():
		if child is MeshInstance3D:
			var mi := child as MeshInstance3D
			if mi.mesh != null:
				for i in mi.mesh.get_surface_count():
					var base := mi.mesh.surface_get_material(i) as StandardMaterial3D
					if base == null:
						continue
					if base.resource_name.begins_with("RunnerAccent"):
						var tinted := base.duplicate() as StandardMaterial3D
						tinted.albedo_color = accent
						mi.set_surface_override_material(i, tinted)
					elif base.resource_name.begins_with("RunnerGlow"):
						var glow := base.duplicate() as StandardMaterial3D
						glow.emission_enabled = true
						glow.emission = accent
						glow.emission_energy_multiplier = 2.4
						mi.set_surface_override_material(i, glow)
		_tint_accents(child, accent)

# ---------------------------------------------------------------- run lifecycle
func configure(run_speed: float) -> void:
	var profile := RunnerCatalog.get_runner(AppState.selected_runner)
	var role := str(profile["role"])
	max_speed = RemoteConfigService.get_number("max_speed", 31.0)
	speed_bonus = 0.0
	power_speed_bonus = 0.0
	base_speed_multiplier = 1.0
	base_credit_multiplier = 1.0
	route_scanner_active = false
	recovery_ready = false
	lane_speed = LANE_SPEED
	jump_velocity = JUMP_VELOCITY
	if GameModeService.selected_mode == "EVENT" and EventEngine.active_modifier == "Hyper Speed":
		speed_bonus += 4.0
		max_speed += 4.0
	match role:
		"Speed":
			speed_bonus += 1.3
			max_speed += 1.5
		"Precision":
			lane_speed += 4.0
		"Vault":
			jump_velocity += 1.0
		"Stamina":
			max_speed += 0.8
		"Flow":
			speed_bonus += 0.6
	if GameModeService.selected_mode == "CHALLENGE":
		var challenge := ChallengeService.current()
		match int(challenge.get("modifier", 0)):
			1:
				speed_bonus += 3.0
				max_speed += 3.0
			2:
				jump_velocity += 1.8
			3:
				base_speed_multiplier = 0.88
			4:
				base_credit_multiplier = 1.5
	power_speed_multiplier = base_speed_multiplier
	credit_multiplier = base_credit_multiplier
	speed = minf(run_speed + speed_bonus, max_speed)

## Speed the runner accelerates towards for the given director speed (role / modifier bonuses are permanent).
func target_speed(director_speed: float) -> float:
	return minf(director_speed + speed_bonus, max_speed)

func begin_run() -> void:
	run_active = true
	_skip_land_fx = true
	was_grounded = false
	velocity = Vector3.ZERO
	jumping = false
	slide_queued = false
	jump_buffer = 0.0
	coyote_timer = COYOTE_TIME
	invulnerable_time = 0.0
	boost_time = 0.0
	_pending_clears.clear()
	_set_slide(false)
	clear_power()
	set_flow_state(0.0, 0, 1.0)

func stop_run() -> void:
	run_active = false
	velocity = Vector3.ZERO
	_set_slide(false)
	clear_power()
	if slide_sparks:
		slide_sparks.emitting = false

func grant_invulnerability(seconds: float) -> void:
	invulnerable_time = maxf(invulnerable_time, seconds)

func apply_boost(seconds: float) -> void:
	boost_time = maxf(boost_time, seconds)
	AudioService.play_sfx("overdrive", 1.2)
	AccessibilityService.haptic("light")

# ---------------------------------------------------------------- physics
func _physics_process(delta: float) -> void:
	if not run_active or hold_idle:
		_idle_pose(delta)
		return
	if AppState.paused:
		return
	animation_time += delta
	invulnerable_time = maxf(0.0, invulnerable_time - delta)
	boost_time = maxf(0.0, boost_time - delta)
	jump_buffer = maxf(0.0, jump_buffer - delta)
	_handle_actions()
	var grounded := is_on_floor()
	if grounded:
		coyote_timer = COYOTE_TIME
		jumping = false
		if not was_grounded:
			_on_landed()
	else:
		coyote_timer = maxf(0.0, coyote_timer - delta)
	# Vertical motion first, THEN the jump impulse - setting the impulse before the "grounded" branch
	# would overwrite it with the floor-stick velocity and make jumping impossible.
	if grounded and velocity.y <= 0.0:
		velocity.y = -0.5
	else:
		velocity.y -= GRAVITY * delta
	if jump_buffer > 0.0 and coyote_timer > 0.0:
		_execute_jump()
	was_grounded = grounded
	var forward := speed * power_speed_multiplier + power_speed_bonus + (3.5 if boost_time > 0.0 else 0.0)
	velocity.z = maxf(0.1, forward)
	var target_x: float = LANE_X[lane]
	velocity.x = clampf((target_x - global_position.x) * lane_speed, -lane_speed * 1.1, lane_speed * 1.1)
	if sliding:
		slide_timer -= delta
		if slide_timer <= 0.0:
			_set_slide(false)
	move_and_slide()
	for i in get_slide_collision_count():
		var hit: Object = get_slide_collision(i).get_collider()
		if hit is Node and (hit as Node).has_meta("obstacle_id"):
			_collide(str((hit as Node).get_meta("obstacle_id")), hit as Node3D)
	_update_pending_clears()
	_animate_effects(delta)
	_animate_body(delta, grounded)
	if global_position.y < -4.0:
		collided.emit("fall")

func _handle_actions() -> void:
	if Input.is_action_just_pressed("runner_left"):
		move_lane(-1)
	if Input.is_action_just_pressed("runner_right"):
		move_lane(1)
	if Input.is_action_just_pressed("runner_jump"):
		request_jump()
	if Input.is_action_just_pressed("runner_slide"):
		request_slide()
	if Input.is_action_just_pressed("runner_power"):
		power_requested.emit()

func _on_landed() -> void:
	if _skip_land_fx:
		_skip_land_fx = false                       # the settle at the start line is not a real landing
	else:
		AudioService.play_sfx("land")
		landed.emit()
		if landing_puff:
			landing_puff.restart()
			landing_puff.emitting = true
	if slide_queued:
		slide_queued = false
		_begin_slide()

# ---------------------------------------------------------------- input
func _unhandled_input(event: InputEvent) -> void:
	if not run_active or AppState.paused:
		return
	if event is InputEventScreenTouch:
		var touch := event as InputEventScreenTouch
		if touch.pressed:
			if _touch_index == -1:
				_touch_index = touch.index
				_swipe_origin = touch.position
		elif touch.index == _touch_index:
			_touch_index = -1
	elif event is InputEventScreenDrag:
		var drag := event as InputEventScreenDrag
		if drag.index == _touch_index and _try_swipe(drag.position - _swipe_origin):
			_swipe_origin = drag.position
	elif event is InputEventMouseButton:
		var button := event as InputEventMouseButton
		if button.button_index == MOUSE_BUTTON_LEFT and button.device != InputEvent.DEVICE_ID_EMULATION:
			_mouse_down = button.pressed
			_swipe_origin = button.position
	elif event is InputEventMouseMotion:
		var motion := event as InputEventMouseMotion
		if _mouse_down and motion.device != InputEvent.DEVICE_ID_EMULATION and _try_swipe(motion.position - _swipe_origin):
			_swipe_origin = motion.position

## Fires as soon as the finger has travelled far enough (no need to lift it), so controls feel instant.
func _try_swipe(delta: Vector2) -> bool:
	if delta.length() < SWIPE_THRESHOLD:
		return false
	if absf(delta.x) > absf(delta.y):
		move_lane(-1 if delta.x < 0.0 else 1)
	elif delta.y < 0.0:
		request_jump()
	else:
		request_slide()
	return true

# ---------------------------------------------------------------- actions
func move_lane(direction: int) -> void:
	var old_lane := lane
	lane = clampi(lane + direction, 0, 2)
	if lane == old_lane:
		return
	lane_changed.emit(lane)
	AudioService.play_sfx("lane_change")
	AccessibilityService.haptic("light")
	if run_active and _threat_ahead(old_lane, -1, speed * 0.5) != null:
		near_miss.emit()
		AudioService.play_sfx("near_miss")

func request_jump() -> void:
	jump_buffer = JUMP_BUFFER_TIME
	slide_queued = false

func request_slide() -> void:
	if not is_on_floor() and not coyote_timer > 0.0:
		slide_queued = true                   # fast-fall, slide the moment we land
		velocity.y = minf(velocity.y, -FAST_FALL_SPEED)
		return
	if sliding:
		return
	_begin_slide()

func jump() -> void:                          # kept for callers that used the old API
	request_jump()

func slide() -> void:
	request_slide()

func _execute_jump() -> void:
	jump_buffer = 0.0
	coyote_timer = 0.0
	if sliding:
		_set_slide(false)
	velocity.y = jump_velocity
	jumping = true
	was_grounded = false
	jumped.emit()
	AudioService.play_sfx("jump")
	AccessibilityService.haptic("light")
	var threat := _threat_ahead(lane, ObstacleCatalog.Kind.JUMP, speed * 0.45)
	if threat != null and not _pending_clears.has(threat):
		_pending_clears.append(threat)

func _begin_slide() -> void:
	_set_slide(true)
	AudioService.play_sfx("slide")
	var threat := _threat_ahead(lane, ObstacleCatalog.Kind.SLIDE, speed * 0.38)
	if threat != null and not _pending_clears.has(threat):
		_pending_clears.append(threat)

func _set_slide(value: bool) -> void:
	sliding = value
	slide_timer = SLIDE_TIME if value else 0.0
	if collider != null and collider.shape is BoxShape3D:
		var shape := collider.shape as BoxShape3D
		shape.size.y = SLIDE_HEIGHT if value else RUNNER_HEIGHT
		collider.position.y = shape.size.y * 0.5
	if slide_sparks:
		slide_sparks.emitting = value and not AccessibilityService.is_enabled("reduced_flashes")
	if value:
		slid.emit()

# ---------------------------------------------------------------- near-miss bookkeeping
## Nearest live obstacle in a lane that is still ahead of us within `window` metres. kind_filter -1 = any kind.
func _threat_ahead(lane_index: int, kind_filter: int, window: float) -> Node3D:
	var lane_x: float = LANE_X[lane_index]
	var best: Node3D = null
	var best_dist := INF
	for node in get_tree().get_nodes_in_group("obstacles"):
		var obstacle := node as Node3D
		if obstacle == null or not obstacle.visible or bool(obstacle.get_meta("near_missed", false)):
			continue
		if kind_filter >= 0 and int(obstacle.get_meta("obstacle_kind", -1)) != kind_filter:
			continue
		if absf(obstacle.global_position.x - lane_x) > 1.7:
			continue
		var front := obstacle.global_position.z - float(obstacle.get_meta("obstacle_depth", 1.0)) * 0.5 - global_position.z
		if front >= 0.0 and front <= window and front < best_dist:
			best = obstacle
			best_dist = front
	if best != null and kind_filter < 0:
		best.set_meta("near_missed", true)
	return best

func _update_pending_clears() -> void:
	if _pending_clears.is_empty():
		return
	for i in range(_pending_clears.size() - 1, -1, -1):
		var obstacle := _pending_clears[i]
		if not is_instance_valid(obstacle):
			_pending_clears.remove_at(i)
			continue
		var back := obstacle.global_position.z + float(obstacle.get_meta("obstacle_depth", 1.0)) * 0.5
		if global_position.z > back + 0.4:
			_pending_clears.remove_at(i)
			if not bool(obstacle.get_meta("near_missed", false)):
				obstacle.set_meta("near_missed", true)
				near_miss.emit()
				AudioService.play_sfx("near_miss")

# ---------------------------------------------------------------- powers
func set_power_state(power_id: String, active: bool, remaining: float) -> void:
	active_power = power_id
	power_remaining = maxf(0.0, remaining)
	set_shield(active and power_id == "phase_shield")
	if not active:
		set_power_effect(power_id, false)

func set_power_effect(power_id: String, active: bool) -> void:
	power_speed_bonus = 0.0
	power_speed_multiplier = base_speed_multiplier
	credit_multiplier = base_credit_multiplier
	route_scanner_active = false
	recovery_ready = false
	if scanner_ring:
		scanner_ring.visible = false
	if magnet_area:
		magnet_area.set_deferred("monitoring", false)
	if not active:
		return
	match power_id:
		"magnet":
			if magnet_area:
				magnet_area.set_deferred("monitoring", true)
		"overdrive": power_speed_bonus = 7.0
		"time_warp": power_speed_multiplier = base_speed_multiplier * 0.78
		"route_scanner":
			route_scanner_active = true
			if scanner_ring:
				scanner_ring.visible = true
		"double_credits": credit_multiplier = base_credit_multiplier * 2.0
		"recovery_pulse": recovery_ready = true
		"flow_surge": power_speed_bonus = 2.5

func clear_power() -> void:
	set_power_state(active_power, false, 0.0)

func set_shield(active: bool) -> void:
	shielded = active
	if shield_bubble:
		shield_bubble.visible = active

func set_flow_state(_value: float, stage: int, _multiplier: float) -> void:
	flow_stage = stage
	if flow_trail:
		flow_trail.visible = stage >= 3
		_trail_material.albedo_color = Color(1.0, 0.45, 0.9, 0.9) if stage == 3 else Color(1.0, 0.7, 0.25, 1.0)

func collect(value: int) -> void:
	collectible_collected.emit(value)
	AudioService.play_sfx("pickup", 1.0 + float(flow_stage) * 0.04)

func _on_magnet_area_entered(area: Area3D) -> void:
	if area == null or not is_instance_valid(area) or not area.has_meta("collectible_value"):
		return
	if bool(area.get_meta("collected", false)):
		return
	area.set_meta("collected", true)
	area.set_deferred("monitorable", false)
	var value := int(area.get_meta("collectible_value", 10))
	var tween := create_tween()
	tween.tween_method(_pull_collectible.bind(area, area.global_position), 0.0, 1.0, 0.16)
	tween.tween_callback(_finish_pull.bind(area, value))

func _pull_collectible(t: float, area: Area3D, start: Vector3) -> void:
	if is_instance_valid(area):
		area.global_position = start.lerp(global_position + Vector3(0.0, 1.0, 0.0), t)

func _finish_pull(area: Area3D, value: int) -> void:
	collect(value)
	if is_instance_valid(area):
		area.visible = false

# ---------------------------------------------------------------- collisions
func _collide(obstacle_id: String, body: Node3D = null) -> void:
	if invulnerable_time > 0.0:
		if body != null:
			_shatter(body)                          # phase through anything touched while invulnerable
		return
	if shielded or recovery_ready:
		var used_power := active_power
		shielded = false
		recovery_ready = false
		set_shield(false)
		power_remaining = 0.0
		invulnerable_time = 1.2
		if body != null:
			_shatter(body)
		AudioService.play_sfx("shield_hit")
		AccessibilityService.haptic("medium")
		power_consumed.emit(used_power)
		near_miss.emit()
		return
	AudioService.play_sfx("collision")
	AccessibilityService.haptic("heavy")
	collided.emit(obstacle_id)

## The obstacle that absorbed a hit is removed, otherwise the runner would still be pushing against it
## and die on the very next physics frame.
func _shatter(body: Node3D) -> void:
	body.set_meta("near_missed", true)
	body.set_deferred("collision_layer", 0)
	var tween := create_tween()
	tween.tween_property(body, "scale", Vector3(0.05, 0.05, 0.05), 0.16)
	tween.tween_callback(_hide_node.bind(body))

func _hide_node(node: Node3D) -> void:
	if is_instance_valid(node):
		node.visible = false

# ---------------------------------------------------------------- animation
func _animate_effects(delta: float) -> void:
	if shield_bubble and shield_bubble.visible:
		shield_bubble.rotation.y += delta * 1.6
		var pulse := 1.0 + 0.03 * sin(animation_time * 9.0)
		shield_bubble.scale = Vector3.ONE * pulse
	if scanner_ring and scanner_ring.visible:
		scanner_ring.rotation.y += delta * 3.6
		scanner_ring.scale = Vector3.ONE * (1.0 + 0.08 * sin(animation_time * 8.0))
	if flow_trail and flow_trail.visible:
		flow_trail.scale.x = 0.9 + 0.18 * sin(animation_time * 14.0) + 0.12 * float(flow_stage - 3)
	if invulnerable_time > 0.0 and model != null:
		model.visible = int(animation_time * 18.0) % 2 == 0 or shielded       # blink while invulnerable
	elif model != null and not model.visible:
		model.visible = true

func _animate_body(delta: float, grounded: bool) -> void:
	if not _rig_ready:
		return
	_pose_air = move_toward(_pose_air, 0.0 if grounded else 1.0, delta * 9.0)
	_pose_slide = move_toward(_pose_slide, 1.0 if sliding else 0.0, delta * 10.0)
	var cadence := clampf(speed / 5.0, 2.4, 5.8)
	_phase = fposmod(_phase + delta * cadence * TAU, TAU)
	var s := sin(_phase)
	var knee_l := maxf(0.0, sin(_phase + 1.1)) * 1.3
	var knee_r := maxf(0.0, sin(_phase + 1.1 + PI)) * 1.3
	# rotation.x < 0 swings a limb hanging from its pivot forward (+z); > 0 swings it back.
	var thigh_l := lerpf(-s * 0.95, -0.9, _pose_air)
	var thigh_r := lerpf(s * 0.95, 0.35, _pose_air)
	var shin_l := lerpf(knee_l, 1.1, _pose_air)
	var shin_r := lerpf(knee_r, 0.5, _pose_air)
	var arm_l := lerpf(s * 0.85, -1.15, _pose_air)
	var arm_r := lerpf(-s * 0.85, 0.5, _pose_air)
	_leg_l.rotation.x = lerpf(thigh_l, -0.1, _pose_slide)
	_leg_r.rotation.x = lerpf(thigh_r, -0.1, _pose_slide)
	_shin_l.rotation.x = lerpf(shin_l, 0.15, _pose_slide)
	_shin_r.rotation.x = lerpf(shin_r, 0.15, _pose_slide)
	_arm_l.rotation.x = lerpf(arm_l, 0.9, _pose_slide)
	_arm_r.rotation.x = lerpf(arm_r, 0.9, _pose_slide)
	_forearm_l.rotation.x = lerpf(-1.1 - 0.25 * s, -0.5, _pose_slide)
	_forearm_r.rotation.x = lerpf(-1.1 + 0.25 * s, -0.5, _pose_slide)
	_torso.rotation.x = lerpf(0.16 + 0.03 * s, 0.1, _pose_slide)
	_hips.position.y = _hips_base_y + absf(s) * 0.05 * (1.0 - _pose_air) - _pose_slide * 0.36
	_hips.rotation.x = -_pose_slide * 1.15
	_hips.rotation.z = lerpf(_hips.rotation.z, clampf(-velocity.x * 0.02, -0.3, 0.3), minf(1.0, delta * 10.0))

func _idle_pose(delta: float) -> void:
	if not _rig_ready:
		return
	animation_time += delta
	var breathe := sin(animation_time * 1.7)
	_pose_air = move_toward(_pose_air, 0.0, delta * 6.0)
	_pose_slide = move_toward(_pose_slide, 0.0, delta * 6.0)
	_hips.position.y = _hips_base_y - 0.012 + 0.012 * breathe
	_hips.rotation = Vector3.ZERO
	_torso.rotation.x = 0.04 + 0.02 * breathe
	_leg_l.rotation.x = lerpf(_leg_l.rotation.x, 0.0, delta * 8.0)
	_leg_r.rotation.x = lerpf(_leg_r.rotation.x, 0.0, delta * 8.0)
	_shin_l.rotation.x = lerpf(_shin_l.rotation.x, 0.0, delta * 8.0)
	_shin_r.rotation.x = lerpf(_shin_r.rotation.x, 0.0, delta * 8.0)
	_arm_l.rotation.x = lerpf(_arm_l.rotation.x, 0.12, delta * 8.0)
	_arm_r.rotation.x = lerpf(_arm_r.rotation.x, 0.12, delta * 8.0)
	_forearm_l.rotation.x = lerpf(_forearm_l.rotation.x, -0.35, delta * 8.0)
	_forearm_r.rotation.x = lerpf(_forearm_r.rotation.x, -0.35, delta * 8.0)
