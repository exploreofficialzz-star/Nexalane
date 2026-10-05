extends Node
class_name AnalyticsServiceImpl

const QUEUE_PATH := "user://nexalane_analytics.jsonl"
const MAX_FILE_BYTES := 512 * 1024
const FLUSH_BATCH := 12

var enabled := true
var queue: Array[Dictionary] = []

func _ready() -> void:
	enabled = ConsentService.has_decision() and ConsentService.analytics_allowed()

func track(event_name: String, properties: Dictionary = {}) -> void:
	if not enabled or not ConsentService.analytics_allowed():
		return
	var event := {
		"event": event_name,
		"ts_ms": int(Time.get_unix_time_from_system() * 1000.0),
		"session_id": AppState.active_run_id,
		"content_version": AppState.CONTENT_VERSION,
		"properties": properties
	}
	queue.append(event)
	if queue.size() >= FLUSH_BATCH:
		flush()

func flush() -> void:
	if queue.is_empty():
		return
	var f := FileAccess.open(QUEUE_PATH, FileAccess.READ_WRITE)
	if f == null:
		f = FileAccess.open(QUEUE_PATH, FileAccess.WRITE)
	if f == null:
		queue.clear()   # never let an unwritable disk grow the in-memory queue without bound
		return
	if f.get_length() > MAX_FILE_BYTES:
		f.close()
		f = FileAccess.open(QUEUE_PATH, FileAccess.WRITE)   # rotate: no uploader drained it, drop the oldest data
		if f == null:
			queue.clear()
			return
	f.seek_end()
	for event in queue:
		f.store_line(JSON.stringify(event))
	f.close()
	queue.clear()

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_WM_CLOSE_REQUEST:
		flush()
