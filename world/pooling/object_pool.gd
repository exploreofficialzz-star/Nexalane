extends Node
class_name ObjectPool

var inactive: Array[Node] = []

func acquire(factory: Callable) -> Node:
	while not inactive.is_empty():
		var node: Node = inactive.pop_back()
		if is_instance_valid(node):
			return node
	return factory.call() as Node

func release(node: Node, pool_root: Node) -> void:
	if node == null or not is_instance_valid(node):
		return
	var parent := node.get_parent()
	if parent != null:
		parent.remove_child(node)
	pool_root.add_child(node)
	inactive.append(node)

func clear() -> void:
	for node in inactive:
		if is_instance_valid(node):
			node.queue_free()
	inactive.clear()
