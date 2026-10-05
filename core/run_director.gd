extends Node
class_name RunDirectorImpl

signal difficulty_changed(level: float)

const DIFFICULTY_DISTANCE := 4500.0

var distance := 0.0
var speed := 16.0
var difficulty := 0.0
var run_seed := 0
var _last_milestone := -1

func _ready() -> void:
	AppState.run_started.connect(_on_run_started)

## Difficulty is a pure function of track distance so that the track generator is deterministic
## (it must never depend on how far the runner happens to have travelled when a chunk is spawned).
func difficulty_at(distance_m: float) -> float:
	return clampf(distance_m / DIFFICULTY_DISTANCE, 0.0, 1.0)

func speed_at(distance_m: float) -> float:
	var base := RemoteConfigService.get_number("base_speed", 16.0)
	var ramp := RemoteConfigService.get_number("speed_ramp", 0.045)
	var top := RemoteConfigService.get_number("max_speed", 31.0)
	return minf(base + distance_m * ramp, top)

func reset() -> void:
	distance = 0.0
	difficulty = 0.0
	speed = speed_at(0.0)
	_last_milestone = -1

func _process(_delta: float) -> void:
	if AppState.mode == AppState.GameMode.MENU or AppState.paused:
		return
	distance = AppState.run_distance
	difficulty = difficulty_at(distance)
	speed = speed_at(distance)
	var milestone := int(distance / 500.0)
	if milestone != _last_milestone:
		_last_milestone = milestone
		difficulty_changed.emit(difficulty)

func _on_run_started(new_seed: int) -> void:
	run_seed = new_seed
	reset()
