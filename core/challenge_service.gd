extends Node
class_name ChallengeServiceImpl

var selected_id := "vault_01"

func _ready() -> void:
	selected_id = str(SaveService.data.get("progression", {}).get("challenge", "vault_01"))

func select(id: String) -> void:
	for challenge in ContentRegistry.challenges():
		if str(challenge["id"]) == id:
			selected_id = id
			SaveService.data["progression"]["challenge"] = id
			SaveService.save_game()
			AnalyticsService.track("challenge_selected", {"challenge": id})
			return

func current() -> Dictionary:
	for challenge in ContentRegistry.challenges():
		if str(challenge["id"]) == selected_id:
			return challenge
	return ContentRegistry.challenges()[0]

func objective() -> Dictionary:
	var challenge := current()
	return {"kind": "distance", "target": float(challenge["target"]), "reward": int(challenge["reward"])}
