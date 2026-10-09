extends Node
class_name BootTrailImpl

## Startup flight recorder + loading screen (autoload "BootTrail", loaded first).
##  * Every boot step is written to user://boot_trail.log (flushed per line) and printed with the prefix
##    [NEXALANE-BOOT], so `adb logcat -s godot` shows it. The previous launch's log is kept as
##    user://boot_trail_prev.log; if that launch never reached the READY mark the report says so.
##  * A dark loading screen covers the game until Main calls mark_ready(). If that has not happened after
##    WATCHDOG_SECONDS the screen turns into a report (device, GPU, renderer, steps, captured errors) with
##    COPY LOG / CLOSE buttons, so a startup failure can never be a silent blank screen again.
##  * On debug builds, engine and script errors are captured through Godot's Logger API (when the engine has
##    it) and a small ERR badge reopens the report at any time. Release builds hide GDScript runtime errors,
##    so use the debug APK from CI when you need them.
## Other scripts only reach this node through get_node_or_null("/root/BootTrail").call(...), so a problem in
## this file can never stop the game itself from loading.

const LOG_PATH := "user://boot_trail.log"
const PREV_PATH := "user://boot_trail_prev.log"
const READY_MARK := "##READY##"
const WATCHDOG_SECONDS := 8.0
const MAX_LINES := 200
const MAX_ERRORS := 60
const BG := Color(0.024, 0.04, 0.07, 1.0)
const CYAN := Color(0.18, 0.89, 1.0, 1.0)
const DIM := Color(0.56, 0.65, 0.74, 1.0)
const WARN := Color(1.0, 0.54, 0.24, 1.0)

## The signature of Logger._log_error differs between engine releases, so two variants are tried at runtime.
const LOGGER_SOURCES := [
	"extends Logger\nvar sink: Object = null\nfunc _log_error(function: String, file: String, line: int, code: String, rationale: String, editor_notify: bool, error_type: int, script_backtraces: Array[ScriptBacktrace]) -> void:\n\tif sink != null and is_instance_valid(sink):\n\t\tsink.call(\"capture_error\", error_type, file, line, function, code, rationale)\n",
	"extends Logger\nvar sink: Object = null\nfunc _log_error(function: String, file: String, line: int, code: String, rationale: String, editor_notify: bool, error_type: int) -> void:\n\tif sink != null and is_instance_valid(sink):\n\t\tsink.call(\"capture_error\", error_type, file, line, function, code, rationale)\n"
]

var lines := PackedStringArray()
var errors := PackedStringArray()
var error_count := 0
var ready_reported := false
var previous_incomplete := false
var previous_tail := ""

var _t0_ms := 0
var _file: FileAccess = null
var _mutex := Mutex.new()
var _logger: Object = null
var _canvas: CanvasLayer
var _loading_root: Control
var _loading_label: Label
var _report_root: Control
var _report_text: Label
var _copy_button: Button
var _badge: Button
var _dots_clock := 0.0
var _last_error_count := 0
var _report_open := false
var _report_auto := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_t0_ms = Time.get_ticks_msec()
	_load_previous_log()
	_file = FileAccess.open(LOG_PATH, FileAccess.WRITE)
	step("boot trail online")
	if previous_tail != "":
		step("previous launch reached READY: %s" % str(not previous_incomplete))
	for info_line in _system_info_lines():
		step(info_line)
	_install_logger()
	_build_overlay()
	RenderingServer.frame_post_draw.connect(_on_first_frame_drawn, CONNECT_ONE_SHOT)
	var timer := get_tree().create_timer(WATCHDOG_SECONDS, true)
	timer.timeout.connect(_on_watchdog)

func _on_first_frame_drawn() -> void:
	step("first frame drawn")

# ---------------------------------------------------------------- recording
func step(message: String) -> void:
	var entry := "%6.2f  %s" % [float(Time.get_ticks_msec() - _t0_ms) / 1000.0, message]
	print("[NEXALANE-BOOT] ", entry)
	_mutex.lock()
	lines.append(entry)
	if lines.size() > MAX_LINES:
		lines.remove_at(0)
	if _file != null:
		_file.store_line(entry)
		_file.flush()
	_mutex.unlock()

## Called by the Logger shim (possibly from another thread) - it must only touch data guarded by the mutex.
func capture_error(error_type: int, file: String, line: int, function: String, code: String, rationale: String) -> void:
	var kind := "ERROR"
	match error_type:
		1:
			kind = "WARNING"
		2:
			kind = "SCRIPT"
		3:
			kind = "SHADER"
	var detail := rationale if rationale != "" else code
	var entry := "[%s] %s  (%s:%d in %s)" % [kind, detail, file.get_file(), line, function]
	_mutex.lock()
	var is_repeat := errors.size() > 0 and errors[errors.size() - 1] == entry
	if not is_repeat and errors.size() < MAX_ERRORS:
		errors.append(entry)
		if _file != null:
			_file.store_line("      " + entry)
			_file.flush()
	if kind != "WARNING":
		error_count += 1
	_mutex.unlock()

func mark_ready() -> void:
	if ready_reported:
		return
	ready_reported = true
	step("%s game is interactive" % READY_MARK)
	if _loading_root != null:
		_loading_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_hide_loading()
	if _report_open and _report_auto:
		_close_report()
	_update_badge()

func report_text() -> String:
	var out := PackedStringArray()
	out.append("== NEXALANE startup report ==")
	_mutex.lock()
	if previous_incomplete:
		out.append("Previous launch did NOT finish starting. Its last steps:")
		out.append(previous_tail)
		out.append("")
	out.append("-- this launch --")
	out.append_array(lines)
	if errors.size() > 0:
		out.append("")
		out.append("-- engine errors captured (%d) --" % errors.size())
		out.append_array(errors)
	_mutex.unlock()
	if not OS.is_debug_build():
		out.append("")
		out.append("(release build: script runtime errors are not reported - install the debug APK to see them)")
	return "\n".join(out)

func show_report() -> void:
	_open_report(false)

# ---------------------------------------------------------------- environment
func _system_info_lines() -> PackedStringArray:
	var out := PackedStringArray()
	var version_info := Engine.get_version_info()
	out.append("engine: Godot %s" % str(version_info.get("string", "?")))
	var build_kind := "debug" if OS.is_debug_build() else "release"
	out.append("app: %s v%s (%s build)" % [str(ProjectSettings.get_setting("application/config/name", "?")), str(ProjectSettings.get_setting("application_metadata/product_version", "?")), build_kind])
	out.append("device: %s | %s %s" % [OS.get_model_name(), OS.get_name(), OS.get_version()])
	out.append("gpu: %s | %s" % [RenderingServer.get_video_adapter_name(), RenderingServer.get_video_adapter_vendor()])
	out.append("renderer: %s / %s" % [RenderingServer.get_current_rendering_method(), RenderingServer.get_current_rendering_driver_name()])
	out.append("screen: %s | window: %s" % [str(DisplayServer.screen_get_size()), str(DisplayServer.window_get_size())])
	return out

func _load_previous_log() -> void:
	previous_incomplete = false
	previous_tail = ""
	if not FileAccess.file_exists(LOG_PATH):
		return
	var f := FileAccess.open(LOG_PATH, FileAccess.READ)
	if f == null:
		return
	var text := f.get_as_text()
	f.close()
	if text.strip_edges() == "":
		return
	previous_incomplete = text.find(READY_MARK) == -1
	var all_lines := text.split("\n", false)
	var tail := PackedStringArray()
	for i in range(maxi(0, all_lines.size() - 14), all_lines.size()):
		tail.append(all_lines[i])
	previous_tail = "\n".join(tail)
	var keep := FileAccess.open(PREV_PATH, FileAccess.WRITE)
	if keep != null:
		keep.store_string(text)
		keep.close()

func _install_logger() -> void:
	if not ClassDB.class_exists("Logger") or not OS.has_method("add_logger"):
		step("logger: not available in this engine (errors are only in logcat)")
		return
	for source in LOGGER_SOURCES:
		var logger_script := GDScript.new()
		logger_script.source_code = str(source)
		if logger_script.reload() != OK:
			continue
		var instance: Object = logger_script.new()
		if instance == null:
			continue
		instance.set("sink", self)
		OS.call("add_logger", instance)
		_logger = instance
		step("logger: attached")
		return
	step("logger: could not attach")

# ---------------------------------------------------------------- overlay
func _full_rect(c: Control) -> void:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)

func _make_label(text_value: String, size_value: int, color: Color) -> Label:
	var l := Label.new()
	l.text = text_value
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	l.add_theme_font_size_override("font_size", size_value)
	l.add_theme_color_override("font_color", color)
	return l

func _make_button(text_value: String) -> Button:
	var b := Button.new()
	b.text = text_value
	b.custom_minimum_size = Vector2(0, 96)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	b.add_theme_font_size_override("font_size", 30)
	return b

func _build_overlay() -> void:
	_canvas = CanvasLayer.new()
	_canvas.name = "BootTrailLayer"
	_canvas.layer = 128
	add_child(_canvas)
	# --- loading screen
	_loading_root = Control.new()
	_loading_root.name = "Loading"
	_full_rect(_loading_root)
	_loading_root.mouse_filter = Control.MOUSE_FILTER_STOP
	_canvas.add_child(_loading_root)
	var bg := ColorRect.new()
	bg.color = BG
	_full_rect(bg)
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_loading_root.add_child(bg)
	var center := CenterContainer.new()
	_full_rect(center)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_loading_root.add_child(center)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 18)
	center.add_child(box)
	box.add_child(_make_label("NEXALANE", 84, CYAN))
	_loading_label = _make_label("Loading", 30, DIM)
	box.add_child(_loading_label)
	if previous_incomplete:
		box.add_child(_make_label("The last launch did not finish starting.", 22, WARN))
	# --- report screen
	_report_root = Control.new()
	_report_root.name = "Report"
	_full_rect(_report_root)
	_report_root.visible = false
	_canvas.add_child(_report_root)
	var report_bg := ColorRect.new()
	report_bg.color = BG
	_full_rect(report_bg)
	_report_root.add_child(report_bg)
	var margin := MarginContainer.new()
	_full_rect(margin)
	margin.add_theme_constant_override("margin_left", 32)
	margin.add_theme_constant_override("margin_right", 32)
	margin.add_theme_constant_override("margin_top", 64)
	margin.add_theme_constant_override("margin_bottom", 48)
	_report_root.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	margin.add_child(column)
	column.add_child(_make_label("STARTUP REPORT", 46, CYAN))
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(scroll)
	_report_text = Label.new()
	_report_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_report_text.autowrap_mode = TextServer.AUTOWRAP_ARBITRARY
	_report_text.add_theme_font_size_override("font_size", 22)
	scroll.add_child(_report_text)
	var buttons := HBoxContainer.new()
	buttons.add_theme_constant_override("separation", 16)
	column.add_child(buttons)
	_copy_button = _make_button("COPY LOG")
	_copy_button.pressed.connect(_on_copy_pressed)
	buttons.add_child(_copy_button)
	var close_button := _make_button("CLOSE")
	close_button.pressed.connect(_close_report)
	buttons.add_child(close_button)
	# --- error badge (debug builds only, shown after the game is up)
	_badge = Button.new()
	_badge.text = "ERR"
	_badge.visible = false
	_badge.position = Vector2(465.0, 14.0)
	_badge.custom_minimum_size = Vector2(150, 64)
	_badge.add_theme_font_size_override("font_size", 24)
	_badge.pressed.connect(show_report)
	_canvas.add_child(_badge)

func _hide_loading() -> void:
	if _loading_root == null:
		return
	var tween := create_tween()
	tween.tween_property(_loading_root, "modulate:a", 0.0, 0.35)
	tween.tween_callback(_finish_hide)
	get_tree().create_timer(0.8, true).timeout.connect(_finish_hide)

func _finish_hide() -> void:
	if _loading_root != null:
		_loading_root.visible = false

func _open_report(auto_opened: bool) -> void:
	if _report_root == null:
		return
	_report_open = true
	_report_auto = auto_opened
	_report_text.text = report_text()
	_copy_button.text = "COPY LOG"
	_report_root.visible = true

func _close_report() -> void:
	_report_open = false
	_report_auto = false
	if _report_root != null:
		_report_root.visible = false
	if not ready_reported and _loading_root != null:
		_loading_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_loading_root.visible = false

func _on_copy_pressed() -> void:
	DisplayServer.clipboard_set(report_text())
	_copy_button.text = "COPIED"
	step("report copied to clipboard")

func _on_watchdog() -> void:
	if ready_reported:
		return
	step("watchdog: startup not finished after %.0f s" % WATCHDOG_SECONDS)
	_open_report(true)

func _update_badge() -> void:
	if _badge == null:
		return
	_badge.visible = ready_reported and error_count > 0 and OS.is_debug_build()
	_badge.text = "ERR %d" % error_count

func _process(delta: float) -> void:
	if not ready_reported and _loading_root != null and _loading_root.visible:
		_dots_clock += delta
		_loading_label.text = "Loading" + ".".repeat(int(_dots_clock * 2.0) % 4)
	if error_count != _last_error_count:
		_last_error_count = error_count
		_update_badge()
