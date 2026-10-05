extends Node
class_name MissionServiceImpl

signal mission_completed(mission_id: String)

var active: Array[Dictionary] = []
var active_day_key := ""
var _next_day_check_ms := 0

func _ready() -> void:
	_refresh()

func _refresh() -> void:
	active.clear()
	var today := GameModeService.daily_key()
	active_day_key = today
	if str(SaveService.data["missions"].get("date_key", "")) != today:
		SaveService.data["missions"] = {"date_key": today}
	active.append(_mission("daily_distance", "distance", 750.0, 400))
	active.append(_mission("daily_flow", "flow", 3.0, 500))
	active.append(_mission("daily_collect", "collect", 80.0, 450))
	active.append(_mission("daily_route", "route", 3.0, 600))

func _mission(id: String, kind: String, target: float, reward: int) -> Dictionary:
	return {"id": id, "type": kind, "target": target, "progress": float(SaveService.data["missions"].get(id + "_progress", 0.0)), "reward": reward}

## event_type: "distance" (metres), "flow" (stage-3+ reached), "collect" (orbs picked up), "route" (routes chosen).
func report(event_type: String, amount: float) -> void:
	var now_ms := Time.get_ticks_msec()
	if now_ms >= _next_day_check_ms:                       # the date only needs checking about once a second
		_next_day_check_ms = now_ms + 1000
		if GameModeService.daily_key() != active_day_key:
			_refresh()
	for mission in active:
		if mission["type"] != event_type or float(mission["progress"]) >= float(mission["target"]):
			continue
		mission["progress"] = minf(float(mission["target"]), float(mission["progress"]) + amount)
		SaveService.data["missions"][str(mission["id"]) + "_progress"] = mission["progress"]
		if float(mission["progress"]) >= float(mission["target"]):
			_claim(mission)

func _claim(mission: Dictionary) -> void:
	var id := str(mission["id"])
	if bool(SaveService.data["missions"].get(id, false)):
		return
	SaveService.data["missions"][id] = true
	SaveService.data["missions"][id + "_progress"] = mission["progress"]
	EconomyService.grant("credits", int(mission["reward"]), "mission")
	ProgressionService.add_xp(150, "mission")
	AnalyticsService.track("mission_complete", {"mission_id": id})
	AudioService.play_sfx("reward")
	SaveService.save_game()
	mission_completed.emit(id)
