extends Node
class_name LiveOpsServiceImpl

var season_id := "season_01"
var season_xp := 0
var active_event := "city_pulse"
var xp_remainder := 0.0

func _ready() -> void:
	season_id = RemoteConfigService.get_string("season_id", "season_01")
	var season: Dictionary = SaveService.data["season"]
	if str(season.get("id", "")) != season_id:           # a new season starts from zero (and the pass is re-purchasable)
		season["id"] = season_id
		season["xp"] = 0
		season["claimed"] = []
		season["pass"] = false
		SaveService.data["owned_products"].erase("season_pass_999")
		SaveService.save_game()
	season_xp = int(season.get("xp", 0))

func add_season_xp(amount: int) -> void:
	season_xp = maxi(0, season_xp + amount)
	SaveService.data["season"]["xp"] = season_xp

func add_season_xp_fractional(amount: float) -> void:
	if amount <= 0.0:
		return
	xp_remainder += amount
	var whole := int(floor(xp_remainder))
	if whole <= 0:
		return
	xp_remainder -= float(whole)
	add_season_xp(whole)

## The live-event modifier is owned by EventEngine (it rotates daily, UTC).
func current_event_modifier() -> String:
	return EventEngine.active_modifier
