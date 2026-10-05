extends RefCounted
class_name RunnerCatalog

static func all() -> Array[Dictionary]:
	var names := ["Kade","Nova","Juno","Riven","Mira","Sable","Ion","Taro","Lyra","Knox","Vee","Axel","Sana","Orin","Zara","Pax"]
	var roles := ["Balanced","Precision","Collector","Speed","Flow","Recovery","Vault","Magnet","Duelist","Route","Shield","Overdrive","Scout","Stamina","Risk","Elite"]
	var colors := [Color("#55d6ff"),Color("#ff6b9c"),Color("#f5c04a"),Color("#6bff8d"),Color("#bd8cff"),Color("#ff944d"),Color("#4ac0ff"),Color("#e8efff")]
	var result: Array[Dictionary] = []
	for i in names.size():
		result.append({"id": names[i], "role": roles[i], "description": "Relay runner %s — %s specialist." % [names[i], roles[i]], "color": colors[i % colors.size()], "ability": roles[i], "unlock_level": i + 1})
	return result

static func get_runner(runner_id: String) -> Dictionary:
	for runner in all():
		if runner["id"] == runner_id:
			return runner
	return all()[0]
