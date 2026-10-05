extends RefCounted
class_name UITheme

## Visual language: dark glass panels, cyan/orange neon accents, Poppins type. Styles are built once in code so
## the whole UI shares them (no per-scene resources to keep in sync).

const TEXT := Color("#eaf6ff")
const TEXT_DIM := Color("#8fa6bd")
const PANEL := Color(0.040, 0.070, 0.120, 0.94)
const PANEL_SOFT := Color(0.060, 0.100, 0.165, 0.90)
const CYAN := Color("#2de2ff")
const ORANGE := Color("#ff8a3d")
const GOLD := Color("#ffd45a")
const MAGENTA := Color("#ff4fb8")
const GREEN := Color("#5dffb0")
const VIOLET := Color("#9a7cff")
const SLATE := Color("#9fb8cc")
const DANGER := Color("#ff5468")

const ICON_PATH := "res://assets/ui/%s.png"
const FONT_BOLD_PATH := "res://assets/fonts/Poppins-Bold.ttf"
const FONT_MEDIUM_PATH := "res://assets/fonts/Poppins-Medium.ttf"

static var _theme: Theme = null
static var _bold: Font = null
static var _medium: Font = null
static var _icons: Dictionary = {}

static func bold() -> Font:
	if _bold == null:
		_bold = load(FONT_BOLD_PATH) as Font
	return _bold

static func medium() -> Font:
	if _medium == null:
		_medium = load(FONT_MEDIUM_PATH) as Font
	return _medium

static func icon(icon_name: String) -> Texture2D:
	if not _icons.has(icon_name):
		_icons[icon_name] = load(ICON_PATH % icon_name) as Texture2D
	return _icons[icon_name] as Texture2D

static func box(bg: Color, border: Color = Color(0, 0, 0, 0), border_width: int = 0, radius: int = 20, pad_h: float = 18.0, pad_v: float = 12.0) -> StyleBoxFlat:
	var sb := StyleBoxFlat.new()
	sb.bg_color = bg
	sb.border_color = border
	sb.set_border_width_all(border_width)
	sb.set_corner_radius_all(radius)
	sb.content_margin_left = pad_h
	sb.content_margin_right = pad_h
	sb.content_margin_top = pad_v
	sb.content_margin_bottom = pad_v
	return sb

static func get_theme() -> Theme:
	if _theme != null:
		return _theme
	var t := Theme.new()
	t.default_font = medium()
	t.default_font_size = 24
	t.set_color("font_color", "Label", TEXT)
	t.set_color("font_shadow_color", "Label", Color(0, 0, 0, 0.55))
	t.set_constant("shadow_offset_x", "Label", 2)
	t.set_constant("shadow_offset_y", "Label", 2)
	t.set_stylebox("panel", "PanelContainer", box(PANEL, Color(CYAN.r, CYAN.g, CYAN.b, 0.35), 2, 30, 28.0, 24.0))
	t.set_stylebox("background", "ProgressBar", box(Color(0.02, 0.04, 0.07, 0.85), Color(1, 1, 1, 0.08), 1, 10, 0.0, 0.0))
	t.set_stylebox("fill", "ProgressBar", box(CYAN, Color(0, 0, 0, 0), 0, 10, 0.0, 0.0))
	t.set_constant("separation", "VBoxContainer", 12)
	t.set_constant("separation", "HBoxContainer", 12)
	_theme = t
	return t

# ---------------------------------------------------------------- factories
static func label(text_value: String, size_value: int = 24, color: Color = TEXT, use_bold: bool = false, align: int = HORIZONTAL_ALIGNMENT_LEFT) -> Label:
	var l := Label.new()
	l.text = text_value
	l.add_theme_font_size_override("font_size", size_value)
	l.add_theme_color_override("font_color", color)
	if use_bold:
		l.add_theme_font_override("font", bold())
	l.horizontal_alignment = align as HorizontalAlignment
	l.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return l

static func style_button(button: Button, accent: Color, filled: bool = false, radius: int = 22) -> void:
	var normal := box(accent if filled else Color(0.055, 0.095, 0.155, 0.94), Color(accent.r, accent.g, accent.b, 0.95), 2, radius, 22.0, 12.0)
	if filled:
		normal.shadow_color = Color(accent.r, accent.g, accent.b, 0.38)
		normal.shadow_size = 16
	var hover := box(accent.lightened(0.15) if filled else Color(accent.r, accent.g, accent.b, 0.22), Color(accent.r, accent.g, accent.b, 1.0), 2, radius, 22.0, 12.0)
	var pressed := box(accent.darkened(0.25) if filled else Color(accent.r, accent.g, accent.b, 0.42), Color(1, 1, 1, 0.8), 2, radius, 22.0, 12.0)
	var disabled := box(Color(0.05, 0.07, 0.1, 0.7), Color(1, 1, 1, 0.12), 2, radius, 22.0, 12.0)
	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_stylebox_override("pressed", pressed)
	button.add_theme_stylebox_override("disabled", disabled)
	button.add_theme_stylebox_override("focus", StyleBoxEmpty.new())
	var text_color := Color("#06121c") if filled else TEXT
	button.add_theme_color_override("font_color", text_color)
	button.add_theme_color_override("font_hover_color", text_color)
	button.add_theme_color_override("font_pressed_color", text_color)
	button.add_theme_color_override("font_disabled_color", Color(1, 1, 1, 0.35))
	button.add_theme_font_override("font", bold())
	button.add_theme_font_size_override("font_size", 26)
	button.focus_mode = Control.FOCUS_NONE

static func button(text_value: String, accent: Color = CYAN, filled: bool = false, min_size: Vector2 = Vector2(0, 76)) -> Button:
	var b := Button.new()
	b.text = text_value
	b.custom_minimum_size = min_size
	style_button(b, accent, filled)
	b.pressed.connect(UITheme._on_button_pressed)
	return b

static func _on_button_pressed() -> void:
	AudioService.play_sfx("ui_tap")
	AccessibilityService.haptic("light")

static func icon_rect(icon_name: String, size_px: float, tint: Color = Color.WHITE) -> TextureRect:
	var r := TextureRect.new()
	r.texture = icon(icon_name)
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	r.custom_minimum_size = Vector2(size_px, size_px)
	r.modulate = tint
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r

static func panel(style: StyleBoxFlat = null) -> PanelContainer:
	var p := PanelContainer.new()
	if style != null:
		p.add_theme_stylebox_override("panel", style)
	return p

static func spacer(vertical: bool = false) -> Control:
	var s := Control.new()
	s.mouse_filter = Control.MOUSE_FILTER_IGNORE
	if vertical:
		s.size_flags_vertical = Control.SIZE_EXPAND_FILL
	else:
		s.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return s

static func gradient_rect(top_color: Color, bottom_color: Color) -> TextureRect:
	var g := Gradient.new()
	g.set_color(0, top_color)
	g.set_color(1, bottom_color)
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill_from = Vector2(0.0, 0.0)
	gt.fill_to = Vector2(0.0, 1.0)
	gt.width = 8
	gt.height = 256
	var r := TextureRect.new()
	r.texture = gt
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_SCALE
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return r
