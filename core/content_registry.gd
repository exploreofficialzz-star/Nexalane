extends RefCounted
class_name ContentRegistry

static var _districts_cache: Array[Dictionary] = []
static var _challenges_cache: Array[Dictionary] = []
static var _cosmetics_cache: Array[Dictionary] = []

static func districts() -> Array[Dictionary]:
	if _districts_cache.is_empty():
		_districts_cache = _build_districts()
	return _districts_cache

static func district_by_id(district_id: String) -> Dictionary:
	for d in districts():
		if str(d["id"]) == district_id:
			return d
	return districts()[0]

static func district_by_name(district_name: String) -> Dictionary:
	for d in districts():
		if str(d["name"]) == district_name:
			return d
	return districts()[0]

## Palette keys: accent (neon), sky_top / sky_horizon (procedural sky), fog_color, sun (colour) + sun_energy.
static func _build_districts() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	result.append({"id":"old_quarter","name":"Old Quarter","accent":Color("#d47b4a"),"fog":0.0085,"weather":"dry","set_piece":"train_split",
		"sky_top":Color(0.03,0.05,0.11),"sky_horizon":Color(0.85,0.42,0.20),"fog_color":Color(0.14,0.11,0.14),"sun":Color(1.0,0.62,0.35),"sun_energy":0.95})
	result.append({"id":"transit_core","name":"Transit Core","accent":Color("#5cb8e7"),"fog":0.0105,"weather":"dry","set_piece":"station_surge",
		"sky_top":Color(0.02,0.05,0.12),"sky_horizon":Color(0.20,0.50,0.75),"fog_color":Color(0.06,0.11,0.18),"sun":Color(0.55,0.75,1.0),"sun_energy":0.85})
	result.append({"id":"harbor_arc","name":"Harbor Arc","accent":Color("#4c9bb0"),"fog":0.0115,"weather":"mist","set_piece":"bridge_sprint",
		"sky_top":Color(0.02,0.07,0.11),"sky_horizon":Color(0.28,0.62,0.66),"fog_color":Color(0.07,0.14,0.17),"sun":Color(0.70,0.90,1.0),"sun_energy":0.8})
	result.append({"id":"industrial_belt","name":"Industrial Belt","accent":Color("#c78c42"),"fog":0.0135,"weather":"steam","set_piece":"crane_swing",
		"sky_top":Color(0.05,0.05,0.07),"sky_horizon":Color(0.78,0.50,0.22),"fog_color":Color(0.15,0.11,0.08),"sun":Color(1.0,0.70,0.40),"sun_energy":0.85})
	result.append({"id":"skyline_works","name":"Skyline Works","accent":Color("#7b94d6"),"fog":0.0095,"weather":"clear","set_piece":"rooftop_collapse",
		"sky_top":Color(0.03,0.06,0.16),"sky_horizon":Color(0.38,0.48,0.82),"fog_color":Color(0.08,0.10,0.18),"sun":Color(0.65,0.72,1.0),"sun_energy":0.9})
	result.append({"id":"neon_market","name":"Neon Market","accent":Color("#cf64d9"),"fog":0.0125,"weather":"rain","set_piece":"drone_swarm",
		"sky_top":Color(0.06,0.03,0.12),"sky_horizon":Color(0.80,0.25,0.65),"fog_color":Color(0.12,0.06,0.16),"sun":Color(1.0,0.50,0.90),"sun_energy":0.8})
	result.append({"id":"stormline","name":"Stormline","accent":Color("#66a7c8"),"fog":0.0155,"weather":"storm","set_piece":"storm_surge",
		"sky_top":Color(0.03,0.04,0.06),"sky_horizon":Color(0.30,0.40,0.50),"fog_color":Color(0.08,0.10,0.13),"sun":Color(0.60,0.70,0.85),"sun_energy":0.55})
	result.append({"id":"central_spire","name":"Central Spire","accent":Color("#b8d9ff"),"fog":0.0075,"weather":"clear","set_piece":"spire_ascent",
		"sky_top":Color(0.04,0.09,0.20),"sky_horizon":Color(0.65,0.85,1.0),"fog_color":Color(0.14,0.20,0.30),"sun":Color(0.85,0.93,1.0),"sun_energy":1.0})
	return result

static func obstacle_families() -> Array[String]:
	var base := ["barrier","traffic","train","low_beam","gap","drone","gate","container","crane","steam","forklift","laser","wet_bridge","market_cart","scooter"]
	var result: Array[String] = []
	for i in 60:
		result.append("%s_%02d" % [base[i % base.size()], i + 1])
	return result

static func cosmetics(count: int = 24) -> Array[Dictionary]:
	if count == 24 and not _cosmetics_cache.is_empty():
		return _cosmetics_cache
	var result: Array[Dictionary] = []
	for i in count:
		var uses_nova := i >= 18
		result.append({
			"id": "outfit_%02d" % (i + 1),
			"name": "Relay Kit %02d" % (i + 1),
			"cost": (120 + (i - 18) * 60) if uses_nova else (500 + i * 250),
			"currency": "nova" if uses_nova else "credits",
			"color": Color.from_hsv(fposmod(0.06 + float(i) * 0.137, 1.0), 0.78, 1.0)
		})
	if count == 24:
		_cosmetics_cache = result
	return result

static func cosmetic_by_id(cosmetic_id: String) -> Dictionary:
	for item in cosmetics():
		if str(item["id"]) == cosmetic_id:
			return item
	return {}

static func challenges(count: int = 40) -> Array[Dictionary]:
	if count == 40 and not _challenges_cache.is_empty():
		return _challenges_cache
	var tiers := ["Beginner","Skilled","Expert","Master"]
	var result: Array[Dictionary] = []
	for i in count:
		var tier_index := mini(floori(float(i) / 10.0), 3)
		result.append({"id":"vault_%02d" % (i + 1), "tier":tiers[tier_index], "objective":"Reach %dm with modifier %d" % [200 + i * 15, i % 5], "target":200 + i * 15, "reward":300 + i * 75, "modifier":i % 5})
	if count == 40:
		_challenges_cache = result
	return result

static func achievements(count: int = 60) -> Array[Dictionary]:
	var groups := ["distance","collection","mastery","district","flow","social","seasonal"]
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"achievement_%02d" % (i + 1), "group":groups[i % groups.size()], "target":(i + 1) * 5})
	return result

static func boards(count: int = 12) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"board_%02d" % (i + 1), "name":"Route Board %02d" % (i + 1), "cost":750 + i * 200})
	return result

static func trails(count: int = 24) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"trail_%02d" % (i + 1), "name":"Flow Trail %02d" % (i + 1), "cost":350 + i * 90})
	return result

static func event_shop(count: int = 6) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"event_supply_%02d" % (i + 1), "name":"Pulse Supply %02d" % (i + 1), "cost":20 + i * 10, "reward_credits":250 + i * 100, "reward_nova":5 if i % 3 == 2 else 0})
	return result

static func badges(count: int = 36) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"badge_%02d" % (i + 1), "name":"Relay Badge %02d" % (i + 1), "category":["district","flow","social","mastery"][i % 4]})
	return result

static func event_themes(count: int = 12) -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for i in count:
		result.append({"id":"event_%02d" % (i + 1), "name":"City Pulse %02d" % (i + 1), "modifier":["Double Credits","Hyper Speed","Flow Frenzy","Hazard Storm"][i % 4]})
	return result

static func story() -> Array[Dictionary]:
	var chapters := ["First Break","Transit Core","Harbor Arc","Industrial Belt","Skyline Works","Neon Market","Stormline","Central Spire","The Hidden Route","Blackout","Gridwatch Pursuit","The Relay"]
	var result: Array[Dictionary] = []
	for i in chapters.size():
		var missions: Array[Dictionary] = []
		for m in 4:
			missions.append({"id":"chapter_%02d_mission_%02d" % [i + 1, m + 1], "objective":"Complete route objective %d" % (m + 1), "reward_credits":250 + m * 100})
		result.append({"id":"chapter_%02d" % (i + 1), "name":chapters[i], "missions":missions, "challenge":{"id":"chapter_%02d_challenge" % (i + 1), "score":2500 + i * 500}})
	return result
