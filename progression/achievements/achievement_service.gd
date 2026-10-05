extends Node
class_name AchievementServiceImpl

signal achievement_unlocked(achievement_id: String, title: String)

const TITLES := {
	"first_run": "First Break",
	"distance_500": "Half-Kilometer",
	"distance_5000": "Long Haul",
	"score_5000": "Five Grand",
	"flow_stage_4": "Overdrive",
	"collect_100": "Collector",
	"story_complete": "The Relay"
}

func title(achievement_id: String) -> String:
	return str(TITLES.get(achievement_id, achievement_id))

func catalog() -> Dictionary:
	return TITLES.duplicate(true)

func grant(achievement_id: String, reward_credits: int = 250) -> void:
	if bool(SaveService.data["achievements"].get(achievement_id, false)):
		return
	SaveService.data["achievements"][achievement_id] = true
	EconomyService.grant("credits", reward_credits, "achievement")
	ProgressionService.add_xp(100, "achievement")
	AnalyticsService.track("achievement_unlocked", {"achievement_id": achievement_id, "title": title(achievement_id)})
	AudioService.play_sfx("reward")
	SaveService.save_game()
	achievement_unlocked.emit(achievement_id, title(achievement_id))
