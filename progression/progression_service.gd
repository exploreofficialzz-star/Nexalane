extends Node
class_name ProgressionServiceImpl

signal level_up(new_level: int)

const XP_PER_LEVEL := 500

func _ready() -> void:
	_unlock_runners_for_level(int(SaveService.data["profile"].get("level", 1)))

func add_xp(amount: int, source: String = "") -> void:
	if amount <= 0:
		return
	var profile: Dictionary = SaveService.data["profile"]
	var old_level := int(profile.get("level", 1))
	profile["xp"] = int(profile.get("xp", 0)) + amount
	var new_level := 1 + int(floor(float(profile["xp"]) / float(XP_PER_LEVEL)))
	profile["level"] = new_level
	if new_level > old_level:
		_unlock_runners_for_level(new_level)
		level_up.emit(new_level)
		AnalyticsService.track("progression_level_up", {"level": new_level})
	AnalyticsService.track("xp_earned", {"amount": amount, "source": source})

func runner_unlock_level(runner_id: String) -> int:
	var index := 0
	for runner in RunnerCatalog.all():
		if str(runner["id"]) == runner_id:
			return index + 1
		index += 1
	return 999

func is_runner_unlocked(runner_id: String) -> bool:
	if bool(SaveService.data["inventory"]["runners"].get(runner_id, false)):
		return true
	return int(SaveService.data["profile"].get("level", 1)) >= runner_unlock_level(runner_id)

func _unlock_runners_for_level(level: int) -> void:
	var changed := false
	for runner in RunnerCatalog.all():
		var runner_id := str(runner["id"])
		var required := runner_unlock_level(runner_id)
		if required <= level and not bool(SaveService.data["inventory"]["runners"].get(runner_id, false)):
			SaveService.data["inventory"]["runners"][runner_id] = true
			changed = true
			AnalyticsService.track("runner_unlocked", {"runner": runner_id, "level": level})
	if changed:
		SaveService.save_game()

func set_selected_runner(runner_id: String) -> void:
	if not is_runner_unlocked(runner_id):
		return
	for runner in RunnerCatalog.all():
		if str(runner["id"]) != runner_id:
			continue
		SaveService.data["profile"]["selected_runner"] = runner_id
		AppState.selected_runner = runner_id
		SaveService.save_game()
		AnalyticsService.track("runner_selected", {"runner": runner_id})
		return

func set_equipped_power(power_id: String) -> void:
	var valid := ["phase_shield", "magnet", "overdrive", "time_warp", "route_scanner", "double_credits", "recovery_pulse", "flow_surge"]
	if power_id not in valid:
		return
	SaveService.data["profile"]["equipped_power"] = power_id
	SaveService.save_game()
	AnalyticsService.track("power_equipped", {"power": power_id})

func mastery_level(runner_id: String) -> int:
	return int(SaveService.data["progression"]["runner_mastery"].get(runner_id, 1))

func add_mastery(runner_id: String, amount: int) -> void:
	var old := mastery_level(runner_id)
	var next_level := clampi(old + amount, 1, 20)
	SaveService.data["progression"]["runner_mastery"][runner_id] = next_level
	if next_level != old:
		AnalyticsService.track("runner_mastery_up", {"runner": runner_id, "level": next_level})
	SaveService.save_game()
