extends Node
class_name FlowSystem

signal flow_changed(value: float, stage: int, multiplier: float)

const STAGE_MULTIPLIERS := [1.0, 1.25, 1.5, 2.0, 3.0]

var flow := 0.0
var stage := 0
var multiplier := 1.0
var _decay_scale := 1.0

## Call after AppState.mode has been set for the new run.
func reset() -> void:
	flow = 0.0
	stage = 0
	multiplier = 1.0
	_decay_scale = 1.0
	if AppState.mode == AppState.GameMode.EVENT and EventEngine.active_modifier == "Flow Frenzy":
		_decay_scale = 0.35
	elif AppState.mode == AppState.GameMode.CHALLENGE and int(ChallengeService.current().get("modifier", 0)) == 2:
		_decay_scale = 0.45
	AudioService.set_intensity(0.0)
	flow_changed.emit(flow, stage, multiplier)

func tick(delta: float, active: bool) -> void:
	if not active or flow <= 0.0:
		return
	var decay := RemoteConfigService.get_number("flow_decay_per_sec", 0.035) * _decay_scale
	flow = maxf(0.0, flow - decay * delta)
	_recalculate()

func add_precision(amount: float, reason: String) -> void:
	flow = clampf(flow + amount, 0.0, 1.0)
	AnalyticsService.track("flow_gain", {"amount": amount, "reason": reason, "stage": stage})
	_recalculate()

func break_flow(reason: String) -> void:
	flow = 0.0
	AnalyticsService.track("flow_break", {"reason": reason, "stage": stage})
	_recalculate()

func _recalculate() -> void:
	var old_stage := stage
	if flow < 0.20:
		stage = 0
	elif flow < 0.40:
		stage = 1
	elif flow < 0.60:
		stage = 2
	elif flow < 0.82:
		stage = 3
	else:
		stage = 4
	multiplier = float(STAGE_MULTIPLIERS[stage])
	if stage != old_stage:
		if stage >= 3 and stage > old_stage:
			MissionService.report("flow", 1.0)
		AudioService.set_intensity(float(stage) / 4.0)      # music layers follow the stage both up AND down
		flow_changed.emit(flow, stage, multiplier)
