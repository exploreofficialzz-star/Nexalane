extends Node
class_name PlayerSession

signal started
signal ended(score: int, distance: float)
signal objective_completed(label: String)
signal revive_offered
signal revive_countdown(seconds_left: float)
signal toast(message: String)

const REVIVE_WINDOW := 6.0
const REVIVE_JUMP := 18.0

var runner: RunnerController
var flow: FlowSystem
var power: PowerSystem
var score: ScoreSystem
var active := false
var finished := true
var elapsed := 0.0
var run_start_z := 0.0
var run_mode := "ENDLESS"
var objective_target := 0.0
var objective_reward := 0
var objective_kind := "endless"
var peak_flow_stage := 0
var run_collectibles := 0
var run_credits := 0
var objective_finished := false
var routes_selected := 0
var pending_death := false
var revived_this_run := false
var revive_time_left := 0.0
var last_summary: Dictionary = {}
var _power_active_last := false
var _revive_held := false

func setup(player: RunnerController) -> void:
	runner = player
	flow = FlowSystem.new()
	add_child(flow)
	power = PowerSystem.new()
	add_child(power)
	score = ScoreSystem.new()
	add_child(score)
	runner.collided.connect(_on_collision)
	runner.collectible_collected.connect(_on_collect)
	runner.near_miss.connect(_on_near_miss)
	runner.power_requested.connect(request_power)
	runner.power_consumed.connect(_on_power_consumed)
	flow.flow_changed.connect(_on_flow_changed)
	flow.flow_changed.connect(runner.set_flow_state)
	power.power_changed.connect(_on_power_changed)
	power.equipped = str(SaveService.data["profile"].get("equipped_power", "phase_shield"))

func begin(run_seed: int = 0, mode: String = "ENDLESS") -> void:
	run_mode = mode.to_upper()
	GameModeService.set_mode(run_mode)
	AppState.set_mode(GameModeService.mode_enum())
	AppState.begin_run(run_seed)
	active = true
	finished = false
	objective_finished = false
	_power_active_last = false
	_revive_held = false
	elapsed = 0.0
	run_collectibles = 0
	run_credits = 0
	peak_flow_stage = 0
	routes_selected = 0
	pending_death = false
	revived_this_run = false
	var objective := GameModeService.objective()
	objective_kind = str(objective["kind"])
	objective_target = float(objective["target"])
	objective_reward = int(objective["reward"])
	run_start_z = runner.global_position.z
	power.equipped = str(SaveService.data["profile"].get("equipped_power", "phase_shield"))
	power.reset_for_run()
	flow.reset()
	score.reset()
	runner.configure(RunDirector.speed_at(0.0))
	runner.refresh_appearance()
	runner.begin_run()
	GhostService.begin_recording(run_start_z)
	started.emit()
	AnalyticsService.track("run_start", {"seed": AppState.active_seed, "runner": AppState.selected_runner, "mode": run_mode})

func _process(delta: float) -> void:
	if pending_death:
		if not _revive_held:
			revive_time_left = maxf(0.0, revive_time_left - delta)
			revive_countdown.emit(revive_time_left)
			if revive_time_left <= 0.0:
				decline_revive()
		return
	if not active or AppState.paused:
		return
	elapsed += delta
	AppState.run_distance = maxf(0.0, runner.global_position.z - run_start_z)
	flow.tick(delta, true)
	power.tick(delta)
	MissionService.report("distance", runner.speed * delta)
	AppState.run_score = score.tick(delta, runner.speed, flow.multiplier)
	AppState.run_flow = flow.flow
	LiveOpsService.add_season_xp_fractional(delta * 2.0)
	runner.speed = move_toward(runner.speed, runner.target_speed(RunDirector.speed), delta * RunnerController.STARTING_SPEED_RAMP)
	GhostService.sample(delta, runner)
	_check_objective()

# ---------------------------------------------------------------- objective
func _check_objective() -> void:
	if objective_finished or objective_kind == "endless":
		return
	var complete := false
	match objective_kind:
		"distance":
			complete = AppState.run_distance >= objective_target
		"score":
			complete = float(AppState.run_score) >= objective_target
		"collect":
			complete = float(run_collectibles) >= objective_target
		"flow_stage":
			complete = float(peak_flow_stage) >= objective_target
	if complete:
		objective_finished = true
		objective_completed.emit("%s COMPLETE" % GameModeService.objective_text())
		_finish_run("objective")

# ---------------------------------------------------------------- signals from flow / power / runner
func _on_flow_changed(_value: float, stage: int, _multiplier: float) -> void:
	peak_flow_stage = maxi(peak_flow_stage, stage)

func request_power() -> void:
	if not active or AppState.paused:
		return
	power.activate(power.equipped)

func _on_power_changed(power_id: String, is_active: bool, remaining: float) -> void:
	runner.power_remaining = remaining
	if is_active == _power_active_last:
		return                                       # per-frame countdown ticks need no state change
	_power_active_last = is_active
	runner.set_power_state(power_id, is_active, remaining)
	runner.set_power_effect(power_id, is_active)
	if is_active and power_id == "flow_surge":
		flow.add_precision(0.35, "power")

func _on_power_consumed(_power_id: String) -> void:
	power.deactivate("consumed")

func register_route(route_class: String) -> void:
	if not active:
		return
	var normalized := route_class.to_upper()
	var bonus := 45.0
	var credits := 20
	match normalized:
		"REWARD":
			bonus = 120.0
			credits = 50
		"FAST":
			bonus = 90.0
			credits = 35
		"SECRET":
			bonus = 175.0
			credits = 90
		"CHAOS":
			bonus = 140.0
			credits = 60
	routes_selected += 1
	score.route(bonus, flow.multiplier)
	_grant_credits(credits, "route_%s" % normalized.to_lower())
	AnalyticsService.track("route_selected", {"route": normalized, "count": routes_selected})
	MissionService.report("route", 1.0)
	toast.emit("%s ROUTE  +%d" % [normalized, credits])

func _on_collect(value: int) -> void:
	run_collectibles += 1
	SaveService.data["total_collectibles"] = int(SaveService.data.get("total_collectibles", 0)) + 1
	_grant_credits(value, "run_collect")
	MissionService.report("collect", 1.0)
	score.collect(value, flow.multiplier)
	flow.add_precision(0.02, "collection")

func _on_near_miss() -> void:
	var bonus := RemoteConfigService.get_number("flow_near_miss_bonus", 0.10)
	flow.add_precision(bonus, "near_miss")
	score.stunt(35.0, flow.multiplier)

func _grant_credits(base_amount: int, source: String) -> void:
	var amount := _event_reward(base_amount)
	if amount > 0:
		run_credits += amount
		EconomyService.grant("credits", amount, source)

# ---------------------------------------------------------------- death / revive
func _on_collision(obstacle_id: String) -> void:
	if not active:
		return
	flow.break_flow("collision")
	if not revived_this_run and AdsService.can_offer_rewarded():
		active = false
		pending_death = true
		revive_time_left = REVIVE_WINDOW
		runner.stop_run()
		AnalyticsService.track("revive_offered", {"obstacle": obstacle_id, "mode": run_mode})
		revive_offered.emit()
		return
	_finish_run("collision", obstacle_id)

## Called while a rewarded ad is on screen so the decision timer does not run out underneath it.
func hold_revive_timer(held: bool) -> void:
	_revive_held = held

func revive() -> bool:
	if not pending_death:
		return false
	pending_death = false
	revived_this_run = true
	active = true
	_revive_held = false
	var from_z := runner.global_position.z
	runner.global_position.z += REVIVE_JUMP
	runner.global_position.y = 0.05
	runner.velocity = Vector3.ZERO
	runner.begin_run()
	runner.grant_invulnerability(2.4)
	power.reset_for_run()
	_power_active_last = false
	flow.reset()
	get_tree().call_group("track", "clear_obstacles_in_range", from_z - 4.0, from_z + REVIVE_JUMP + 30.0)
	AppState.set_paused(false)
	AnalyticsService.track("revive_used", {"mode": run_mode})
	AudioService.play_sfx("revive")
	return true

func decline_revive() -> void:
	if not pending_death:
		return
	pending_death = false
	_finish_run("collision_declined")

# ---------------------------------------------------------------- finishing
## Ends the run immediately (quit from the pause menu); progress earned so far is kept.
func finish_now(reason: String = "quit") -> void:
	_finish_run(reason)

func _finish_run(reason: String, obstacle_id: String = "") -> void:
	if finished:
		return
	finished = true
	active = false
	pending_death = false
	runner.stop_run()
	flow.break_flow(reason)
	AppState.run_score = score.total()
	var previous_best_score := int(SaveService.data.get("best_score", 0))
	var previous_best_distance := float(SaveService.data.get("best_distance", 0.0))
	SaveService.data["runs_completed"] = int(SaveService.data.get("runs_completed", 0)) + 1
	SaveService.data["best_score"] = maxi(previous_best_score, AppState.run_score)
	SaveService.data["best_distance"] = maxf(previous_best_distance, AppState.run_distance)
	var base_finish := int(AppState.run_distance / 6.0)
	var mode_bonus := objective_reward if objective_finished else 0
	var finish_reward := _event_reward(base_finish + mode_bonus)
	if finish_reward > 0:
		run_credits += finish_reward
		EconomyService.grant("credits", finish_reward, "run_finish")
	var xp_gain := maxi(10, int(AppState.run_distance / 3.0))
	ProgressionService.add_xp(xp_gain, "run_finish")
	ProgressionService.add_mastery(AppState.selected_runner, 1 if objective_finished else 0)
	_update_mode_records()
	_evaluate_achievements()
	if run_mode != "GHOST":
		GhostService.save_local_ghost()
	SaveService.save_game()
	last_summary = {
		"score": AppState.run_score, "distance": AppState.run_distance, "credits": run_credits, "xp": xp_gain,
		"collectibles": run_collectibles, "peak_flow": peak_flow_stage, "reason": reason, "mode": run_mode,
		"objective_finished": objective_finished, "objective_text": GameModeService.objective_text(),
		"new_best_score": AppState.run_score > previous_best_score, "new_best_distance": AppState.run_distance > previous_best_distance,
		"finish_reward": finish_reward
	}
	AnalyticsService.track("run_end", {"score": AppState.run_score, "distance": AppState.run_distance, "obstacle": obstacle_id, "flow": flow.flow, "mode": run_mode, "reason": reason})
	if run_mode in ["DAILY", "WEEKLY"]:
		var board_key := GameModeService.daily_key() if run_mode == "DAILY" else GameModeService.weekly_key()
		BackendService.submit_score("%s_%s" % [run_mode.to_lower(), board_key], AppState.run_score, {"seed": AppState.active_seed, "mode": run_mode})
	AppState.finish_run()
	ended.emit(AppState.run_score, AppState.run_distance)

func _update_mode_records() -> void:
	match run_mode:
		"STORY":
			if objective_finished:
				var story: Dictionary = SaveService.data["story"]
				story["completed_chapters"] = maxi(int(story.get("completed_chapters", 0)), GameModeService.selected_story_chapter)
				story["last_completed_chapter"] = GameModeService.selected_story_chapter
				SaveService.data["progression"]["chapter"] = mini(12, GameModeService.selected_story_chapter + 1)
				GameModeService.selected_story_chapter = clampi(int(SaveService.data["progression"]["chapter"]), 1, 12)
		"DAILY":
			var daily_key := GameModeService.daily_key()
			var daily: Dictionary = SaveService.data["daily"]
			if str(daily.get("key", "")) != daily_key:
				daily["key"] = daily_key
				daily["best_score"] = AppState.run_score
				daily["claimed"] = false
			else:
				daily["best_score"] = maxi(int(daily.get("best_score", 0)), AppState.run_score)
			if objective_finished and not bool(daily.get("claimed", false)):
				daily["claimed"] = true
				EconomyService.grant("nova", 25, "daily_objective")
		"WEEKLY":
			var weekly_key := GameModeService.weekly_key()
			var weekly: Dictionary = SaveService.data["weekly"]
			if str(weekly.get("key", "")) != weekly_key:
				weekly["key"] = weekly_key
				weekly["best_score"] = AppState.run_score
				weekly["claimed"] = false
			else:
				weekly["best_score"] = maxi(int(weekly.get("best_score", 0)), AppState.run_score)
			if objective_finished and not bool(weekly.get("claimed", false)):
				weekly["claimed"] = true
				EconomyService.grant("nova", 60, "weekly_objective")
		_:
			return

func _evaluate_achievements() -> void:
	if int(SaveService.data.get("runs_completed", 0)) >= 1:
		AchievementService.grant("first_run", 100)
	if AppState.run_distance >= 500.0:
		AchievementService.grant("distance_500", 200)
	if AppState.run_distance >= 5000.0:
		AchievementService.grant("distance_5000", 750)
	if AppState.run_score >= 5000:
		AchievementService.grant("score_5000", 400)
	if peak_flow_stage >= 4:
		AchievementService.grant("flow_stage_4", 500)
	if int(SaveService.data.get("total_collectibles", 0)) >= 100:
		AchievementService.grant("collect_100", 400)
	if run_mode == "STORY" and objective_finished and GameModeService.selected_story_chapter >= 12:
		AchievementService.grant("story_complete", 2500)

func _event_reward(base_amount: int) -> int:
	var amount := maxi(0, base_amount)
	var powered := int(round(float(amount) * runner.credit_multiplier))
	if run_mode == "EVENT":
		return EventEngine.apply_reward(powered)
	if run_mode == "CHALLENGE":
		var challenge := ChallengeService.current()
		if int(challenge.get("modifier", 0)) == 4:
			return int(round(float(powered) * 1.5))
	return powered
