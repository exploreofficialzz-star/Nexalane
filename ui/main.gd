extends Node3D
class_name NexalaneMain

## Composition root: builds the world, wires every system together and owns the run lifecycle
## (menu attract mode -> fade -> countdown -> run -> results).

const MENU_SEED := 20260101

var hud: GameHUD
var track: TrackManager
var runner: RunnerController
var session: PlayerSession
var world: WorldEnvironmentController
var camera: ChaseCamera
var ghost_root: Node3D
var running := false
var starting := false
var pending_revive := false
var rewarded_claimed := false
var quitting := false
var _countdown_active := false
var _ghost_samples: Array = []
var _ghost_material: StandardMaterial3D
var _hud_clock := 0.0

func _ready() -> void:
	world = WorldEnvironmentController.new()
	world.name = "World"
	add_child(world)
	track = TrackManager.new()
	track.name = "Track"
	add_child(track)
	runner = RunnerController.new()
	runner.name = "Runner"
	add_child(runner)
	camera = ChaseCamera.new()
	camera.name = "Camera"
	add_child(camera)
	camera.target = runner
	session = PlayerSession.new()
	session.name = "Session"
	add_child(session)
	session.setup(runner)
	hud = GameHUD.new()
	hud.name = "HUD"
	add_child(hud)
	world.setup(runner)
	_connect_signals()
	AppState.selected_runner = str(SaveService.data["profile"].get("selected_runner", "Kade"))
	AppState.selected_mode = GameModeService.selected_mode
	if not ConsentService.has_decision():
		AnalyticsService.enabled = false
	AnalyticsService.track("app_open")
	_enter_menu_scene()

func _connect_signals() -> void:
	hud.start_requested.connect(start_run)
	hud.power_requested.connect(session.request_power)
	hud.pause_requested.connect(_toggle_pause)
	hud.resume_requested.connect(_resume)
	hud.quit_to_menu_requested.connect(_quit_to_menu)
	hud.rewarded_requested.connect(_watch_rewarded)
	hud.revive_requested.connect(_watch_revive)
	hud.end_run_requested.connect(_decline_revive)
	hud.home_requested.connect(_enter_menu_scene)
	session.started.connect(_on_run_started)
	session.ended.connect(_on_run_ended)
	session.objective_completed.connect(hud.flash)
	session.revive_offered.connect(_on_revive_offered)
	session.revive_countdown.connect(hud.set_revive_time)
	session.toast.connect(hud.flash)
	runner.collided.connect(_on_runner_collided)
	runner.power_consumed.connect(_on_power_consumed)
	runner.near_miss.connect(_on_near_miss)
	track.route_selected.connect(session.register_route)
	track.route_fork.connect(_on_route_fork)
	track.district_changed.connect(_on_district_changed)
	AdsService.rewarded_result.connect(_on_rewarded_result)
	BillingService.purchase_succeeded.connect(_on_purchase_succeeded)
	BillingService.purchase_failed.connect(_on_purchase_failed)
	MissionService.mission_completed.connect(_on_mission_completed)
	AchievementService.achievement_unlocked.connect(_on_achievement_unlocked)

# ---------------------------------------------------------------- scene states
## Menu "attract mode": a real track with the runner idling at the start line, framed by the hero camera.
func _enter_menu_scene() -> void:
	_destroy_ghost()
	runner.stop_run()
	runner.hold_idle = false
	runner.position = Vector3(0.0, 0.05, TrackManager.RUN_START_Z)
	runner.lane = 1
	runner.velocity = Vector3.ZERO
	runner.visible = true
	track.setup(runner, MENU_SEED)
	world.set_time_variant(MENU_SEED)
	world.set_district("Old Quarter", true)
	camera.set_menu_mode(true)
	camera.snap()
	runner.refresh_appearance()

func start_run() -> void:
	if starting or running:
		return
	starting = true
	quitting = false
	rewarded_claimed = false
	AppState.set_paused(false)
	await hud.transition_to_black(0.2)
	if not bool(SaveService.data.get("tutorial_complete", false)):
		GameModeService.set_mode("TRAINING")
	AppState.selected_mode = GameModeService.selected_mode
	var run_seed := GameModeService.seed_for_selected_mode()
	_destroy_ghost()
	runner.position = Vector3(0.0, 0.05, TrackManager.RUN_START_Z)
	runner.lane = 1
	runner.velocity = Vector3.ZERO
	session.begin(run_seed, GameModeService.selected_mode)     # sets the mode and resets RunDirector first ...
	track.setup(runner, AppState.active_seed)                  # ... so the track is generated from a clean state
	world.set_time_variant(AppState.active_seed)
	if GameModeService.selected_mode == "GHOST":
		_prepare_ghost()
	camera.set_menu_mode(true)
	camera.snap()
	AppState.set_paused(true)
	runner.hold_idle = true
	_countdown_active = true
	running = true
	hud.set_run_visible(true)
	if GameModeService.selected_mode == "EVENT":
		AudioService.play_music("event")
	await hud.transition_from_black(0.3)
	camera.set_menu_mode(false)
	for step in ["3", "2", "1"]:
		hud.show_countdown_step(step)
		AudioService.play_sfx("countdown")
		await get_tree().create_timer(0.55).timeout
	hud.show_countdown_step("GO")
	AudioService.play_sfx("go")
	runner.hold_idle = false
	_countdown_active = false
	AppState.set_paused(false)
	if not bool(SaveService.data.get("tutorial_complete", false)):
		SaveService.data["tutorial_complete"] = true
		SaveService.save_game()
	starting = false

# ---------------------------------------------------------------- pause
func _toggle_pause() -> void:
	if not running or _countdown_active or session.pending_death:
		return
	if AppState.paused:
		_resume()
	else:
		AppState.set_paused(true)
		hud.set_paused(true)
		AnalyticsService.track("run_pause")

func _resume() -> void:
	if not running or not AppState.paused or _countdown_active:
		return
	_countdown_active = true
	hud.set_paused(false)
	for step in ["3", "2", "1"]:
		hud.show_countdown_step(step)
		await get_tree().create_timer(0.5).timeout
	hud.show_countdown_step("")
	AppState.set_paused(false)
	_countdown_active = false
	AnalyticsService.track("run_resume")

func _quit_to_menu() -> void:
	if not running:
		return
	quitting = true
	AppState.set_paused(false)
	hud.set_paused(false)
	session.finish_now("quit")

func _unhandled_input(event: InputEvent) -> void:
	if event.is_action_pressed("ui_cancel") and running:
		_toggle_pause()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_APPLICATION_PAUSED:
		SaveService.save_game()
		AnalyticsService.flush()
		if running and not _countdown_active and not AppState.paused and not session.pending_death:
			AppState.set_paused(true)
			hud.set_paused(true)
	elif what == NOTIFICATION_WM_CLOSE_REQUEST:
		SaveService.save_game()
		AnalyticsService.flush()
	elif what == NOTIFICATION_WM_GO_BACK_REQUEST:
		if running:
			_toggle_pause()
		elif hud.detail_layer.visible:
			hud.close_detail()
		elif hud.end_layer.visible:
			hud._on_home_pressed()
		elif not hud.modal_layer.visible:
			SaveService.save_game()
			get_tree().quit()

# ---------------------------------------------------------------- run events
func _on_run_started() -> void:
	AnalyticsService.track("gameplay_started", {"seed": AppState.active_seed})

func _on_run_ended(_score: int, _distance: float) -> void:
	running = false
	pending_revive = false
	AppState.set_paused(false)
	AudioService.set_intensity(0.0)
	AudioService.play_music("menu")
	hud.set_paused(false)
	hud.show_revive(false)
	_destroy_ghost()
	camera.set_menu_mode(true)
	if quitting:
		quitting = false
		hud.set_run_visible(false)
		_enter_menu_scene()
		return
	hud.show_end(session.last_summary)
	AdsService.show_interstitial()

func _on_runner_collided(_obstacle_id: String) -> void:
	camera.kick(1.0)

func _on_power_consumed(_power_id: String) -> void:
	camera.kick(0.6)
	hud.flash("SHIELD ABSORBED THE HIT")

func _on_near_miss() -> void:
	camera.kick(0.12)

func _on_route_fork(_options: Array[String]) -> void:
	pass

func _on_district_changed(district_name: String) -> void:
	world.set_district(district_name)
	if not running:
		return
	hud.set_district(district_name)
	if GameModeService.selected_mode != "EVENT":
		AudioService.play_music(str(ContentRegistry.district_by_name(district_name)["id"]))

func _on_mission_completed(mission_id: String) -> void:
	hud.flash("MISSION COMPLETE  •  %s" % mission_id.replace("daily_", "").to_upper())

func _on_achievement_unlocked(_achievement_id: String, title: String) -> void:
	hud.flash("ACHIEVEMENT  •  %s" % title.to_upper())

# ---------------------------------------------------------------- revive / rewarded
func _on_revive_offered() -> void:
	pending_revive = true
	hud.show_revive(true)

func _watch_revive() -> void:
	if not pending_revive:
		return
	session.hold_revive_timer(true)
	AdsService.show_rewarded("revive")

func _decline_revive() -> void:
	if not pending_revive:
		return
	pending_revive = false
	hud.show_revive(false)
	session.decline_revive()

func _watch_rewarded() -> void:
	if rewarded_claimed or not AdsService.can_offer_rewarded():
		return
	AdsService.show_rewarded("post_run")

func _on_rewarded_result(success: bool) -> void:
	session.hold_revive_timer(false)
	if pending_revive:
		if success and session.revive():
			pending_revive = false
			hud.show_revive(false)
			return
		hud.flash("REVIVE UNAVAILABLE")
		return
	if not success or rewarded_claimed:
		return
	rewarded_claimed = true
	var bonus_factor := maxf(0.0, RemoteConfigService.get_number("rewarded_multiplier", 2.0) - 1.0)
	var reward := maxi(50, int(round(float(session.last_summary.get("finish_reward", 0)) * bonus_factor)))
	EconomyService.grant("credits", reward, "rewarded_ad")
	SaveService.save_game()
	AudioService.play_sfx("reward")
	AnalyticsService.track("rewarded_granted", {"reward": reward})
	hud.hide_rewarded_button()
	hud.flash("+%d CREDITS" % reward)

func _on_purchase_succeeded(product_id: String) -> void:
	hud.flash("PURCHASE COMPLETE  •  %s" % product_id.replace("_", " ").to_upper())
	hud.refresh_menu()

func _on_purchase_failed(_product_id: String, reason: String) -> void:
	hud.flash("PURCHASE UNAVAILABLE  •  %s" % reason.replace("_", " ").to_upper())

# ---------------------------------------------------------------- ghost
func _ghost_shader_material() -> StandardMaterial3D:
	if _ghost_material == null:
		_ghost_material = StandardMaterial3D.new()
		_ghost_material.albedo_color = Color(0.35, 0.85, 1.0, 0.34)
		_ghost_material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		_ghost_material.emission_enabled = true
		_ghost_material.emission = Color(0.2, 0.8, 1.0)
		_ghost_material.emission_energy_multiplier = 2.0
		_ghost_material.cull_mode = BaseMaterial3D.CULL_DISABLED
	return _ghost_material

func _prepare_ghost() -> void:
	var ghost := GhostService.load_local_ghost()
	_ghost_samples = ghost.get("samples", [])
	if _ghost_samples.is_empty():
		return
	var model := ModelLibrary.instantiate("runner_base", false)
	if model == null:
		return
	_ghostify(model)
	ghost_root = Node3D.new()
	ghost_root.name = "GhostRunner"
	ghost_root.add_child(model)
	add_child(ghost_root)

func _ghostify(node: Node) -> void:
	for child in node.get_children():
		if child is MeshInstance3D:
			(child as MeshInstance3D).material_override = _ghost_shader_material()
		_ghostify(child)

func _destroy_ghost() -> void:
	if ghost_root != null and is_instance_valid(ghost_root):
		ghost_root.queue_free()
	ghost_root = null
	_ghost_samples = []

# ---------------------------------------------------------------- per frame
func _process(delta: float) -> void:
	if not running:
		return
	AppState.run_score = session.score.total()
	if ghost_root != null and is_instance_valid(ghost_root) and not _ghost_samples.is_empty():
		var p := GhostService.position_at_time(session.elapsed, _ghost_samples)
		ghost_root.position = Vector3(p.x, p.y, session.run_start_z + p.z)
		ghost_root.visible = session.elapsed <= GhostService.end_time(_ghost_samples) + 0.6
	hud.set_stats(AppState.run_distance, AppState.run_score, session.flow.flow, session.flow.multiplier)
	_hud_clock -= delta
	if _hud_clock > 0.0:
		return
	_hud_clock = 0.1
	hud.set_power(session.power.equipped, session.power.ready_fraction(), session.power.active, session.power.remaining)
	var fraction := 0.0
	var objective_text := ""
	if session.objective_kind != "endless":
		objective_text = GameModeService.objective_text()
		match session.objective_kind:
			"distance": fraction = AppState.run_distance / maxf(1.0, session.objective_target)
			"score": fraction = float(AppState.run_score) / maxf(1.0, session.objective_target)
			"collect": fraction = float(session.run_collectibles) / maxf(1.0, session.objective_target)
			"flow_stage": fraction = float(session.peak_flow_stage) / maxf(1.0, session.objective_target)
	hud.set_objective(objective_text, fraction)
