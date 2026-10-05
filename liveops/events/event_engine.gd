extends Node
class_name EventEngineImpl

## Live-event rotation. The active theme changes at 00:00 UTC; modifiers implemented by the game:
## "Double Credits" (credit rewards x2), "Hyper Speed" (+4 m/s), "Flow Frenzy" (flow decays slower),
## "Hazard Storm" (denser, harder track and 1.5x credit rewards).

var active_event_id := "event_01"
var active_modifier := "Double Credits"
var end_timestamp := 0

func _ready() -> void:
	refresh_rotation()

func refresh_rotation() -> void:
	var now := int(Time.get_unix_time_from_system())
	var day_index := int(floor(float(now) / 86400.0))
	var themes := ContentRegistry.event_themes()
	var theme: Dictionary = themes[day_index % themes.size()]
	active_event_id = str(theme["id"])
	active_modifier = str(theme["modifier"])
	end_timestamp = (day_index + 1) * 86400

func configure(event_id: String, modifier: String, duration_seconds: int) -> void:
	active_event_id = event_id
	active_modifier = modifier
	end_timestamp = int(Time.get_unix_time_from_system()) + duration_seconds

func is_active() -> bool:
	return end_timestamp == 0 or Time.get_unix_time_from_system() < end_timestamp

func apply_reward(base_credits: int) -> int:
	if not is_active():
		return base_credits
	match active_modifier:
		"Double Credits": return base_credits * 2
		"Hazard Storm": return int(round(float(base_credits) * 1.5))
		_: return base_credits

## Extra difficulty (0..1 scale) the track generator adds while the event is live.
func difficulty_bonus() -> float:
	return 0.22 if is_active() and active_modifier == "Hazard Storm" else 0.0
