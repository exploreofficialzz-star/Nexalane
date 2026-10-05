extends Node
class_name AppStateService

signal mode_changed(mode: String)
signal run_started(run_seed: int)
signal run_finished(score: int, distance: float)
signal paused_changed(value: bool)

const PRODUCT_VERSION := "0.4.5"
const CONTENT_VERSION := "2026.10.03"
const TUNING_VERSION := 5

enum GameMode { MENU, STORY, ENDLESS, DAILY, WEEKLY, GHOST, CHALLENGE, EVENT, TRAINING }

var mode: GameMode = GameMode.MENU
var active_seed: int = 0
var active_run_id: String = ""
var run_score: int = 0
var run_distance: float = 0.0
var run_flow: float = 0.0
var selected_runner: String = "Kade"
var selected_mode: String = "ENDLESS"
var paused := false
var session_started_at_ms := 0

func set_mode(next_mode: GameMode) -> void:
	mode = next_mode
	mode_changed.emit(GameMode.keys()[mode].to_lower())

func set_paused(value: bool) -> void:
	if paused == value:
		return
	paused = value
	paused_changed.emit(paused)

func begin_run(run_seed: int = 0) -> int:
	paused = false
	active_seed = run_seed if run_seed != 0 else _generate_seed()
	active_run_id = "%s-%s" % [Time.get_datetime_string_from_system(true).replace(":", "").replace("-", ""), str(active_seed)]
	run_score = 0
	run_distance = 0.0
	run_flow = 0.0
	session_started_at_ms = Time.get_ticks_msec()
	run_started.emit(active_seed)
	return active_seed

func finish_run() -> void:
	run_finished.emit(run_score, run_distance)
	set_mode(GameMode.MENU)

func _generate_seed() -> int:
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	return maxi(1, int(rng.randi()))
