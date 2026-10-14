extends Node3D
class_name ChunkLife

## Ambient "life" of one track chunk (0.6.0), so the street never feels like a static diorama:
##   * bunting strung across the street, every flag swaying in the wind
##   * a cheering crowd of little bean people on the pavements (bouncing, waving)
##   * pigeons that sit on the pavement and burst into the air when the runner gets close
##   * balloons bobbing between the buildings, steam venting from the street, a patrolling drone
##   * neon / lamp halos that breathe and flicker (flicker is replaced by a steady glow when "reduced flashes" is on)
## Everything is made from primitive meshes (no new assets) and batched with MultiMesh, so a chunk costs a handful of draw calls.
## PropLibrary.decorate() creates one ChunkLife per chunk; TrackManager feeds pulse_time / focus_z every frame.

static var pulse_time: float = 0.0            # seconds, advanced by TrackManager
static var focus_z: float = 0.0               # the runner's (interpolated) z, advanced by TrackManager
static var _shared: Dictionary = {}

const ACTIVE_AHEAD := 175.0                   # animate chunks up to this far ahead of the runner ...
const ACTIVE_BEHIND := 40.0                   # ... and this far behind
const ROAD_HALF := 9.4
const FLAG_COLORS: Array = [Color(1.0, 0.35, 0.55), Color(0.2, 0.85, 1.0), Color(1.0, 0.85, 0.25), Color(0.5, 1.0, 0.55), Color(0.72, 0.5, 1.0), Color(1.0, 0.55, 0.2), Color(0.96, 0.96, 1.0)]
const BEAN_COLORS: Array = [Color(0.2, 0.75, 0.95), Color(0.95, 0.38, 0.58), Color(0.95, 0.74, 0.2), Color(0.42, 0.9, 0.52), Color(0.66, 0.48, 0.95), Color(0.95, 0.52, 0.2), Color(0.9, 0.92, 1.0)]
const SKIN_TONES: Array = [Color(0.93, 0.68, 0.5), Color(0.78, 0.55, 0.38), Color(0.55, 0.37, 0.26), Color(0.4, 0.26, 0.18), Color(0.96, 0.78, 0.64)]

var chunk_len: float = 48.0
var _flick_amp: float = 0.55
var _tier: int = 2                  # 0 = LOW device, 1 = MID, 2 = HIGH: how much life one chunk gets
var _halos: Array = []        # {mat, base, phase, speed, neon}
var _bunting: Array = []      # {mm, xs, y, z, phase}
var _beans: Array = []        # {x, z, yaw, phase, left, right, hoodie, skin}
var _bean_mm: Dictionary = {}
var _birds: Array = []        # {x, z, fly, vx, vy, vz, pos, yaw, phase}
var _bird_mm: Dictionary = {}
var _balloons: Array = []     # {x, y, z, phase}
var _balloon_mm: MultiMesh = null
var _drones: Array = []       # {node, rotors, led, speed, y, phase}


# ---------------------------------------------------------------- entry points
static func populate(root: Node3D, district: Dictionary, length: float, random: RandomNumberGenerator, density: float, chunk_index: int) -> void:
	if density <= 0.0:
		return
	var life := ChunkLife.new()
	life.name = "Life"
	life.chunk_len = length
	life.physics_interpolation_mode = Node.PHYSICS_INTERPOLATION_MODE_OFF         # animated every rendered frame
	root.add_child(life)
	life._build(district, random, density, chunk_index)


## Windows breathe: the shared facade materials pulse slowly and out of step, so neighbouring buildings never glow in unison.
static func tick_global(t: float) -> void:
	var kinds: Array = ["a", "b", "c", "d"]
	for i in range(kinds.size()):
		var m: StandardMaterial3D = MaterialLibrary.facade(str(kinds[i]))
		m.emission_energy_multiplier = 1.8 + 0.20 * sin(t * (0.55 + 0.19 * float(i)) + float(i) * 1.9)


# ---------------------------------------------------------------- shared resources
static func _mesh(key: String) -> Mesh:
	if _shared.has(key):
		return _shared[key] as Mesh
	var out: Mesh = null
	if key == "flag":
		var p := PrismMesh.new()
		p.size = Vector3(0.72, 0.95, 0.03)
		out = p
	elif key == "bean_body":
		var c := CapsuleMesh.new()
		c.radius = 0.30
		c.height = 1.24
		c.radial_segments = 10
		c.rings = 4
		out = c
	elif key == "bean_head":
		var s := SphereMesh.new()
		s.radius = 0.25
		s.height = 0.50
		s.radial_segments = 10
		s.rings = 6
		out = s
	elif key == "bean_arm":
		var c2 := CapsuleMesh.new()
		c2.radius = 0.075
		c2.height = 0.56
		c2.radial_segments = 6
		c2.rings = 2
		out = c2
	elif key == "bean_visor":
		var b := BoxMesh.new()
		b.size = Vector3(0.38, 0.10, 0.08)
		out = b
	elif key == "balloon":
		var s2 := SphereMesh.new()
		s2.radius = 0.5
		s2.height = 1.2
		s2.radial_segments = 10
		s2.rings = 6
		out = s2
	elif key == "bird_body":
		var s3 := SphereMesh.new()
		s3.radius = 0.12
		s3.height = 0.24
		s3.radial_segments = 8
		s3.rings = 4
		out = s3
	elif key == "bird_wing":
		var w := BoxMesh.new()
		w.size = Vector3(0.30, 0.02, 0.17)
		out = w
	elif key == "cable":
		var cb := BoxMesh.new()
		cb.size = Vector3(ROAD_HALF * 2.0, 0.05, 0.05)
		out = cb
	_shared[key] = out
	return out


static func _vertex_color_material() -> StandardMaterial3D:
	if _shared.has("vc_mat"):
		return _shared["vc_mat"] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.vertex_color_use_as_albedo = true
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	_shared["vc_mat"] = m
	return m


static func _flat_material(color: Color) -> StandardMaterial3D:
	var key := "flat|" + color.to_html(false)
	if _shared.has(key):
		return _shared[key] as StandardMaterial3D
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.roughness = 0.8
	_shared[key] = m
	return m


func _multi(mesh: Mesh, count: int, vis_end: float) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = true
	mm.mesh = mesh
	mm.instance_count = count
	mm.custom_aabb = AABB(Vector3(-14.0, -2.0, -6.0), Vector3(28.0, 26.0, chunk_len + 12.0))
	var inst := MultiMeshInstance3D.new()
	inst.multimesh = mm
	inst.material_override = _vertex_color_material()
	inst.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	inst.visibility_range_end = vis_end
	add_child(inst)
	return mm


# ---------------------------------------------------------------- building a chunk
func _build(district: Dictionary, random: RandomNumberGenerator, density: float, chunk_index: int) -> void:
	var accent: Color = district["accent"]
	_tier = 0 if density < 0.7 else (1 if density < 0.95 else 2)
	_flick_amp = 0.55 * AccessibilityService.flash_scale() + 0.04
	_collect_halos(random)
	_make_bunting(random)
	_make_crowd(random)
	_make_pigeons(random)
	_make_balloons(random, accent)
	if chunk_index % 2 == 1:
		_make_steam(random)
	if _tier >= 2 and chunk_index % 3 == 0:
		_make_drone(random, accent)
	_animate(0.0, true)


func _collect_halos(random: RandomNumberGenerator) -> void:
	var parent := get_parent()
	if parent == null:
		return
	for child in parent.get_children():
		if child is MeshInstance3D and child.has_meta("halo"):
			var mi := child as MeshInstance3D
			var src := mi.material_override as StandardMaterial3D
			if src == null:
				continue
			var mat := src.duplicate() as StandardMaterial3D      # shared by every halo of that colour: give this one its own
			mi.material_override = mat
			var neon: bool = str(mi.get_meta("halo")) == "neon"
			_halos.append({"mat": mat, "base": mat.albedo_color, "phase": random.randf_range(0.0, 20.0),
				"speed": random.randf_range(5.0, 9.0) if neon else random.randf_range(0.6, 1.2), "neon": neon})


func _make_bunting(random: RandomNumberGenerator) -> void:
	var lines: int = 2 if _tier >= 2 else 1
	for li in range(lines):
		var z: float = chunk_len * (0.28 + 0.42 * float(li)) + random.randf_range(-3.0, 3.0)
		var y: float = random.randf_range(8.0, 9.6)
		var cable := MeshInstance3D.new()
		cable.mesh = _mesh("cable")
		cable.material_override = _flat_material(Color(0.07, 0.07, 0.09))
		cable.position = Vector3(0.0, y, z)
		cable.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		cable.visibility_range_end = 150.0
		add_child(cable)
		var count := 14
		var mm := _multi(_mesh("flag"), count, 150.0)
		var xs := PackedFloat32Array()
		xs.resize(count)
		var offset: int = random.randi_range(0, FLAG_COLORS.size() - 1)
		for i in range(count):
			xs[i] = lerpf(-ROAD_HALF + 0.7, ROAD_HALF - 0.7, (float(i) + 0.5) / float(count))
			mm.set_instance_color(i, FLAG_COLORS[(i + offset) % FLAG_COLORS.size()])
		_bunting.append({"mm": mm, "xs": xs, "y": y, "z": z, "phase": random.randf_range(0.0, 6.0)})


func _make_crowd(random: RandomNumberGenerator) -> void:
	var groups: int = 2 if _tier >= 2 else 1
	for g in range(groups):
		var side: int = -1 if random.randf() < 0.5 else 1
		var gz: float = random.randf_range(5.0, maxf(6.0, chunk_len - 8.0))
		var n: int = 2 if _tier == 0 else random.randi_range(3, 4)
		for k in range(n):
			var x: float = float(side) * random.randf_range(6.6, 8.8)
			var z: float = gz + float(k) * random.randf_range(0.9, 1.5)
			_beans.append({"x": x, "z": z, "yaw": -float(side) * PI * 0.5 + random.randf_range(-0.45, 0.25), "phase": random.randf_range(0.0, 6.28),
				"left": random.randf() < 0.55, "right": random.randf() < 0.7,
				"hoodie": BEAN_COLORS[random.randi_range(0, BEAN_COLORS.size() - 1)], "skin": SKIN_TONES[random.randi_range(0, SKIN_TONES.size() - 1)]})
	var n_total: int = _beans.size()
	if n_total == 0:
		return
	_bean_mm["body"] = _multi(_mesh("bean_body"), n_total, 115.0)
	_bean_mm["head"] = _multi(_mesh("bean_head"), n_total, 115.0)
	_bean_mm["arm"] = _multi(_mesh("bean_arm"), n_total * 2, 115.0)
	_bean_mm["visor"] = _multi(_mesh("bean_visor"), n_total, 115.0)
	for i in range(n_total):
		var b: Dictionary = _beans[i]
		(_bean_mm["body"] as MultiMesh).set_instance_color(i, b["hoodie"])
		(_bean_mm["head"] as MultiMesh).set_instance_color(i, b["skin"])
		(_bean_mm["arm"] as MultiMesh).set_instance_color(i * 2, b["hoodie"])
		(_bean_mm["arm"] as MultiMesh).set_instance_color(i * 2 + 1, b["hoodie"])
		(_bean_mm["visor"] as MultiMesh).set_instance_color(i, Color(0.05, 0.07, 0.12))


func _make_pigeons(random: RandomNumberGenerator) -> void:
	var n: int = 2 + _tier
	for i in range(n):
		var side: int = -1 if random.randf() < 0.5 else 1
		var p := Vector3(float(side) * random.randf_range(4.9, 8.4), 0.12, random.randf_range(4.0, maxf(5.0, chunk_len - 4.0)))
		_birds.append({"x": p.x, "z": p.z, "fly": -1.0, "vx": float(side) * random.randf_range(1.5, 4.0), "vy": random.randf_range(5.5, 8.5),
			"vz": random.randf_range(8.0, 13.0), "pos": p, "yaw": random.randf_range(0.0, TAU), "phase": random.randf_range(0.0, 6.28),
			"trigger": random.randf_range(14.0, 24.0)})
	_bird_mm["body"] = _multi(_mesh("bird_body"), n, 95.0)
	_bird_mm["wing"] = _multi(_mesh("bird_wing"), n * 2, 95.0)
	for i in range(n):
		var tone: float = random.randf_range(0.45, 0.78)
		(_bird_mm["body"] as MultiMesh).set_instance_color(i, Color(tone, tone, tone + 0.06))
		(_bird_mm["wing"] as MultiMesh).set_instance_color(i * 2, Color(tone * 0.8, tone * 0.8, tone * 0.9))
		(_bird_mm["wing"] as MultiMesh).set_instance_color(i * 2 + 1, Color(tone * 0.8, tone * 0.8, tone * 0.9))


func _make_balloons(random: RandomNumberGenerator, accent: Color) -> void:
	var n: int = 2 + _tier
	for i in range(n):
		var side: int = -1 if random.randf() < 0.5 else 1
		_balloons.append({"x": float(side) * random.randf_range(5.0, 8.6), "y": random.randf_range(6.0, 12.5), "z": random.randf_range(2.0, chunk_len - 2.0),
			"phase": random.randf_range(0.0, 6.28)})
	_balloon_mm = _multi(_mesh("balloon"), n, 140.0)
	for i in range(n):
		var c: Color = FLAG_COLORS[random.randi_range(0, FLAG_COLORS.size() - 1)]
		_balloon_mm.set_instance_color(i, c.lerp(accent, 0.15))


func _make_steam(random: RandomNumberGenerator) -> void:
	var side: int = -1 if random.randf() < 0.5 else 1
	var p := CPUParticles3D.new()
	p.amount = DeviceProfileService.particle_count(10 if _tier >= 2 else 6)
	p.lifetime = 2.2
	p.preprocess = 2.2
	p.direction = Vector3.UP
	p.spread = 14.0
	p.initial_velocity_min = 1.3
	p.initial_velocity_max = 2.4
	p.gravity = Vector3(0.0, 0.45, 0.0)
	p.scale_amount_min = 0.9
	p.scale_amount_max = 1.7
	p.local_coords = false
	var fade := Gradient.new()
	fade.colors = PackedColorArray([Color(1.0, 1.0, 1.0, 0.0), Color(1.0, 1.0, 1.0, 0.34), Color(1.0, 1.0, 1.0, 0.0)])
	fade.offsets = PackedFloat32Array([0.0, 0.25, 1.0])
	p.color_ramp = fade
	var quad := QuadMesh.new()
	quad.size = Vector2(1.0, 1.0)
	var m := StandardMaterial3D.new()
	m.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	m.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	m.vertex_color_use_as_albedo = true
	m.billboard_mode = BaseMaterial3D.BILLBOARD_PARTICLES
	m.albedo_texture = load("res://assets/vfx/vfx_smoke.png") as Texture2D
	m.cull_mode = BaseMaterial3D.CULL_DISABLED
	m.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED
	quad.material = m
	p.mesh = quad
	p.position = Vector3(float(side) * random.randf_range(5.6, 7.0), 0.05, random.randf_range(6.0, maxf(7.0, chunk_len - 6.0)))
	p.visibility_range_end = 110.0
	p.emitting = true
	add_child(p)


func _make_drone(random: RandomNumberGenerator, accent: Color) -> void:
	var node := Node3D.new()
	node.name = "Drone"
	var y: float = random.randf_range(11.0, 16.0)
	node.position = Vector3(random.randf_range(-5.0, 5.0), y, random.randf_range(0.0, chunk_len))
	var body := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.9, 0.22, 0.9)
	body.mesh = box
	body.material_override = _flat_material(Color(0.16, 0.18, 0.24))
	body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.add_child(body)
	var rotors: Array = []
	for sx in [-1.0, 1.0]:
		for sz in [-1.0, 1.0]:
			var rotor := MeshInstance3D.new()
			var disc := CylinderMesh.new()
			disc.top_radius = 0.30
			disc.bottom_radius = 0.30
			disc.height = 0.02
			disc.radial_segments = 10
			disc.rings = 1
			rotor.mesh = disc
			rotor.material_override = _flat_material(Color(0.6, 0.65, 0.75))
			rotor.position = Vector3(float(sx) * 0.52, 0.16, float(sz) * 0.52)
			rotor.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			node.add_child(rotor)
			rotors.append(rotor)
	var led := MeshInstance3D.new()
	var quad := QuadMesh.new()
	quad.size = Vector2(1.1, 1.1)
	led.mesh = quad
	var led_mat := MaterialLibrary.additive_sprite(accent.lerp(Color(1.0, 0.25, 0.2), 0.5), "res://assets/vfx/vfx_glow.png", true, false)
	led.material_override = led_mat
	led.position = Vector3(0.0, -0.18, 0.0)
	led.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	node.add_child(led)
	add_child(node)
	_drones.append({"node": node, "rotors": rotors, "led": led_mat, "speed": random.randf_range(-6.0, -3.0) if random.randf() < 0.5 else random.randf_range(3.0, 6.0),
		"y": y, "phase": random.randf_range(0.0, 6.28)})


# ---------------------------------------------------------------- per frame
func _process(delta: float) -> void:
	var dz: float = global_position.z + chunk_len * 0.5 - focus_z
	if dz > ACTIVE_AHEAD or dz < -ACTIVE_BEHIND:
		return                                              # too far away to be seen: keep the last pose, cost nothing
	_animate(minf(delta, 0.05), false)


func _animate(delta: float, first: bool) -> void:
	var t: float = pulse_time
	_update_halos(t)
	_update_bunting(t)
	_update_beans(t)
	_update_balloons(t)
	_update_birds(delta, first)
	_update_drones(delta, t)


func _update_halos(t: float) -> void:
	for h in _halos:
		var d: Dictionary = h
		var base: Color = d["base"]
		var k: float = 1.0
		if bool(d["neon"]):
			k = 0.88 + 0.12 * sin(t * float(d["speed"]) + float(d["phase"]))
			var cycle: float = fmod(t * 0.43 + float(d["phase"]) * 0.17, 1.0)
			if cycle > 0.94:
				k *= 1.0 - _flick_amp * (0.55 + 0.45 * sin(t * 61.0))      # an occasional stutter, like a tired neon tube
		else:
			k = 0.93 + 0.07 * sin(t * float(d["speed"]) + float(d["phase"]))
		(d["mat"] as StandardMaterial3D).albedo_color = Color(base.r * k, base.g * k, base.b * k, base.a)


func _update_bunting(t: float) -> void:
	var hang: Transform3D = Transform3D(Basis(Vector3.BACK, PI), Vector3(0.0, -0.475, 0.0))      # apex down, hinged on the cable
	for line in _bunting:
		var d: Dictionary = line
		var mm: MultiMesh = d["mm"]
		var xs: PackedFloat32Array = d["xs"]
		var y: float = float(d["y"])
		var z: float = float(d["z"])
		var ph: float = float(d["phase"])
		for i in range(xs.size()):
			var swing: float = 0.34 * sin(t * 2.3 + float(i) * 0.9 + ph) + 0.10 * sin(t * 5.1 + float(i) * 1.7)
			mm.set_instance_transform(i, Transform3D(Basis(Vector3.RIGHT, swing), Vector3(xs[i], y, z)) * hang)


func _update_beans(t: float) -> void:
	if _beans.is_empty():
		return
	var mm_body: MultiMesh = _bean_mm["body"]
	var mm_head: MultiMesh = _bean_mm["head"]
	var mm_arm: MultiMesh = _bean_mm["arm"]
	var mm_visor: MultiMesh = _bean_mm["visor"]
	for i in range(_beans.size()):
		var b: Dictionary = _beans[i]
		var ph: float = float(b["phase"])
		var hop: float = absf(sin(t * 5.6 + ph)) * 0.16
		var yaw: Basis = Basis(Vector3.UP, float(b["yaw"]))
		var base: Vector3 = Vector3(float(b["x"]), 0.0, float(b["z"]))
		mm_body.set_instance_transform(i, Transform3D(yaw, base + Vector3(0.0, 0.62 + hop, 0.0)))
		mm_head.set_instance_transform(i, Transform3D(yaw, base + Vector3(0.0, 1.50 + hop, 0.0)))
		mm_visor.set_instance_transform(i, Transform3D(yaw, base + yaw * Vector3(0.0, 1.52 + hop, 0.22)))
		for side in range(2):
			var s: float = 1.0 if side == 0 else -1.0
			var up: bool = bool(b["left"]) if side == 0 else bool(b["right"])
			var angle: float = 0.18 + 0.06 * sin(t * 2.0 + ph)
			if up:
				angle = 2.45 + 0.55 * sin(t * 9.0 + ph + float(side) * 1.9)         # arm thrown up and waving
			var arm_basis: Basis = yaw * Basis(Vector3.BACK, s * angle)
			var pivot: Vector3 = base + yaw * Vector3(s * 0.36, 1.06 + hop, 0.0)
			mm_arm.set_instance_transform(i * 2 + side, Transform3D(arm_basis, pivot + arm_basis * Vector3(0.0, -0.30, 0.0)))


func _update_balloons(t: float) -> void:
	if _balloon_mm == null:
		return
	for i in range(_balloons.size()):
		var b: Dictionary = _balloons[i]
		var ph: float = float(b["phase"])
		var pos := Vector3(float(b["x"]) + 0.45 * sin(t * 0.6 + ph * 2.0), float(b["y"]) + 0.55 * sin(t * 0.9 + ph), float(b["z"]) + 0.3 * sin(t * 0.5 + ph))
		_balloon_mm.set_instance_transform(i, Transform3D(Basis(Vector3.UP, 0.4 * sin(t * 0.7 + ph)), pos))


func _update_birds(delta: float, first: bool) -> void:
	if _birds.is_empty():
		return
	var mm_body: MultiMesh = _bird_mm["body"]
	var mm_wing: MultiMesh = _bird_mm["wing"]
	var gz: float = 0.0
	if not first and is_inside_tree():
		gz = global_position.z
	for i in range(_birds.size()):
		var b: Dictionary = _birds[i]
		var pos: Vector3 = b["pos"]
		var fly: float = float(b["fly"])
		var yaw: float = float(b["yaw"])
		var flap: float = -0.12                                    # wings folded
		if fly < 0.0:
			var ahead: float = gz + pos.z - focus_z
			if not first and ahead < float(b["trigger"]) and ahead > -4.0:
				fly = 0.0                                          # the runner is close: take off
			var cycle: float = fmod(pulse_time * 1.3 + float(b["phase"]), 3.0)
			pos.y = 0.05 if cycle < 0.4 else 0.12                   # now and then it dips to peck at the ground
		else:
			fly += delta
			pos.x += float(b["vx"]) * delta
			pos.y += float(b["vy"]) * delta
			pos.z += float(b["vz"]) * delta
			b["vy"] = maxf(float(b["vy"]) - 2.2 * delta, 1.2)
			yaw = atan2(float(b["vx"]), float(b["vz"]))
			flap = 0.85 * sin(fly * 30.0 + float(b["phase"]))
		b["fly"] = fly
		b["pos"] = pos
		b["yaw"] = yaw
		var gone: bool = fly > 4.5
		var basis_body: Basis = Basis(Vector3.UP, yaw)
		var body_basis: Basis = Basis.from_scale(Vector3.ZERO)
		if not gone:
			body_basis = basis_body * Basis.from_scale(Vector3(1.0, 0.9, 1.7))
		mm_body.set_instance_transform(i, Transform3D(body_basis, pos + Vector3(0.0, 0.10, 0.0)))
		for side in range(2):
			var s: float = 1.0 if side == 0 else -1.0
			var wing_basis: Basis = Basis.from_scale(Vector3.ZERO)
			if not gone:
				wing_basis = basis_body * Basis(Vector3.BACK, s * flap)
			mm_wing.set_instance_transform(i * 2 + side, Transform3D(wing_basis, pos + Vector3(0.0, 0.14, 0.0) + basis_body * Vector3(s * 0.17, 0.0, 0.0)))


func _update_drones(delta: float, t: float) -> void:
	for dr in _drones:
		var d: Dictionary = dr
		var node: Node3D = d["node"]
		var ph: float = float(d["phase"])
		var z: float = node.position.z + float(d["speed"]) * delta
		if z > chunk_len + 14.0:
			z = -14.0
		elif z < -14.0:
			z = chunk_len + 14.0
		node.position = Vector3(node.position.x, float(d["y"]) + 0.35 * sin(t * 1.7 + ph), z)
		node.rotation.z = 0.10 * sin(t * 1.3 + ph)
		for r in d["rotors"]:
			(r as Node3D).rotation.y = t * 55.0
		var m: StandardMaterial3D = d["led"]
		var blink: float = 1.0 if fmod(t * 1.6 + ph, 1.0) < 0.45 else 0.25
		m.albedo_color = Color(m.albedo_color.r, m.albedo_color.g, m.albedo_color.b, blink)
