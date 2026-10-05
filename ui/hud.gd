extends CanvasLayer
class_name GameHUD

## Portrait HUD built entirely from containers (no hard-coded positions), so it adapts to any aspect ratio and
## to phone notches (safe area). Layers, back to front: menu, run HUD, results, detail sheet, pause, revive,
## modal (consent / tutorial), toast + banner, countdown, fade.

signal start_requested
signal power_requested
signal pause_requested
signal resume_requested
signal quit_to_menu_requested
signal rewarded_requested
signal revive_requested
signal end_run_requested
signal home_requested

const MODES := ["ENDLESS", "STORY", "DAILY", "WEEKLY", "EVENT", "TRAINING", "GHOST", "CHALLENGE"]
const POWER_IDS := ["phase_shield", "magnet", "overdrive", "time_warp", "route_scanner", "double_credits", "recovery_pulse", "flow_surge"]
const STAT_INTERVAL := 0.08

var root: Control
var menu_layer: Control
var run_layer: Control
var end_layer: Control
var detail_layer: Control
var pause_layer: Control
var revive_layer: Control
var modal_layer: Control
var fade_rect: ColorRect
var countdown_label: Label
var toast_panel: PanelContainer
var toast_label: Label
var banner_label: Label

var score_label: Label
var distance_label: Label
var flow_label: Label
var flow_bar: ProgressBar
var district_label: Label
var objective_label: Label
var objective_bar: ProgressBar
var pause_button: Button
var power_button: Button
var power_cool: ProgressBar
var bottom_row: HBoxContainer

var currency_credits: Label
var currency_nova: Label
var level_label: Label
var mode_info: Label
var mode_title: Label
var best_label: Label
var start_button: Button
var mode_buttons: Dictionary = {}

var detail_title: Label
var detail_content: VBoxContainer
var end_content: VBoxContainer
var rewarded_button: Button
var revive_time_label: Label
var revive_button: Button
var resume_button: Button

var _safe_containers: Array[MarginContainer] = []
var _stat_clock := 0.0
var _pending_stats := {"distance": 0.0, "score": 0, "flow": 0.0, "multiplier": 1.0}
var _last_flow_stage := -1
var _toast_tween: Tween
var _banner_tween: Tween
var _detail_section := ""

func _ready() -> void:
	layer = 8
	root = Control.new()
	root.name = "UIRoot"
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.theme = UITheme.get_theme()
	add_child(root)
	_build_menu_layer()
	_build_run_layer()
	_build_end_layer()
	_build_detail_layer()
	_build_pause_layer()
	_build_revive_layer()
	_build_modal_layer()
	_build_toast_and_banner()
	_build_fade_and_countdown()
	get_viewport().size_changed.connect(_apply_layout)
	_apply_layout()
	AccessibilityService.settings_changed.connect(_on_settings_changed)
	_on_settings_changed()
	set_run_visible(false)
	refresh_menu()
	_maybe_show_consent()
	fade_in_now()

# ---------------------------------------------------------------- layout helpers
func _full_rect(c: Control) -> void:
	c.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	c.mouse_filter = Control.MOUSE_FILTER_IGNORE

func _safe_margin(parent: Control) -> MarginContainer:
	var m := MarginContainer.new()
	_full_rect(m)
	parent.add_child(m)
	_safe_containers.append(m)
	return m

func _apply_layout() -> void:
	var viewport_size := get_viewport().get_visible_rect().size
	var extra_x := maxf(0.0, (viewport_size.x - 1080.0) * 0.5)
	var insets := _safe_insets()
	for m in _safe_containers:
		m.add_theme_constant_override("margin_left", int(26.0 + extra_x + insets.x))
		m.add_theme_constant_override("margin_right", int(26.0 + extra_x + insets.z))
		m.add_theme_constant_override("margin_top", int(22.0 + insets.y))
		m.add_theme_constant_override("margin_bottom", int(26.0 + insets.w))

## Safe-area insets (left, top, right, bottom) in UI units. Only meaningful on phones with notches / gesture bars.
func _safe_insets() -> Vector4:
	if not OS.has_feature("mobile"):
		return Vector4.ZERO
	var window := Vector2(DisplayServer.window_get_size())
	if window.x <= 0.0 or window.y <= 0.0:
		return Vector4.ZERO
	var viewport_size := get_viewport().get_visible_rect().size
	var safe := Rect2(DisplayServer.get_display_safe_area())
	var sx := viewport_size.x / window.x
	var sy := viewport_size.y / window.y
	return Vector4(safe.position.x * sx, safe.position.y * sy, maxf(0.0, window.x - safe.end.x) * sx, maxf(0.0, window.y - safe.end.y) * sy)

func _dim(alpha: float = 0.72) -> ColorRect:
	var d := ColorRect.new()
	d.color = Color(0.01, 0.02, 0.04, alpha)
	d.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	d.mouse_filter = Control.MOUSE_FILTER_STOP
	return d

func _center_card(layer_node: Control, card_width: float = 900.0) -> VBoxContainer:
	var center := CenterContainer.new()
	_full_rect(center)
	layer_node.add_child(center)
	var card := UITheme.panel()
	card.custom_minimum_size = Vector2(card_width, 0)
	center.add_child(card)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 16)
	card.add_child(content)
	return content

# ---------------------------------------------------------------- menu
func _build_menu_layer() -> void:
	menu_layer = Control.new()
	menu_layer.name = "Menu"
	_full_rect(menu_layer)
	root.add_child(menu_layer)
	var top_shade := UITheme.gradient_rect(Color(0, 0.02, 0.05, 0.82), Color(0, 0.02, 0.05, 0.0))
	top_shade.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	top_shade.custom_minimum_size = Vector2(0, 520)
	top_shade.offset_bottom = 520
	menu_layer.add_child(top_shade)
	var bottom_shade := UITheme.gradient_rect(Color(0, 0.02, 0.05, 0.0), Color(0, 0.02, 0.05, 0.92))
	bottom_shade.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	bottom_shade.offset_top = -900
	menu_layer.add_child(bottom_shade)
	var safe := _safe_margin(menu_layer)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	safe.add_child(column)
	# --- top bar: currencies + level
	var top_bar := HBoxContainer.new()
	top_bar.add_theme_constant_override("separation", 14)
	column.add_child(top_bar)
	top_bar.add_child(_currency_chip("icon_credit", true))
	top_bar.add_child(_currency_chip("icon_nova", false))
	top_bar.add_child(UITheme.spacer())
	var level_chip := UITheme.panel(UITheme.box(Color(0.04, 0.08, 0.14, 0.9), Color(UITheme.ORANGE.r, UITheme.ORANGE.g, UITheme.ORANGE.b, 0.8), 2, 22, 20.0, 8.0))
	level_label = UITheme.label("LV 1", 26, UITheme.ORANGE, true)
	level_chip.add_child(level_label)
	top_bar.add_child(level_chip)
	# --- logo
	var logo := TextureRect.new()
	logo.texture = load("res://assets/ui/ui_logo.png") as Texture2D
	logo.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	logo.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	logo.custom_minimum_size = Vector2(0, 250)
	logo.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(logo)
	column.add_child(UITheme.spacer(true))
	# --- mode selector
	mode_title = UITheme.label("ENDLESS", 40, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER)
	column.add_child(mode_title)
	mode_info = UITheme.label("", 21, UITheme.TEXT_DIM, false, HORIZONTAL_ALIGNMENT_CENTER)
	mode_info.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	mode_info.custom_minimum_size = Vector2(0, 60)
	column.add_child(mode_info)
	var scroll := ScrollContainer.new()
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	scroll.custom_minimum_size = Vector2(0, 84)
	column.add_child(scroll)
	var chips := HBoxContainer.new()
	chips.add_theme_constant_override("separation", 10)
	scroll.add_child(chips)
	for mode_name in MODES:
		var chip := UITheme.button(mode_name, UITheme.CYAN, false, Vector2(190, 66))
		chip.add_theme_font_size_override("font_size", 22)
		chip.pressed.connect(_select_mode.bind(mode_name))
		mode_buttons[mode_name] = chip
		chips.add_child(chip)
	# --- start
	start_button = UITheme.button("START RUN", UITheme.CYAN, true, Vector2(0, 118))
	start_button.add_theme_font_size_override("font_size", 40)
	start_button.pressed.connect(_on_start_pressed)
	column.add_child(start_button)
	best_label = UITheme.label("", 22, UITheme.TEXT_DIM, false, HORIZONTAL_ALIGNMENT_CENTER)
	column.add_child(best_label)
	# --- nav bar
	var nav := HBoxContainer.new()
	nav.add_theme_constant_override("separation", 8)
	column.add_child(nav)
	for entry in [["GARAGE", "icon_garage", "garage"], ["MISSIONS", "icon_missions", "missions"], ["SHOP", "icon_shop", "shop"], ["SEASON", "icon_season", "season"], ["TROPHIES", "icon_achievements", "achievements"], ["RANKS", "icon_leaders", "leaderboards"], ["SETTINGS", "icon_settings", "settings"]]:
		nav.add_child(_nav_item(str(entry[0]), str(entry[1]), str(entry[2])))

func _currency_chip(icon_name: String, credits: bool) -> PanelContainer:
	var chip := UITheme.panel(UITheme.box(Color(0.04, 0.08, 0.14, 0.9), Color(1, 1, 1, 0.14), 2, 22, 14.0, 6.0))
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	chip.add_child(row)
	row.add_child(UITheme.icon_rect(icon_name, 46.0))
	var l := UITheme.label("0", 28, UITheme.GOLD if credits else UITheme.CYAN, true)
	row.add_child(l)
	if credits:
		currency_credits = l
	else:
		currency_nova = l
	return chip

func _nav_item(text_value: String, icon_name: String, section: String) -> Button:
	var b := Button.new()
	b.custom_minimum_size = Vector2(0, 112)
	b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	UITheme.style_button(b, UITheme.VIOLET, false, 20)
	b.pressed.connect(UITheme._on_button_pressed)
	b.pressed.connect(_open_detail.bind(section))
	var col := VBoxContainer.new()
	col.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.add_theme_constant_override("separation", 4)
	col.mouse_filter = Control.MOUSE_FILTER_IGNORE
	b.add_child(col)
	var icon_node := UITheme.icon_rect(icon_name, 46.0)
	icon_node.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	col.add_child(icon_node)
	var caption := UITheme.label(text_value, 15, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER)
	col.add_child(caption)
	return b

func refresh_menu() -> void:
	if currency_credits == null:
		return
	currency_credits.text = _format_number(EconomyService.balance("credits"))
	currency_nova.text = _format_number(EconomyService.balance("nova"))
	level_label.text = "LV %d" % int(SaveService.data["profile"].get("level", 1))
	best_label.text = "BEST  %s   •   %.0f m" % [_format_number(int(SaveService.data.get("best_score", 0))), float(SaveService.data.get("best_distance", 0.0))]
	_refresh_mode_ui()

func _format_number(value: int) -> String:
	var s := str(absi(value))
	var out := ""
	var count := 0
	for i in range(s.length() - 1, -1, -1):
		out = s[i] + out
		count += 1
		if count % 3 == 0 and i > 0:
			out = "," + out
	return ("-" if value < 0 else "") + out

func _select_mode(mode_name: String) -> void:
	GameModeService.set_mode(mode_name)
	AppState.selected_mode = GameModeService.selected_mode
	_refresh_mode_ui()

func _refresh_mode_ui() -> void:
	var selected := GameModeService.selected_mode
	mode_title.text = GameModeService.mode_label()
	match selected:
		"STORY": mode_info.text = "Chapter %02d  •  %s" % [GameModeService.selected_story_chapter, GameModeService.objective_text()]
		"DAILY": mode_info.text = "One shared route for everyone today (UTC)  •  reach 1800 m  •  +25 NOVA on completion"
		"WEEKLY": mode_info.text = "This week's route  •  reach 4000 m  •  +60 NOVA on completion"
		"EVENT": mode_info.text = "Limited-time modifier: %s  •  reach 2500 m" % EventEngine.active_modifier
		"TRAINING": mode_info.text = "Easy practice route  •  900 m  •  learn the moves"
		"GHOST": mode_info.text = "Race your last run on the same route." if GhostService.has_local_ghost() else "Finish one run first - then you can race it here."
		"CHALLENGE":
			var challenge := ChallengeService.current()
			mode_info.text = "%s  •  %dm  •  modifier %d" % [str(challenge["id"]).to_upper(), int(challenge["target"]), int(challenge["modifier"])]
		_: mode_info.text = "Run as far as you can. Build flow for score multipliers."
	for mode_name in mode_buttons.keys():
		var b: Button = mode_buttons[mode_name]
		UITheme.style_button(b, UITheme.ORANGE if mode_name == selected else UITheme.CYAN, mode_name == selected)
		b.add_theme_font_size_override("font_size", 22)

func _on_start_pressed() -> void:
	AudioService.play_sfx("ui_confirm")
	start_requested.emit()

# ---------------------------------------------------------------- run HUD
func _build_run_layer() -> void:
	run_layer = Control.new()
	run_layer.name = "RunHUD"
	_full_rect(run_layer)
	root.add_child(run_layer)
	var safe := _safe_margin(run_layer)
	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation", 10)
	safe.add_child(column)
	var top := HBoxContainer.new()
	top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_child(top)
	var left := VBoxContainer.new()
	left.mouse_filter = Control.MOUSE_FILTER_IGNORE
	left.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left.add_theme_constant_override("separation", 2)
	top.add_child(left)
	score_label = UITheme.label("0", 72, UITheme.TEXT, true)
	score_label.add_theme_constant_override("shadow_offset_x", 3)
	score_label.add_theme_constant_override("shadow_offset_y", 3)
	left.add_child(score_label)
	distance_label = UITheme.label("0 m", 30, UITheme.TEXT_DIM, true)
	left.add_child(distance_label)
	var flow_row := HBoxContainer.new()
	flow_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flow_row.add_theme_constant_override("separation", 12)
	left.add_child(flow_row)
	flow_bar = ProgressBar.new()
	flow_bar.show_percentage = false
	flow_bar.max_value = 1.0
	flow_bar.step = 0.001
	flow_bar.custom_minimum_size = Vector2(300, 20)
	flow_bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	flow_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	flow_row.add_child(flow_bar)
	flow_label = UITheme.label("FLOW x1.0", 24, UITheme.CYAN, true)
	flow_row.add_child(flow_label)
	var right := VBoxContainer.new()
	right.mouse_filter = Control.MOUSE_FILTER_IGNORE
	right.add_theme_constant_override("separation", 6)
	top.add_child(right)
	pause_button = UITheme.button("", UITheme.SLATE, false, Vector2(96, 96))
	var pause_icon := UITheme.icon_rect("icon_pause", 44.0)
	pause_icon.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	pause_icon.pivot_offset = Vector2(22, 22)
	pause_icon.position = Vector2(26, 26)
	pause_button.add_child(pause_icon)
	pause_button.pressed.connect(func() -> void: pause_requested.emit())
	right.add_child(pause_button)
	district_label = UITheme.label("", 20, UITheme.ORANGE, true, HORIZONTAL_ALIGNMENT_RIGHT)
	right.add_child(district_label)
	var obj_row := VBoxContainer.new()
	obj_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	obj_row.add_theme_constant_override("separation", 4)
	column.add_child(obj_row)
	objective_label = UITheme.label("", 22, UITheme.TEXT, true)
	obj_row.add_child(objective_label)
	objective_bar = ProgressBar.new()
	objective_bar.show_percentage = false
	objective_bar.max_value = 1.0
	objective_bar.step = 0.001
	objective_bar.custom_minimum_size = Vector2(0, 10)
	objective_bar.mouse_filter = Control.MOUSE_FILTER_IGNORE
	objective_bar.add_theme_stylebox_override("fill", UITheme.box(UITheme.ORANGE, Color(0, 0, 0, 0), 0, 8, 0.0, 0.0))
	obj_row.add_child(objective_bar)
	column.add_child(UITheme.spacer(true))
	bottom_row = HBoxContainer.new()
	bottom_row.mouse_filter = Control.MOUSE_FILTER_IGNORE
	bottom_row.alignment = BoxContainer.ALIGNMENT_END
	column.add_child(bottom_row)
	var power_box := VBoxContainer.new()
	power_box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	power_box.add_theme_constant_override("separation", 8)
	bottom_row.add_child(power_box)
	power_button = Button.new()
	power_button.custom_minimum_size = Vector2(200, 200)
	_style_power_button(UITheme.MAGENTA)
	power_button.text = "SHIELD"
	power_button.pressed.connect(func() -> void: power_requested.emit())
	power_box.add_child(power_button)
	power_cool = ProgressBar.new()
	power_cool.show_percentage = false
	power_cool.max_value = 1.0
	power_cool.step = 0.001
	power_cool.custom_minimum_size = Vector2(200, 12)
	power_cool.mouse_filter = Control.MOUSE_FILTER_IGNORE
	power_cool.add_theme_stylebox_override("fill", UITheme.box(UITheme.MAGENTA, Color(0, 0, 0, 0), 0, 8, 0.0, 0.0))
	power_box.add_child(power_cool)

func _style_power_button(accent: Color) -> void:
	var make := func(bg: Color, border: Color) -> StyleBoxFlat:
		var sb := UITheme.box(bg, border, 4, 100, 10.0, 10.0)
		sb.shadow_color = Color(accent.r, accent.g, accent.b, 0.4)
		sb.shadow_size = 18
		return sb
	power_button.add_theme_stylebox_override("normal", make.call(Color(0.06, 0.04, 0.12, 0.92), accent))
	power_button.add_theme_stylebox_override("hover", make.call(Color(0.12, 0.06, 0.2, 0.95), accent.lightened(0.2)))
	power_button.add_theme_stylebox_override("pressed", make.call(Color(accent.r, accent.g, accent.b, 0.5), Color.WHITE))
	power_button.add_theme_stylebox_override("disabled", UITheme.box(Color(0.04, 0.05, 0.08, 0.8), Color(1, 1, 1, 0.18), 4, 100, 10.0, 10.0))
	power_button.add_theme_font_override("font", UITheme.bold())
	power_button.add_theme_font_size_override("font_size", 24)
	power_button.add_theme_color_override("font_color", UITheme.TEXT)
	power_button.add_theme_color_override("font_disabled_color", Color(1, 1, 1, 0.45))
	power_button.focus_mode = Control.FOCUS_NONE

func _on_settings_changed() -> void:
	if bottom_row != null:
		bottom_row.alignment = BoxContainer.ALIGNMENT_BEGIN if AccessibilityService.is_enabled("left_handed") else BoxContainer.ALIGNMENT_END

func set_run_visible(active: bool) -> void:
	run_layer.visible = active
	menu_layer.visible = not active
	detail_layer.visible = false
	end_layer.visible = false
	pause_layer.visible = false
	revive_layer.visible = false
	if active:
		toast_panel.visible = false
		_last_flow_stage = -1
	else:
		refresh_menu()

func set_stats(distance: float, score: int, flow: float, multiplier: float) -> void:
	_pending_stats["distance"] = distance
	_pending_stats["score"] = score
	_pending_stats["flow"] = flow
	_pending_stats["multiplier"] = multiplier
	flow_bar.value = flow

func _process(delta: float) -> void:
	if not run_layer.visible:
		return
	_stat_clock -= delta
	if _stat_clock > 0.0:
		return
	_stat_clock = STAT_INTERVAL
	score_label.text = _format_number(int(_pending_stats["score"]))
	distance_label.text = "%d m" % int(_pending_stats["distance"])
	var multiplier := float(_pending_stats["multiplier"])
	flow_label.text = "FLOW x%.2f" % multiplier
	var stage := 0
	if multiplier >= 3.0:
		stage = 4
	elif multiplier >= 2.0:
		stage = 3
	elif multiplier >= 1.5:
		stage = 2
	elif multiplier >= 1.25:
		stage = 1
	if stage != _last_flow_stage:
		_last_flow_stage = stage
		var colors := [UITheme.CYAN, UITheme.CYAN, UITheme.GREEN, UITheme.MAGENTA, UITheme.ORANGE]
		flow_bar.add_theme_stylebox_override("fill", UITheme.box(colors[stage], Color(0, 0, 0, 0), 0, 10, 0.0, 0.0))
		flow_label.add_theme_color_override("font_color", colors[stage])

func set_objective(text_value: String, fraction: float) -> void:
	objective_label.text = text_value
	objective_bar.value = clampf(fraction, 0.0, 1.0)
	objective_bar.visible = text_value != ""

func set_power(power_id: String, ready_fraction: float, active: bool, remaining: float) -> void:
	var title := power_id.replace("_", " ").to_upper()
	if active:
		power_button.text = "%s\n%.1fs" % [title, remaining]
		power_button.disabled = true
		power_cool.value = 1.0
	else:
		power_button.text = title if ready_fraction >= 1.0 else "%s\nCHARGING" % title
		power_button.disabled = ready_fraction < 1.0
		power_cool.value = ready_fraction

func set_power_name(power_id: String) -> void:
	power_button.text = power_id.replace("_", " ").to_upper()

func set_district(district_name: String) -> void:
	district_label.text = district_name.to_upper()
	show_banner(district_name.to_upper(), "NOW ENTERING")

# ---------------------------------------------------------------- toast / banner
func _build_toast_and_banner() -> void:
	var holder := VBoxContainer.new()
	holder.set_anchors_and_offsets_preset(Control.PRESET_TOP_WIDE)
	holder.offset_top = 330
	holder.offset_bottom = 760
	holder.alignment = BoxContainer.ALIGNMENT_BEGIN
	holder.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_theme_constant_override("separation", 14)
	root.add_child(holder)
	banner_label = UITheme.label("", 64, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER)
	banner_label.modulate.a = 0.0
	holder.add_child(banner_label)
	var center := CenterContainer.new()
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	holder.add_child(center)
	toast_panel = UITheme.panel(UITheme.box(Color(0.03, 0.06, 0.1, 0.9), Color(UITheme.CYAN.r, UITheme.CYAN.g, UITheme.CYAN.b, 0.6), 2, 26, 30.0, 12.0))
	toast_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	toast_panel.visible = false
	center.add_child(toast_panel)
	toast_label = UITheme.label("", 28, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER)
	toast_panel.add_child(toast_label)

func flash(message: String) -> void:
	if message == "":
		toast_panel.visible = false
		return
	toast_label.text = message
	toast_panel.visible = true
	toast_panel.modulate.a = 1.0
	if _toast_tween != null and _toast_tween.is_valid():
		_toast_tween.kill()
	_toast_tween = create_tween()
	_toast_tween.tween_interval(1.9)
	_toast_tween.tween_property(toast_panel, "modulate:a", 0.0, 0.5)
	_toast_tween.tween_callback(_hide_toast)

func _hide_toast() -> void:
	toast_panel.visible = false

func show_banner(title: String, subtitle: String = "") -> void:
	if not run_layer.visible:
		return
	banner_label.text = title
	if _banner_tween != null and _banner_tween.is_valid():
		_banner_tween.kill()
	banner_label.modulate.a = 0.0
	banner_label.pivot_offset = banner_label.size * 0.5
	banner_label.scale = Vector2(1.18, 1.18)
	_banner_tween = create_tween()
	_banner_tween.set_parallel(true)
	_banner_tween.tween_property(banner_label, "modulate:a", 1.0, 0.25)
	_banner_tween.tween_property(banner_label, "scale", Vector2.ONE, 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_banner_tween.chain().tween_interval(1.5)
	_banner_tween.chain().tween_property(banner_label, "modulate:a", 0.0, 0.6)

# ---------------------------------------------------------------- fade / countdown
func _build_fade_and_countdown() -> void:
	countdown_label = UITheme.label("", 220, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER)
	countdown_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	countdown_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	countdown_label.add_theme_color_override("font_outline_color", UITheme.CYAN)
	countdown_label.add_theme_constant_override("outline_size", 10)
	countdown_label.visible = false
	root.add_child(countdown_label)
	fade_rect = ColorRect.new()
	fade_rect.color = Color(0, 0, 0, 1)
	fade_rect.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	fade_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(fade_rect)

func fade_in_now() -> void:
	var tween := create_tween()
	tween.tween_property(fade_rect, "color:a", 0.0, 0.5 * AccessibilityService.flash_scale() + 0.05)

## Awaitable: `await hud.fade_to(1.0, 0.2)`.
func fade_to(alpha: float, duration: float) -> void:
	var d := duration * (0.5 if AccessibilityService.is_enabled("reduced_flashes") else 1.0)
	if d <= 0.01:
		fade_rect.color.a = alpha
		return
	var tween := create_tween()
	tween.tween_property(fade_rect, "color:a", alpha, d)
	await tween.finished

func transition_to_black(duration: float = 0.18) -> void:
	await fade_to(1.0, duration)

func transition_from_black(duration: float = 0.28) -> void:
	await fade_to(0.0, duration)

func show_countdown_step(text_value: String) -> void:
	countdown_label.text = text_value
	countdown_label.visible = text_value != ""
	if text_value == "":
		return
	countdown_label.pivot_offset = countdown_label.size * 0.5
	countdown_label.scale = Vector2(1.5, 1.5)
	countdown_label.modulate.a = 1.0
	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(countdown_label, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(countdown_label, "modulate:a", 0.0, 0.45).set_delay(0.12)

# ---------------------------------------------------------------- pause / revive / results
func _build_pause_layer() -> void:
	pause_layer = Control.new()
	_full_rect(pause_layer)
	pause_layer.visible = false
	root.add_child(pause_layer)
	pause_layer.add_child(_dim(0.7))
	var content := _center_card(pause_layer, 760.0)
	content.add_child(UITheme.label("PAUSED", 64, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER))
	resume_button = UITheme.button("RESUME", UITheme.CYAN, true, Vector2(0, 100))
	resume_button.pressed.connect(func() -> void: resume_requested.emit())
	content.add_child(resume_button)
	var quit := UITheme.button("QUIT TO MENU", UITheme.SLATE, false, Vector2(0, 84))
	quit.pressed.connect(func() -> void: quit_to_menu_requested.emit())
	content.add_child(quit)

func set_paused(value: bool) -> void:
	pause_layer.visible = value

func _build_revive_layer() -> void:
	revive_layer = Control.new()
	_full_rect(revive_layer)
	revive_layer.visible = false
	root.add_child(revive_layer)
	revive_layer.add_child(_dim(0.62))
	var content := _center_card(revive_layer, 820.0)
	content.add_child(UITheme.label("SECOND CHANCE", 54, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER))
	revive_time_label = UITheme.label("6", 150, UITheme.ORANGE, true, HORIZONTAL_ALIGNMENT_CENTER)
	content.add_child(revive_time_label)
	revive_button = UITheme.button("REVIVE", UITheme.CYAN, true, Vector2(0, 100))
	revive_button.pressed.connect(func() -> void: revive_requested.emit())
	content.add_child(revive_button)
	var decline := UITheme.button("NO THANKS", UITheme.SLATE, false, Vector2(0, 80))
	decline.pressed.connect(func() -> void: end_run_requested.emit())
	content.add_child(decline)

func show_revive(value: bool) -> void:
	revive_layer.visible = value
	if value:
		revive_button.text = "REVIVE  (FREE)" if AdsService.ads_removed else "REVIVE  •  WATCH AD"
		revive_time_label.text = "6"

func set_revive_time(seconds: float) -> void:
	revive_time_label.text = str(maxi(0, int(ceil(seconds))))

func _build_end_layer() -> void:
	end_layer = Control.new()
	_full_rect(end_layer)
	end_layer.visible = false
	root.add_child(end_layer)
	end_layer.add_child(_dim(0.78))
	end_content = _center_card(end_layer, 940.0)

func show_end(summary: Dictionary) -> void:
	menu_layer.visible = false
	run_layer.visible = false
	end_layer.visible = true
	for child in end_content.get_children():
		end_content.remove_child(child)
		child.queue_free()
	var objective_done := bool(summary.get("objective_finished", false))
	var reason := str(summary.get("reason", ""))
	var title := "OBJECTIVE COMPLETE" if objective_done else ("RUN OVER" if reason.begins_with("collision") else "RUN COMPLETE")
	end_content.add_child(UITheme.label(title, 52, UITheme.GREEN if objective_done else UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER))
	end_content.add_child(UITheme.label(_format_number(int(summary.get("score", 0))), 120, UITheme.GOLD, true, HORIZONTAL_ALIGNMENT_CENTER))
	if bool(summary.get("new_best_score", false)):
		end_content.add_child(UITheme.label("NEW PERSONAL BEST!", 30, UITheme.ORANGE, true, HORIZONTAL_ALIGNMENT_CENTER))
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 24)
	grid.add_theme_constant_override("v_separation", 10)
	end_content.add_child(grid)
	var rows := [
		["DISTANCE", "%d m" % int(summary.get("distance", 0.0))],
		["CREDITS EARNED", "+%s" % _format_number(int(summary.get("credits", 0)))],
		["XP", "+%d" % int(summary.get("xp", 0))],
		["ORBS", str(int(summary.get("collectibles", 0)))],
		["PEAK FLOW", "STAGE %d" % int(summary.get("peak_flow", 0))],
		["OBJECTIVE", "%s  •  %s" % [str(summary.get("objective_text", "")), "DONE" if objective_done else "MISSED"]]
	]
	for r in rows:
		var key := UITheme.label(str(r[0]), 22, UITheme.TEXT_DIM, true)
		key.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		grid.add_child(key)
		grid.add_child(UITheme.label(str(r[1]), 24, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_RIGHT))
	var again := UITheme.button("RUN AGAIN", UITheme.CYAN, true, Vector2(0, 104))
	again.add_theme_font_size_override("font_size", 36)
	again.pressed.connect(_on_start_pressed)
	end_content.add_child(again)
	rewarded_button = UITheme.button("DOUBLE REWARD  •  WATCH AD", UITheme.GOLD, false, Vector2(0, 84))
	rewarded_button.visible = AdsService.can_offer_rewarded() and not AdsService.ads_removed and int(summary.get("finish_reward", 0)) > 0
	rewarded_button.pressed.connect(func() -> void: rewarded_requested.emit())
	end_content.add_child(rewarded_button)
	var home := UITheme.button("HOME", UITheme.SLATE, false, Vector2(0, 80))
	home.pressed.connect(_on_home_pressed)
	end_content.add_child(home)
	start_button.text = "RUN AGAIN"

func hide_rewarded_button() -> void:
	if rewarded_button != null and is_instance_valid(rewarded_button):
		rewarded_button.visible = false

func _on_home_pressed() -> void:
	end_layer.visible = false
	menu_layer.visible = true
	refresh_menu()
	home_requested.emit()

# ---------------------------------------------------------------- detail sheets
func _build_detail_layer() -> void:
	detail_layer = Control.new()
	_full_rect(detail_layer)
	detail_layer.visible = false
	root.add_child(detail_layer)
	detail_layer.add_child(_dim(0.86))
	var safe := _safe_margin(detail_layer)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 14)
	safe.add_child(column)
	var header := HBoxContainer.new()
	column.add_child(header)
	detail_title = UITheme.label("", 52, UITheme.TEXT, true)
	detail_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(detail_title)
	var close := UITheme.button("BACK", UITheme.SLATE, false, Vector2(190, 76))
	close.pressed.connect(close_detail)
	header.add_child(close)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	column.add_child(scroll)
	detail_content = VBoxContainer.new()
	detail_content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_content.add_theme_constant_override("separation", 14)
	scroll.add_child(detail_content)

func _open_detail(section: String) -> void:
	_detail_section = section
	detail_layer.visible = true
	detail_title.text = section.to_upper()
	for child in detail_content.get_children():
		detail_content.remove_child(child)
		child.queue_free()
	match section:
		"garage": _build_garage()
		"missions": _build_missions()
		"shop": _build_shop()
		"settings": _build_settings()
		"season": _build_season()
		"achievements": _build_achievements()
		"leaderboards": _build_leaderboards()

func close_detail() -> void:
	detail_layer.visible = false
	refresh_menu()

func _section(title: String) -> void:
	detail_content.add_child(UITheme.label(title, 30, UITheme.ORANGE, true))

func _row_panel() -> HBoxContainer:
	var card := UITheme.panel(UITheme.box(UITheme.PANEL_SOFT, Color(1, 1, 1, 0.08), 1, 20, 20.0, 12.0))
	card.mouse_filter = Control.MOUSE_FILTER_PASS
	detail_content.add_child(card)
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 14)
	card.add_child(row)
	return row

func _row_label(row: HBoxContainer, title: String, subtitle: String = "") -> void:
	var col := VBoxContainer.new()
	col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	col.add_theme_constant_override("separation", 2)
	row.add_child(col)
	col.add_child(UITheme.label(title, 24, UITheme.TEXT, true))
	if subtitle != "":
		var sub := UITheme.label(subtitle, 18, UITheme.TEXT_DIM)
		sub.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		col.add_child(sub)

func _row_button(row: HBoxContainer, text_value: String, accent: Color, filled: bool, handler: Callable, disabled: bool = false) -> void:
	var b := UITheme.button(text_value, accent, filled, Vector2(210, 66))
	b.add_theme_font_size_override("font_size", 22)
	b.disabled = disabled
	b.pressed.connect(handler)
	b.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(b)

func _build_garage() -> void:
	_section("RUNNERS")
	for runner_def in RunnerCatalog.all():
		var runner_id := str(runner_def["id"])
		var unlocked := ProgressionService.is_runner_unlocked(runner_id)
		var row := _row_panel()
		var swatch := ColorRect.new()
		swatch.color = runner_def["color"]
		swatch.custom_minimum_size = Vector2(16, 58)
		row.add_child(swatch)
		var subtitle := str(runner_def["role"]) if unlocked else "Unlocks at level %d" % ProgressionService.runner_unlock_level(runner_id)
		_row_label(row, runner_id, subtitle)
		var selected := runner_id == AppState.selected_runner
		_row_button(row, "SELECTED" if selected else ("SELECT" if unlocked else "LOCKED"), UITheme.CYAN, not selected and unlocked, _select_runner.bind(runner_id), selected or not unlocked)
	_section("POWER")
	var equipped := str(SaveService.data["profile"].get("equipped_power", "phase_shield"))
	for power_id in POWER_IDS:
		var row := _row_panel()
		_row_label(row, power_id.replace("_", " ").to_upper(), "%.1f s active  •  %.0f s recharge" % [float(PowerSystem.DURATIONS.get(power_id, 5.0)), float(PowerSystem.COOLDOWNS.get(power_id, 20.0))])
		_row_button(row, "EQUIPPED" if power_id == equipped else "EQUIP", UITheme.MAGENTA, power_id != equipped, _select_power.bind(power_id), power_id == equipped)
	_section("OUTFITS")
	var current_outfit := ShopService.equipped()
	var none_row := _row_panel()
	_row_label(none_row, "RUNNER COLOUR", "Use the runner's own accent colour")
	_row_button(none_row, "EQUIPPED" if current_outfit == "" else "EQUIP", UITheme.GREEN, current_outfit != "", _equip_outfit.bind(""), current_outfit == "")
	var any_owned := false
	for item in ContentRegistry.cosmetics():
		var item_id := str(item["id"])
		if not ShopService.is_owned(item_id):
			continue
		any_owned = true
		var row := _row_panel()
		var swatch := ColorRect.new()
		swatch.color = item["color"]
		swatch.custom_minimum_size = Vector2(16, 58)
		row.add_child(swatch)
		_row_label(row, str(item["name"]))
		_row_button(row, "EQUIPPED" if current_outfit == item_id else "EQUIP", UITheme.GREEN, current_outfit != item_id, _equip_outfit.bind(item_id), current_outfit == item_id)
	if not any_owned:
		detail_content.add_child(UITheme.label("Buy outfits in the SHOP to equip them here.", 20, UITheme.TEXT_DIM))

func _select_runner(runner_id: String) -> void:
	ProgressionService.set_selected_runner(runner_id)
	flash("%s READY FOR NEXT RUN" % runner_id.to_upper())
	_open_detail("garage")

func _select_power(power_id: String) -> void:
	ProgressionService.set_equipped_power(power_id)
	flash("%s EQUIPPED" % power_id.replace("_", " ").to_upper())
	_open_detail("garage")

func _equip_outfit(outfit_id: String) -> void:
	ShopService.equip_cosmetic(outfit_id)
	flash("OUTFIT EQUIPPED" if outfit_id != "" else "RUNNER COLOUR RESTORED")
	_open_detail("garage")

func _build_missions() -> void:
	_section("DAILY MISSIONS")
	for mission in MissionService.active:
		var target := float(mission["target"])
		var progress := float(mission["progress"])
		var done := progress >= target
		var row := _row_panel()
		var col := VBoxContainer.new()
		col.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row.add_child(col)
		col.add_child(UITheme.label(str(mission["id"]).replace("daily_", "").to_upper(), 24, UITheme.TEXT, true))
		var bar := ProgressBar.new()
		bar.show_percentage = false
		bar.max_value = target
		bar.value = minf(progress, target)
		bar.custom_minimum_size = Vector2(0, 14)
		bar.add_theme_stylebox_override("fill", UITheme.box(UITheme.GREEN if done else UITheme.CYAN, Color(0, 0, 0, 0), 0, 8, 0.0, 0.0))
		col.add_child(bar)
		col.add_child(UITheme.label("%.0f / %.0f" % [minf(progress, target), target], 18, UITheme.TEXT_DIM))
		row.add_child(UITheme.label("DONE" if done else "+%d" % int(mission["reward"]), 26, UITheme.GREEN if done else UITheme.GOLD, true))
	_section("CHALLENGE VAULT")
	for challenge in ContentRegistry.challenges().slice(0, 20):
		var challenge_id := str(challenge["id"])
		var selected := challenge_id == ChallengeService.selected_id
		var row := _row_panel()
		_row_label(row, "%s  •  %s" % [challenge_id.to_upper(), str(challenge["tier"])], "%dm  •  reward %d CR" % [int(challenge["target"]), int(challenge["reward"])])
		_row_button(row, "SELECTED" if selected else "SELECT", UITheme.VIOLET, not selected, _select_challenge.bind(challenge_id), selected)

func _select_challenge(challenge_id: String) -> void:
	ChallengeService.select(challenge_id)
	flash("%s SELECTED" % challenge_id.to_upper())
	_open_detail("missions")

func _build_shop() -> void:
	var balance := HBoxContainer.new()
	balance.add_theme_constant_override("separation", 20)
	detail_content.add_child(balance)
	balance.add_child(UITheme.icon_rect("icon_credit", 44.0))
	balance.add_child(UITheme.label(_format_number(EconomyService.balance("credits")), 30, UITheme.GOLD, true))
	balance.add_child(UITheme.icon_rect("icon_nova", 44.0))
	balance.add_child(UITheme.label(_format_number(EconomyService.balance("nova")), 30, UITheme.CYAN, true))
	var restore := UITheme.button("RESTORE PURCHASES", UITheme.SLATE, false, Vector2(0, 70))
	restore.pressed.connect(_restore_purchases)
	detail_content.add_child(restore)
	_section("PREMIUM")
	for product_id in BillingService.PRODUCTS.keys():
		var owned := BillingService.is_one_time(product_id) and BillingService.is_owned(product_id)
		var row := _row_panel()
		_row_label(row, str(product_id).replace("_", " ").to_upper(), _product_blurb(str(product_id)))
		_row_button(row, "OWNED" if owned else "BUY", UITheme.GOLD, not owned, _purchase_product.bind(str(product_id)), owned)
	_section("OUTFITS")
	for item in ContentRegistry.cosmetics():
		var item_id := str(item["id"])
		var owned := ShopService.is_owned(item_id)
		var row := _row_panel()
		var swatch := ColorRect.new()
		swatch.color = item["color"]
		swatch.custom_minimum_size = Vector2(16, 58)
		row.add_child(swatch)
		_row_label(row, str(item["name"]), "%d %s" % [int(item["cost"]), str(item["currency"]).to_upper()])
		_row_button(row, "OWNED" if owned else "BUY", UITheme.GOLD, not owned, _purchase_cosmetic.bind(item_id), owned)
	_section("EVENT SHOP  •  %d TOKENS" % EconomyService.balance("event_tokens"))
	for item in ContentRegistry.event_shop():
		var row := _row_panel()
		_row_label(row, str(item["name"]), "%d tokens  →  +%d CR  +%d NOVA" % [int(item["cost"]), int(item["reward_credits"]), int(item["reward_nova"])])
		_row_button(row, "CLAIM", UITheme.ORANGE, true, _purchase_event_item.bind(str(item["id"])))

func _product_blurb(product_id: String) -> String:
	var def: Dictionary = BillingService.PRODUCTS[product_id]
	var parts: Array[String] = []
	if int(def.get("credits", 0)) > 0:
		parts.append("%d CR" % int(def["credits"]))
	if int(def.get("nova", 0)) > 0:
		parts.append("%d NOVA" % int(def["nova"]))
	if int(def.get("event_tokens", 0)) > 0:
		parts.append("%d tokens" % int(def["event_tokens"]))
	if def.has("cosmetics"):
		parts.append("outfit")
	if product_id == "remove_ads_499":
		parts.append("no ads, free revives")
	if product_id == "season_pass_999":
		parts.append("+50% season credits")
	return "  •  ".join(parts)

func _purchase_product(product_id: String) -> void:
	BillingService.purchase(product_id)
	_open_detail("shop")

func _restore_purchases() -> void:
	BillingService.restore_purchases()
	flash("RESTORE REQUEST SENT")

func _purchase_cosmetic(item_id: String) -> void:
	if ShopService.purchase_cosmetic(item_id):
		flash("OUTFIT UNLOCKED")
	else:
		flash("NOT ENOUGH CURRENCY")
	_open_detail("shop")

func _purchase_event_item(item_id: String) -> void:
	if ShopService.purchase_event_item(item_id):
		flash("EVENT SUPPLY CLAIMED")
	else:
		flash("NOT ENOUGH EVENT TOKENS")
	_open_detail("shop")

func _build_season() -> void:
	var tier := SeasonEngine.tier()
	detail_content.add_child(UITheme.label("SEASON %s" % LiveOpsService.season_id.to_upper(), 30, UITheme.ORANGE, true))
	detail_content.add_child(UITheme.label("TIER %02d" % tier, 90, UITheme.TEXT, true))
	var bar := ProgressBar.new()
	bar.show_percentage = false
	bar.max_value = 1.0
	bar.step = 0.001
	bar.value = SeasonEngine.progress_to_next()
	bar.custom_minimum_size = Vector2(0, 22)
	detail_content.add_child(bar)
	detail_content.add_child(UITheme.label("%d / %d XP to next tier  •  pass: %s" % [LiveOpsService.season_xp % SeasonEngine.XP_PER_TIER, SeasonEngine.XP_PER_TIER, "ACTIVE" if bool(SaveService.data["season"].get("pass", false)) else "not owned"], 20, UITheme.TEXT_DIM))
	var claimable := SeasonEngine.claimable_tiers()
	var claim := UITheme.button("CLAIM %d REWARD%s" % [claimable.size(), "" if claimable.size() == 1 else "S"] if not claimable.is_empty() else "NOTHING TO CLAIM", UITheme.GOLD, not claimable.is_empty(), Vector2(0, 90))
	claim.disabled = claimable.is_empty()
	claim.pressed.connect(_claim_season)
	detail_content.add_child(claim)
	_section("UPCOMING")
	for t in range(tier, mini(tier + 5, SeasonEngine.MAX_TIER + 1)):
		var reward := SeasonEngine.reward_at_tier(t)
		var row := _row_panel()
		_row_label(row, "TIER %02d" % t, "%d CR%s" % [int(reward["credits"]), "  •  %d NOVA" % int(reward["nova"]) if int(reward["nova"]) > 0 else ""])

func _claim_season() -> void:
	var count := SeasonEngine.claim_all()
	flash("%d SEASON REWARD%s CLAIMED" % [count, "" if count == 1 else "S"])
	_open_detail("season")

func _build_achievements() -> void:
	for achievement_id in AchievementService.catalog().keys():
		var unlocked := bool(SaveService.data["achievements"].get(achievement_id, false))
		var row := _row_panel()
		row.add_child(UITheme.icon_rect("icon_check" if unlocked else "icon_lock", 40.0, UITheme.GREEN if unlocked else UITheme.TEXT_DIM))
		_row_label(row, AchievementService.title(str(achievement_id)), "UNLOCKED" if unlocked else "LOCKED")

func _build_leaderboards() -> void:
	_section("PERSONAL BESTS")
	for entry in [["ENDLESS", int(SaveService.data.get("best_score", 0))], ["DAILY", int(SaveService.data["daily"].get("best_score", 0))], ["WEEKLY", int(SaveService.data["weekly"].get("best_score", 0))]]:
		var row := _row_panel()
		_row_label(row, str(entry[0]))
		row.add_child(UITheme.label(_format_number(int(entry[1])), 30, UITheme.GOLD, true))
	detail_content.add_child(UITheme.label("ONLINE BOARDS: " + ("CONNECTED" if BackendService.online else "OFFLINE (scores stay on this device)"), 20, UITheme.TEXT_DIM))
	var refresh := UITheme.button("REFRESH DAILY BOARD", UITheme.CYAN, false, Vector2(0, 76))
	refresh.pressed.connect(_refresh_board.bind("daily"))
	detail_content.add_child(refresh)

func _refresh_board(board_id: String) -> void:
	var entries := BackendService.fetch_leaderboard(board_id)
	flash("%s BOARD  •  %d ENTRIES" % [board_id.to_upper(), entries.size()])

func _build_settings() -> void:
	_section("AUDIO & FEEL")
	_add_toggle("MUSIC", "music")
	_add_toggle("SOUND EFFECTS", "sfx")
	_add_toggle("HAPTICS", "haptics")
	_add_toggle("CAMERA SHAKE", "camera_shake")
	_add_toggle("REDUCED FLASHES", "reduced_flashes")
	_add_toggle("LEFT-HANDED POWER BUTTON", "left_handed")
	_section("GRAPHICS")
	var current := str(SaveService.data["settings"].get("graphics", "auto")).to_upper()
	var gfx := UITheme.button("QUALITY: %s  (%s)" % [current, DeviceProfileService.profile], UITheme.VIOLET, false, Vector2(0, 76))
	gfx.pressed.connect(_cycle_graphics)
	detail_content.add_child(gfx)
	_section("PRIVACY")
	var privacy_text := "Analytics: %s  •  Ads: %s" % ["ON" if ConsentService.analytics_allowed() else "OFF", "ON" if ConsentService.ads_allowed() else "OFF"]
	detail_content.add_child(UITheme.label(privacy_text, 22, UITheme.TEXT_DIM))
	var change := UITheme.button("CHANGE DATA CHOICES", UITheme.SLATE, false, Vector2(0, 76))
	change.pressed.connect(_reopen_consent)
	detail_content.add_child(change)
	detail_content.add_child(UITheme.label("NEXALANE v%s  •  content %s" % [AppState.PRODUCT_VERSION, AppState.CONTENT_VERSION], 18, UITheme.TEXT_DIM))

func _add_toggle(caption: String, key: String) -> void:
	var value := bool(SaveService.data["settings"].get(key, false))
	var b := UITheme.button("%s:  %s" % [caption, "ON" if value else "OFF"], UITheme.GREEN if value else UITheme.SLATE, value, Vector2(0, 76))
	b.pressed.connect(_toggle_setting.bind(key))
	detail_content.add_child(b)

func _toggle_setting(key: String) -> void:
	AccessibilityService.set_setting(key, not bool(SaveService.data["settings"].get(key, false)))
	_open_detail("settings")

func _cycle_graphics() -> void:
	var order := ["auto", "low", "mid", "high"]
	var current := str(SaveService.data["settings"].get("graphics", "auto")).to_lower()
	var next_value: String = order[(order.find(current) + 1) % order.size()]
	AccessibilityService.set_setting("graphics", next_value)
	flash("QUALITY: %s" % next_value.to_upper())
	_open_detail("settings")

# ---------------------------------------------------------------- consent + tutorial
func _build_modal_layer() -> void:
	modal_layer = Control.new()
	_full_rect(modal_layer)
	modal_layer.visible = false
	root.add_child(modal_layer)

func _clear_modal() -> VBoxContainer:
	for child in modal_layer.get_children():
		modal_layer.remove_child(child)
		child.queue_free()
	modal_layer.visible = true
	modal_layer.add_child(_dim(0.84))
	return _center_card(modal_layer, 940.0)

func _maybe_show_consent() -> void:
	if not ConsentService.has_decision():
		_show_consent()
	else:
		_maybe_show_tutorial()

func _reopen_consent() -> void:
	detail_layer.visible = false
	_show_consent()

func _show_consent() -> void:
	var card := _clear_modal()
	card.add_child(UITheme.label("YOUR DATA, YOUR CHOICE", 46, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER))
	var body := UITheme.label("NEXALANE works fully offline. Optional analytics help us fix bugs and balance the game. Optional ads let you revive and double rewards. Change this any time in Settings.", 24, UITheme.TEXT_DIM, false, HORIZONTAL_ALIGNMENT_CENTER)
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(body)
	var allow := UITheme.button("ALLOW OPTIONAL DATA & ADS", UITheme.CYAN, true, Vector2(0, 100))
	allow.pressed.connect(_on_consent.bind(true))
	card.add_child(allow)
	var decline := UITheme.button("CONTINUE PRIVATELY", UITheme.SLATE, false, Vector2(0, 84))
	decline.pressed.connect(_on_consent.bind(false))
	card.add_child(decline)

func _on_consent(allow: bool) -> void:
	ConsentService.set_consent(allow, allow, false)
	modal_layer.visible = false
	_maybe_show_tutorial()

func _maybe_show_tutorial() -> void:
	if bool(SaveService.data.get("tutorial_complete", false)):
		return
	var card := _clear_modal()
	card.add_child(UITheme.label("WELCOME TO THE RELAY", 46, UITheme.TEXT, true, HORIZONTAL_ALIGNMENT_CENTER))
	var hints := GridContainer.new()
	hints.columns = 2
	hints.add_theme_constant_override("h_separation", 20)
	hints.add_theme_constant_override("v_separation", 14)
	card.add_child(hints)
	for hint in [["icon_arrow", 270.0, "SWIPE LEFT / RIGHT", "Change lane (A / D)"], ["icon_arrow", 0.0, "SWIPE UP", "Jump over low hazards (W / Space)"], ["icon_arrow", 180.0, "SWIPE DOWN", "Slide under high hazards (S)"], ["icon_power", 0.0, "POWER BUTTON", "Shield, magnet and more (E)"]]:
		var icon_node := UITheme.icon_rect(str(hint[0]), 64.0, UITheme.CYAN)
		icon_node.pivot_offset = Vector2(32, 32)
		icon_node.rotation_degrees = float(hint[1])
		hints.add_child(icon_node)
		var col := VBoxContainer.new()
		col.add_theme_constant_override("separation", 0)
		col.add_child(UITheme.label(str(hint[2]), 24, UITheme.TEXT, true))
		col.add_child(UITheme.label(str(hint[3]), 18, UITheme.TEXT_DIM))
		hints.add_child(col)
	var tip := UITheme.label("Pass close to hazards and grab orbs to build FLOW for score multipliers.", 22, UITheme.ORANGE, false, HORIZONTAL_ALIGNMENT_CENTER)
	tip.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	card.add_child(tip)
	var ok := UITheme.button("I'M READY", UITheme.CYAN, true, Vector2(0, 96))
	ok.pressed.connect(func() -> void: modal_layer.visible = false)
	card.add_child(ok)
