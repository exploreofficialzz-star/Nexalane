extends Node
class_name ScoreSystem

var distance_score := 0.0
var collectible_score := 0.0
var stunt_score := 0.0
var route_bonus := 0.0

func reset() -> void:
	distance_score = 0.0
	collectible_score = 0.0
	stunt_score = 0.0
	route_bonus = 0.0

func tick(delta: float, speed: float, flow_multiplier: float) -> int:
	distance_score += speed * delta * flow_multiplier
	return total()

func collect(value: int, flow_multiplier: float) -> void:
	collectible_score += float(value) * flow_multiplier

func stunt(value: float, flow_multiplier: float) -> void:
	stunt_score += value * flow_multiplier

func route(value: float, flow_multiplier: float) -> void:
	route_bonus += value * flow_multiplier

func total() -> int:
	return maxi(0, int(distance_score + collectible_score + stunt_score + route_bonus))
