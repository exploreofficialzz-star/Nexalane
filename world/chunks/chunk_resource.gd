extends Resource
class_name TrackChunkDefinition

@export var chunk_id := "chunk_001"
@export var district_id := "old_quarter"
@export var length := 48.0
@export var risk := 0.20
@export var reward := 0.40
@export var route_class := "SAFE"
@export var difficulty_min := 0.0
@export var obstacle_count := 3
@export var collectible_count := 8
@export var set_piece := ""
@export var obstacle_family := "barrier_01"

func compatible(difficulty: float) -> bool:
	return difficulty >= difficulty_min - 0.10
