extends Node

## Loads the QA harness after the project has initialized its autoload singletons.
func _ready() -> void:
	var harness_script := load("res://tests/qa_harness.gd")
	if harness_script == null:
		push_error("Unable to load QA harness")
		get_tree().quit(1)
		return
	var harness: Node = harness_script.new()
	# QA.tscn is still attaching its root node when this callback runs; defer the
	# harness attachment so the new node receives a valid scene tree.
	get_tree().root.call_deferred("add_child", harness)
	await get_tree().process_frame
	await harness._initialize()
