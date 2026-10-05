extends Node
class_name GhostServiceImpl

## Records the runner's line (x / height) against distance travelled so the next run can race it.
## Samples store z RELATIVE to the run start, so a ghost lines up with the player at the same distance.

const SAVE_PATH := "user://nexalane_last_ghost.json"
const FORMAT_VERSION := 3

var current_samples: Array[Dictionary] = []
var record_interval := 0.25
var accumulator := 0.0
var elapsed := 0.0
var start_z := 0.0

func begin_recording(start_z_value: float = 0.0) -> void:
	current_samples.clear()
	accumulator = 0.0
	elapsed = 0.0
	start_z = start_z_value

func sample(delta: float, runner: Node3D) -> void:
	if runner == null:
		return
	elapsed += delta
	accumulator += delta
	if accumulator < record_interval:
		return
	accumulator = 0.0
	var p := runner.global_position
	current_samples.append({"t": elapsed, "x": p.x, "y": p.y, "z": p.z - start_z})

func export_ghost() -> Dictionary:
	return {"version": FORMAT_VERSION, "seed": AppState.active_seed, "runner": AppState.selected_runner, "samples": current_samples.duplicate(true)}

func save_local_ghost() -> void:
	var ghost := export_ghost()
	if not validate_ghost(ghost):
		return                               # too short to be worth racing; keep the previous ghost
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(ghost))
		file.close()

func load_local_ghost() -> Dictionary:
	if not FileAccess.file_exists(SAVE_PATH):
		return {}
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return {}
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	file.close()
	if typeof(parsed) == TYPE_DICTIONARY and validate_ghost(parsed):
		return parsed
	return {}

func validate_ghost(ghost: Dictionary) -> bool:
	if int(ghost.get("version", 0)) != FORMAT_VERSION or not ghost.has("seed"):
		return false
	var samples: Variant = ghost.get("samples")
	return typeof(samples) == TYPE_ARRAY and samples.size() >= 2

func has_local_ghost() -> bool:
	return not load_local_ghost().is_empty()

## Returns (x, y, distance) of the recorded line at the given run distance.
func position_at_distance(distance: float, samples: Array) -> Vector3:
	if samples.is_empty():
		return Vector3.ZERO
	var target_z := maxf(0.0, distance)
	var first: Dictionary = samples[0]
	var previous: Dictionary = first
	for entry in samples:
		var current: Dictionary = entry
		var z := float(current.get("z", 0.0))
		if z >= target_z:
			var prev_z := float(previous.get("z", 0.0))
			var span := maxf(0.001, z - prev_z)
			var t := clampf((target_z - prev_z) / span, 0.0, 1.0)
			return Vector3(
				lerpf(float(previous.get("x", 0.0)), float(current.get("x", 0.0)), t),
				lerpf(float(previous.get("y", 0.0)), float(current.get("y", 0.0)), t),
				target_z
			)
		previous = current
	var last: Dictionary = samples[samples.size() - 1]
	return Vector3(float(last.get("x", 0.0)), float(last.get("y", 0.0)), target_z)

## Time based playback: where the recorded run was `t` seconds after its start. Because the same seed produces the
## same track, the ghost really races you - it pulls ahead or falls behind depending on pace.
func position_at_time(t: float, samples: Array) -> Vector3:
	if samples.is_empty():
		return Vector3.ZERO
	var previous: Dictionary = samples[0]
	for entry in samples:
		var current: Dictionary = entry
		var ct := float(current.get("t", 0.0))
		if ct >= t:
			var pt := float(previous.get("t", 0.0))
			var k := clampf((t - pt) / maxf(0.001, ct - pt), 0.0, 1.0)
			return Vector3(
				lerpf(float(previous.get("x", 0.0)), float(current.get("x", 0.0)), k),
				lerpf(float(previous.get("y", 0.0)), float(current.get("y", 0.0)), k),
				lerpf(float(previous.get("z", 0.0)), float(current.get("z", 0.0)), k)
			)
		previous = current
	var last: Dictionary = samples[samples.size() - 1]
	return Vector3(float(last.get("x", 0.0)), float(last.get("y", 0.0)), float(last.get("z", 0.0)))

func end_time(samples: Array) -> float:
	if samples.is_empty():
		return 0.0
	var last: Dictionary = samples[samples.size() - 1]
	return float(last.get("t", 0.0))
