extends Node3D
class_name TrackManager

## Streams the endless track: ground, deterministic obstacles/collectibles (TrackPlanner), scenery (PropLibrary).
## Chunk nodes are positioned at their START (z = start of the chunk) and all content is placed in chunk-local
## coordinates 0..length, so consecutive chunks tile exactly with no gaps or overlaps.

signal district_changed(district_name: String)
signal route_fork(route_options: Array[String])
signal route_selected(route_class: String)

const LANE_X := [-3.2, 0.0, 3.2]
const ROAD_WIDTH := 18.0
const GROUND_COLLIDER_WIDTH := 14.0
const CHUNKS_PER_DISTRICT := 7
const FORK_PHASE := 4                       # fork chunks are 4, 10, 16 ...
const FORK_EVERY := 6
const INITIAL_CHUNKS := 6
const RUN_START_Z := 4.0                    # where Main puts the runner; distance 0 is here

var registry: Array[TrackChunkDefinition] = []
var rng := RandomNumberGenerator.new()
var decor_rng := RandomNumberGenerator.new()
var planner := TrackPlanner.new()
var runner: RunnerController
var active_chunks: Array[Node3D] = []
var next_z := 0.0
var spawned_count := 0
var current_seed := 0
var pool_root: Node3D

var _obstacle_pool: Dictionary = {}          # family -> Array[StaticBody3D]
var _coin_pool: Array[Area3D] = []
var _coin_visuals: Array[Node3D] = []
var _district_marks: Array[Dictionary] = []
var _fork_count := 0
var _coin_spin := 0.0

func _ready() -> void:
	add_to_group("track")

func setup(player: RunnerController, run_seed: int) -> void:
	runner = player
	current_seed = run_seed
	rng.seed = run_seed
	registry = ChunkRegistry.build()
	_clear_chunks()
	if pool_root == null or not is_instance_valid(pool_root):
		pool_root = Node3D.new()
		pool_root.name = "ObjectPool"
		add_child(pool_root)
	next_z = 0.0
	spawned_count = 0
	_fork_count = 0
	_district_marks.clear()
	planner.reset(TrackPlanner.START_GRACE)
	for i in INITIAL_CHUNKS:
		_spawn_chunk()

func _process(delta: float) -> void:
	if runner == null or registry.is_empty():
		return
	var ahead := RemoteConfigService.get_number("spawn_ahead", 260.0)
	if DeviceProfileService.profile == "LOW":
		ahead = minf(ahead, 200.0)
	if next_z - runner.global_position.z < ahead:
		_spawn_chunk()                                          # at most one per frame keeps frame times even
	var keep_z := runner.global_position.z - RemoteConfigService.get_number("despawn_behind", 60.0)
	while not active_chunks.is_empty() and float(active_chunks[0].get_meta("end_z")) < keep_z:
		var old: Node3D = active_chunks.pop_front()
		_recycle_chunk(old)
	while not _district_marks.is_empty() and runner.global_position.z >= float(_district_marks[0]["z"]):
		var mark: Dictionary = _district_marks.pop_front()
		district_changed.emit(str(mark["name"]))
	_coin_spin += delta * 3.2
	for visual in _coin_visuals:
		visual.rotation.y = _coin_spin

# ---------------------------------------------------------------- chunk construction
func _difficulty_for(z: float) -> float:
	var d := RunDirector.difficulty_at(maxf(0.0, z - RUN_START_Z))
	if AppState.mode == AppState.GameMode.EVENT:
		d += EventEngine.difficulty_bonus()
	if AppState.mode == AppState.GameMode.TRAINING:
		d *= 0.5
	return clampf(d, 0.0, 1.0)

func _pick_definition(district_id: String, difficulty: float) -> TrackChunkDefinition:
	var candidates: Array[TrackChunkDefinition] = []
	for c in registry:
		if c.district_id == district_id and c.compatible(difficulty):
			candidates.append(c)
	if candidates.is_empty():
		for c in registry:
			if c.district_id == district_id:
				candidates.append(c)
	return candidates[rng.randi_range(0, candidates.size() - 1)]

func _fork_options() -> Array[String]:
	var options: Array[String] = []
	if _fork_count % 2 == 0:
		options.append_array(["SAFE", "REWARD", "FAST"])
	else:
		options.append_array(["SECRET", "FAST", "CHAOS"])
	_fork_count += 1
	for i in range(options.size() - 1, 0, -1):          # Fisher-Yates with the gameplay RNG (deterministic)
		var j := rng.randi_range(0, i)
		var tmp := options[i]
		options[i] = options[j]
		options[j] = tmp
	return options

func _spawn_chunk() -> void:
	var index := spawned_count
	var districts := ContentRegistry.districts()
	var district: Dictionary = districts[floori(float(index) / float(CHUNKS_PER_DISTRICT)) % districts.size()]
	var district_id := str(district["id"])
	var difficulty := _difficulty_for(next_z)
	var def := _pick_definition(district_id, difficulty)
	var length := def.length
	var speed := RunDirector.speed_at(maxf(0.0, next_z - RUN_START_Z))
	var is_fork := index >= FORK_PHASE and (index - FORK_PHASE) % FORK_EVERY == 0
	var root := Node3D.new()
	root.name = "Chunk_%03d" % index
	root.position = Vector3(0.0, 0.0, next_z)
	add_child(root)
	_build_ground(root, length, district)
	var plan: Dictionary
	var options: Array[String] = []
	if is_fork:
		options = _fork_options()
		plan = planner.plan_fork(rng, options, next_z, length, speed)
	else:
		plan = planner.plan_chunk(rng, district_id, next_z, length, difficulty, speed, def.collectible_count)
	_place_obstacles(root, plan["obstacles"])
	_place_coins(root, plan["coins"])
	_place_boosts(root, plan["boosts"])
	if is_fork:
		_build_fork_gate(root, options)
		route_fork.emit(options)
	elif index % CHUNKS_PER_DISTRICT == 0 and index > 0:
		_build_district_gate(root)
	decor_rng.seed = current_seed * 1000003 + index          # scenery RNG is isolated from gameplay RNG
	PropLibrary.decorate(root, district, length, decor_rng, DeviceProfileService.prop_density, index)
	root.set_meta("end_z", next_z + length)
	active_chunks.append(root)
	if index % CHUNKS_PER_DISTRICT == 0:
		_district_marks.append({"z": next_z, "name": str(district["name"])})
	next_z += length
	spawned_count += 1

func _build_ground(parent: Node3D, length: float, district: Dictionary) -> void:
	var weather := str(district["weather"])
	var wet := weather in ["rain", "storm", "mist", "steam"]
	var body := StaticBody3D.new()
	body.name = "Ground"
	body.collision_layer = 2
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(GROUND_COLLIDER_WIDTH, 0.5, length + 1.0)      # 1 m overlap: no seams for the character body to catch on
	shape.shape = box
	shape.position = Vector3(0.0, -0.25, length * 0.5)
	body.add_child(shape)
	var mesh := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(ROAD_WIDTH, length)
	mesh.mesh = plane
	mesh.position = Vector3(0.0, 0.0, length * 0.5)
	mesh.material_override = MaterialLibrary.ground(wet, length, district["accent"])
	mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	body.add_child(mesh)
	parent.add_child(body)

# ---------------------------------------------------------------- obstacles
func _create_obstacle(family: String) -> StaticBody3D:
	var def := ObstacleCatalog.definition(family)
	var size: Vector3 = def["size"]
	var body := StaticBody3D.new()
	body.collision_layer = 2
	body.collision_mask = 0
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	shape.shape = box
	shape.position = Vector3(0.0, float(def["y"]) + size.y * 0.5, 0.0)
	body.add_child(shape)
	var visual := ModelLibrary.instantiate(str(def["model"]), true)
	if visual != null:
		ModelLibrary.set_visibility_range(visual, 240.0)
		body.add_child(visual)
	body.set_meta("pool_type", "obstacle")
	body.set_meta("pool_family", family)
	body.add_to_group("obstacles")
	return body

func _acquire_obstacle(family: String) -> StaticBody3D:
	var pool: Array = _obstacle_pool.get(family, [])
	var body: StaticBody3D = null
	while not pool.is_empty() and body == null:
		var candidate: StaticBody3D = pool.pop_back()
		if is_instance_valid(candidate):
			body = candidate
	_obstacle_pool[family] = pool
	if body == null:
		body = _create_obstacle(family)
	body.visible = true
	body.scale = Vector3.ONE
	body.collision_layer = 2
	return body

func _place_obstacles(parent: Node3D, items: Array[Dictionary]) -> void:
	for item in items:
		var family := str(item["family"])
		var body := _acquire_obstacle(family)
		if body.get_parent() != null:
			body.get_parent().remove_child(body)
		body.position = Vector3(LANE_X[int(item["lane"])], 0.0, float(item["z"]))
		body.set_meta("obstacle_id", str(item["id"]))
		body.set_meta("obstacle_kind", int(item["kind"]))
		body.set_meta("obstacle_depth", float(item["depth"]))
		body.set_meta("near_missed", false)
		parent.add_child(body)

## Used by revive: removes every obstacle between two world z positions so the player is never respawned on top of one.
func clear_obstacles_in_range(z_from: float, z_to: float) -> void:
	for node in get_tree().get_nodes_in_group("obstacles"):
		var body := node as StaticBody3D
		if body == null or not body.visible:
			continue
		if body.global_position.z >= z_from and body.global_position.z <= z_to:
			body.set_deferred("collision_layer", 0)
			body.visible = false

# ---------------------------------------------------------------- collectibles
func _create_coin() -> Area3D:
	var area := Area3D.new()
	area.collision_layer = 4
	area.collision_mask = 1
	var shape := CollisionShape3D.new()
	var sphere := SphereShape3D.new()
	sphere.radius = 0.62
	shape.shape = sphere
	area.add_child(shape)
	var visual := ModelLibrary.instantiate("collectible_coin", false)
	if visual != null:
		visual.name = "CoinVisual"
		ModelLibrary.set_visibility_range(visual, 150.0)
		area.add_child(visual)
		_coin_visuals.append(visual)
	area.body_entered.connect(_on_coin_body_entered.bind(area))
	area.set_meta("pool_type", "coin")
	return area

func _acquire_coin() -> Area3D:
	var area: Area3D = null
	while not _coin_pool.is_empty() and area == null:
		var candidate: Area3D = _coin_pool.pop_back()
		if is_instance_valid(candidate):
			area = candidate
	if area == null:
		area = _create_coin()
	area.visible = true
	area.collision_layer = 4
	area.set_deferred("monitoring", true)
	area.set_deferred("monitorable", true)
	area.set_meta("collected", false)
	return area

func _place_coins(parent: Node3D, coins: Array[Dictionary]) -> void:
	for c in coins:
		var area := _acquire_coin()
		if area.get_parent() != null:
			area.get_parent().remove_child(area)
		area.position = Vector3(float(c["x"]), float(c["y"]), float(c["z"]))
		area.set_meta("collectible_value", int(c["value"]))
		parent.add_child(area)

func _on_coin_body_entered(body: Node3D, area: Area3D) -> void:
	if body != runner or bool(area.get_meta("collected", false)):
		return
	area.set_meta("collected", true)
	runner.collect(int(area.get_meta("collectible_value", 10)))
	area.visible = false
	area.set_deferred("monitoring", false)
	area.set_deferred("monitorable", false)

func _place_boosts(parent: Node3D, boosts: Array[Dictionary]) -> void:
	for b in boosts:
		var area := Area3D.new()
		area.collision_layer = 0
		area.collision_mask = 1
		area.position = Vector3(LANE_X[int(b["lane"])], 0.4, float(b["z"]))
		var shape := CollisionShape3D.new()
		var box := BoxShape3D.new()
		box.size = Vector3(2.6, 0.9, 5.6)
		shape.shape = box
		area.add_child(shape)
		var pad := ModelLibrary.instantiate("prop_boost_pad", false)
		if pad != null:
			pad.position.y = -0.4
			area.add_child(pad)
		area.body_entered.connect(_on_boost_body_entered)
		parent.add_child(area)

# ---------------------------------------------------------------- gates
func _build_district_gate(parent: Node3D) -> void:
	var arch := ModelLibrary.instantiate("prop_arch", false)
	if arch != null:
		arch.position = Vector3(0.0, 0.0, 3.0)
		ModelLibrary.set_visibility_range(arch, 230.0)
		parent.add_child(arch)

func _build_fork_gate(parent: Node3D, options: Array[String]) -> void:
	var arch := ModelLibrary.instantiate("prop_arch", false)
	if arch != null:
		arch.position = Vector3(0.0, 0.0, 6.0)
		parent.add_child(arch)
	for lane in 3:
		var sign := MeshInstance3D.new()
		var quad := QuadMesh.new()
		quad.size = Vector2(3.0, 1.5)
		sign.mesh = quad
		sign.position = Vector3(LANE_X[lane], 5.2, 5.55)
		sign.rotation.y = PI                                   # front face looks back at the player
		sign.material_override = MaterialLibrary.route_decal(options[lane])
		sign.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		parent.add_child(sign)
	var trigger := Area3D.new()
	trigger.collision_layer = 0
	trigger.collision_mask = 1
	trigger.position = Vector3(0.0, 2.0, 6.0)
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(12.0, 4.0, 1.2)
	shape.shape = box
	trigger.add_child(shape)
	trigger.set_meta("options", options)
	trigger.set_meta("fired", false)
	trigger.body_entered.connect(_on_fork_trigger.bind(trigger))
	parent.add_child(trigger)

func _on_boost_body_entered(body: Node3D) -> void:
	if body == runner:
		runner.apply_boost(2.2)

func _on_fork_trigger(body: Node3D, trigger: Area3D) -> void:
	if body != runner or bool(trigger.get_meta("fired", false)):
		return
	trigger.set_meta("fired", true)
	var options: Array = trigger.get_meta("options", [])
	if options.size() > runner.lane:
		route_selected.emit(str(options[runner.lane]))

# ---------------------------------------------------------------- recycling
func _clear_chunks() -> void:
	for chunk in active_chunks:
		if is_instance_valid(chunk):
			_recycle_chunk(chunk)
	active_chunks.clear()
	for child in get_children():
		if child != pool_root and child is Node3D and str(child.name).begins_with("Chunk_"):
			child.queue_free()

func _recycle_chunk(root: Node3D) -> void:
	for child in root.get_children():
		if not child.has_meta("pool_type"):
			continue
		root.remove_child(child)
		if str(child.get_meta("pool_type")) == "obstacle":
			var body := child as StaticBody3D
			body.collision_layer = 0
			body.visible = false
			var family := str(body.get_meta("pool_family"))
			var pool: Array = _obstacle_pool.get(family, [])
			pool.append(body)
			_obstacle_pool[family] = pool
			pool_root.add_child(body)
		else:
			var area := child as Area3D
			area.collision_layer = 0
			area.visible = false
			_coin_pool.append(area)
			pool_root.add_child(area)
	root.queue_free()

func active_chunk_count() -> int:
	return active_chunks.size()

func pooled_counts() -> Dictionary:
	var obstacles := 0
	for family in _obstacle_pool.keys():
		obstacles += (_obstacle_pool[family] as Array).size()
	return {"obstacles": obstacles, "coins": _coin_pool.size()}
