extends RefCounted
class_name ChunkRegistry

static func build(count: int = 84) -> Array[TrackChunkDefinition]:
	var routes := ["SAFE","FAST","REWARD","CHAOS","SECRET"]
	var districts := ContentRegistry.districts()
	var result: Array[TrackChunkDefinition] = []
	var obstacle_families := ContentRegistry.obstacle_families()
	for i in count:
		var d := districts[i % districts.size()]
		var c := TrackChunkDefinition.new()
		c.chunk_id = "chunk_%03d" % (i + 1)
		c.district_id = d["id"]
		c.length = 42.0 + float((i * 7) % 13)
		c.risk = 0.10 + float(i % 7) * 0.11
		c.reward = 0.25 + float((i * 3) % 8) * 0.10
		c.route_class = routes[i % routes.size()]
		c.difficulty_min = float(i % 12) / 12.0
		c.obstacle_count = 2 + i % 5
		c.collectible_count = 5 + i % 8
		c.set_piece = str(d["set_piece"]) if i % 12 == 11 else ""
		c.obstacle_family = obstacle_families[(i * 7) % obstacle_families.size()]
		result.append(c)
	return result
