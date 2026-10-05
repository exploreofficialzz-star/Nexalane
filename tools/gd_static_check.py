#!/usr/bin/env python3
"""Static GDScript checks - a stand-in for the Godot compiler when no engine binary is available.

It catches the error classes that actually broke NEXALANE 0.4.4 (none of which the old audit noticed):
  * broken indentation / unbalanced brackets                      (parse error)
  * `class_name` that equals an autoload singleton's name          (parse error: "hides an autoload singleton")
  * `var x := <Variant expression>`                                (INFERENCE_ON_VARIANT is an ERROR by default)
  * calls / member access on autoloads and class_names that do not exist or have the wrong argument count
  * `.connect(handler)` to a method that does not exist, `signal.emit(...)` with the wrong argument count
  * `res://` paths that do not exist
It is heuristic: ERRORS are high-confidence problems, WARNINGS deserve a human look. Exit code 1 when any ERROR.

    python tools/gd_static_check.py            # whole project
    python tools/gd_static_check.py --warn     # also list warnings
"""
from __future__ import annotations
import re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEYWORDS = {'if', 'elif', 'else', 'for', 'while', 'match', 'return', 'await', 'and', 'or', 'not', 'in', 'is', 'as', 'func', 'var', 'const',
            'signal', 'class', 'extends', 'pass', 'break', 'continue', 'static', 'enum', 'preload', 'assert', 'yield', 'super', 'self', 'true', 'false', 'null', 'void'}
TYPED_BUILTINS = set('''str int float bool absf absi maxi maxf mini minf clampi clampf lerpf sin cos tan asin acos atan atan2 sqrt pow exp log fmod fposmod
posmod move_toward smoothstep randf randi randf_range randi_range deg_to_rad rad_to_deg linear_to_db db_to_linear snappedf floorf ceilf roundf floori ceili
roundi signf signi is_equal_approx is_zero_approx len hash typeof sinh cosh tanh inverse_lerp lerp_angle remap wrapf wrapi randomize rand_from_seed
cubic_interpolate bezier_interpolate is_nan is_inf is_instance_valid is_instance_id_valid range var_to_str str_to_var load preload print printerr push_warning push_error'''.split())
VARIANT_BUILTINS = {'max', 'min', 'clamp', 'abs', 'sign', 'lerp', 'floor', 'ceil', 'round', 'snapped', 'wrap'}
CTOR = re.compile(r'^(Vector[234]i?|Color|Rect2i?|Transform[23]D|Basis|Quaternion|AABB|Plane|NodePath|StringName|Callable|Signal|Packed\w+Array|Array|Dictionary|String|int|float|bool|Projection|RID)\(')
GLOBAL_FUNCS = TYPED_BUILTINS | VARIANT_BUILTINS | {'assert', 'print_debug', 'print_rich', 'prints', 'printt', 'weakref', 'instance_from_id', 'seed', 'randfn', 'ease', 'step_decimals', 'pingpong', 'lerp', 'nearest_po2', 'type_string', 'is_same', 'str_to_var', 'bytes_to_var', 'var_to_bytes', 'get_stack', 'push_warning', 'push_error', 'rid_allocate_id'}
# Engine methods the project calls on itself (self / inherited). Extend when a new legitimate one shows up as a warning.
ENGINE_METHODS = set('''add_child remove_child get_children get_child get_parent get_tree get_viewport get_node get_node_or_null find_child queue_free
is_inside_tree add_to_group is_in_group get_nodes_in_group create_tween create_timer call_deferred set_deferred connect disconnect emit_signal has_meta
set_meta get_meta remove_meta has_method has_signal get_instance_id duplicate set_anchors_and_offsets_preset set_anchors_preset add_theme_color_override
add_theme_font_override add_theme_font_size_override add_theme_stylebox_override add_theme_constant_override set_process set_physics_process
set_process_input move_and_slide is_on_floor get_slide_collision get_slide_collision_count look_at look_at_from_position get_visible_rect
get_playback_position seek play stop emit tween_property tween_callback tween_interval tween_method set_parallel chain parallel set_trans set_ease
kill is_valid bind call callv unbind get_global_transform get_physics_process_delta_time get_process_delta_time to_global to_local
append append_array erase has size is_empty clear keys values get duplicate pop_back pop_front push_back push_front insert remove_at find sort
slice map filter reduce any all min max shuffle pick_random rfind substr begins_with ends_with replace split to_lower to_upper to_utf8_buffer
strip_edges is_valid_int to_int to_float lerp lerp_angle normalized length distance_to dot cross angle_to limit_length lightened darkened to_html from_hsv
srgb_to_linear linear_to_srgb get_modified_time file_exists get_open_error get_as_text store_string store_line get_length get_error close seek_end
open rename_absolute copy_absolute globalize_path parse_string stringify get_datetime_string_from_system get_date_dict_from_system get_unix_time_from_system
get_ticks_msec get_ticks_usec window_get_size get_display_safe_area has_feature is_debug_build action_get_events add_action action_add_event has_action
vibrate_handheld add_bus get_bus_index set_bus_name set_bus_send set_bus_mute set_bus_volume_db get_instance_id instantiate exists
get_surface_count surface_get_material set_surface_override_material get_active_material get_aabb set_color set_stylebox set_font set_font_size set_constant
set_value get_value set_height set_instance_transform restart set_cell reset_physics_interpolation textures get_mouse_position
get_closest_point is_action_pressed is_action_just_pressed get_action_strength get_vector start finished timeout set_text get_rect_size to_lower
looking_at quit set_camera_path notification propagate_notification set_pause_mode is_connected disconnect_all'''.split())
NODE_MEMBERS = set('name process_mode visible position rotation scale global_position global_transform transform basis modulate material_override mesh text value disabled'.split())


TARGETS: dict = {}


def strip_code(line: str) -> str:
    out, i, q = [], 0, None
    while i < len(line):
        c = line[i]
        if q:
            if c == '\\': i += 2; continue
            if c == q: q = None; out.append(c)
            i += 1; continue
        if c in '"\'': q = c; out.append(c); i += 1; continue
        if c == '#': break
        out.append(c); i += 1
    return ''.join(out)


class Script:
    def __init__(self, path: Path):
        self.path = path
        self.rel = path.relative_to(ROOT).as_posix()
        self.lines = path.read_text(encoding='utf-8').split('\n')
        self.code = [strip_code(l) for l in self.lines]
        self.class_name = None
        self.extends = None
        self.funcs: dict[str, dict] = {}
        self.members: dict[str, str] = {}
        self.signals: dict[str, int] = {}
        self.decl_types: dict[str, str] = {}
        self.parse()

    @staticmethod
    def split_args(arg_text: str) -> list[str]:
        parts, depth, cur = [], 0, []
        for ch in arg_text:
            if ch in '([{': depth += 1
            elif ch in ')]}': depth -= 1
            if ch == ',' and depth == 0: parts.append(''.join(cur)); cur = []
            else: cur.append(ch)
        if ''.join(cur).strip(): parts.append(''.join(cur))
        return [p for p in parts if p.strip()]

    def parse(self):
        depth_enum = None
        for i, raw in enumerate(self.code):
            if not raw.strip() or raw.startswith('\t') or raw.startswith(' '): continue
            s = raw.strip()
            m = re.match(r'class_name\s+(\w+)', s)
            if m: self.class_name = m.group(1)
            m = re.match(r'extends\s+(\w+)', s)
            if m: self.extends = m.group(1)
            m = re.match(r'(?:static\s+)?func\s+(\w+)\s*\((.*)\)\s*(?:->\s*([\w\.\[\]]+))?\s*:', s)
            if m:
                params = self.split_args(m.group(2))
                required = sum(1 for p in params if '=' not in p)
                self.funcs[m.group(1)] = dict(min=required, max=len(params), ret=m.group(3), line=i + 1, static=s.startswith('static'))
                self.members[m.group(1)] = 'func'
                continue
            m = re.match(r'signal\s+(\w+)\s*(?:\((.*)\))?', s)
            if m:
                self.signals[m.group(1)] = len(self.split_args(m.group(2) or ''))
                self.members[m.group(1)] = 'signal'
                continue
            m = re.match(r'enum\s*(\w*)\s*\{(.*)', s)
            if m:
                body = m.group(2)
                j = i
                while '}' not in body and j + 1 < len(self.code):
                    j += 1; body += ' ' + self.code[j].strip()
                if m.group(1): self.members[m.group(1)] = 'enum'
                for v in re.findall(r'(\w+)\s*(?:=[^,}]*)?(?:,|\})', body.split('}')[0] + ','):
                    self.members[v] = 'enumvalue'
                continue
            m = re.match(r'(?:@\w+(?:\([^)]*\))?\s+)*(?:static\s+)?(var|const)\s+(\w+)\s*(?::\s*([^=]+?))?\s*(?:(:?=)\s*(.*))?$', s)
            if m:
                self.members[m.group(2)] = m.group(1)
                self.decl_types[m.group(2)] = (m.group(3) or '').strip() + '|' + ((m.group(4) or '') + ' ' + (m.group(5) or ''))
        # locals and parameters (any indentation) - used to decide whether a subscript yields a typed value
        for raw in self.code:
            s2 = raw.strip()
            m = re.match(r'(?:var|const)\s+(\w+)\s*(?::\s*([^=]+?))?\s*(?:(:?=)\s*(.*))?$', s2)
            if m and m.group(1) not in self.decl_types:
                self.decl_types[m.group(1)] = (m.group(2) or '').strip() + '|' + ((m.group(3) or '') + ' ' + (m.group(4) or ''))
            m = re.match(r'(?:static\s+)?func\s+\w+\s*\((.*)\)', s2)
            if m:
                for prm in self.split_args(m.group(1)):
                    pm = re.match(r'\s*(\w+)\s*:\s*([^=]+?)\s*(?:=.*)?$', prm)
                    if pm and pm.group(1) not in self.decl_types:
                        self.decl_types[pm.group(1)] = pm.group(2).strip() + '|'


def load_project():
    proj = (ROOT / 'project.godot').read_text()
    autoloads = {n: p for n, p in re.findall(r'^(\w+)="\*res://([^"]+)"', proj, re.M)}
    scripts = {p.relative_to(ROOT).as_posix(): Script(p) for p in sorted(ROOT.rglob('*.gd')) if '.godot' not in p.parts}
    return proj, autoloads, scripts


def check(show_warnings=False):
    proj, autoloads, scripts = load_project()
    errors, warnings = [], []
    E = lambda s, ln, msg: errors.append(f'{s.rel}:{ln}: {msg}')
    W = lambda s, ln, msg: warnings.append(f'{s.rel}:{ln}: {msg}')
    by_class = {s.class_name: s for s in scripts.values() if s.class_name}
    auto_scripts = {n: scripts.get(p) for n, p in autoloads.items()}
    for n, p in autoloads.items():
        if p not in scripts: errors.append(f'project.godot: autoload {n} -> missing {p}')
    seen_classes = {}
    for s in scripts.values():
        if s.class_name:
            if s.class_name in autoloads: E(s, 1, f'class_name {s.class_name} hides the autoload singleton of the same name')
            if s.class_name in seen_classes: E(s, 1, f'duplicate class_name {s.class_name} (also {seen_classes[s.class_name]})')
            seen_classes[s.class_name] = s.rel
    targets = {**by_class, **{n: sc for n, sc in auto_scripts.items() if sc}}
    TARGETS.clear(); TARGETS.update(targets)

    for s in scripts.values():
        # ---- indentation + brackets
        stack = [0]; depth = 0; prev_colon = False; prev_indent = 0
        for i, (raw, code) in enumerate(zip(s.lines, s.code), 1):
            if not code.strip():
                continue
            lead = raw[:len(raw) - len(raw.lstrip('\t '))]
            if ' ' in lead and depth == 0: E(s, i, 'space indentation (use tabs)')
            indent = lead.count('\t')
            if depth == 0:
                if prev_colon and indent <= prev_indent: E(s, i, 'block expected after ":" but line is not indented')
                elif indent > prev_indent and not prev_colon: E(s, i, 'unexpected indentation')
                elif indent > prev_indent + 1: E(s, i, 'indentation jumps by more than one level')
                if indent < prev_indent:
                    while stack and stack[-1] > indent: stack.pop()
                    if not stack or stack[-1] != indent: E(s, i, "unindent doesn't match any enclosing block")
                if indent not in stack: stack.append(indent)
            for ch in code:
                if ch in '([{': depth += 1
                elif ch in ')]}': depth -= 1
            if depth < 0: E(s, i, 'unbalanced closing bracket'); depth = 0
            if depth == 0:
                prev_indent = indent
                prev_colon = code.rstrip().endswith(':')
        if depth != 0: E(s, len(s.lines), 'unbalanced brackets at end of file')

        # ---- joined logical statements for the semantic checks
        stmts = []; buf = ''; start = 0; d = 0
        for i, code in enumerate(s.code, 1):
            if d == 0 and not buf: start = i
            buf += ' ' + code.strip() if buf else code.strip()
            d += sum(code.count(c) for c in '([{') - sum(code.count(c) for c in ')]}')
            if d <= 0: stmts.append((start, buf)); buf = ''; d = 0
        local_vars = {}
        for ln, st in stmts:
            m = re.match(r'(?:@\w+(?:\([^)]*\))?\s+)*(?:static\s+)?(?:var|const)\s+(\w+)\s*:=\s*(.+)$', st)
            if m:
                rhs = m.group(2).strip()
                r = rhs_check(rhs, s, scripts, targets)
                if r: (E if r[0] == 'E' else W)(s, ln, f'`{m.group(1)} := {rhs[:70]}` - {r[1]}')

        # ---- cross references
        for ln, st in stmts:
            for m in re.finditer(r'\b([A-Z]\w*)\.(\w+)\s*(\()?', st):
                name, member, paren = m.group(1), m.group(2), m.group(3)
                tgt = targets.get(name)
                if tgt is None or tgt is s: continue
                if member not in tgt.members:
                    if member in NODE_MEMBERS or member in ENGINE_METHODS or member in ('new', 'free', 'name'): continue
                    E(s, ln, f'{name}.{member} does not exist in {tgt.rel}')
                    continue
                if paren and tgt.members[member] == 'func':
                    f = tgt.funcs[member]
                    argtext = arg_text_after(st, m.end() - 1)
                    n_args = len(Script.split_args(argtext))
                    if n_args < f['min'] or n_args > f['max']:
                        E(s, ln, f'{name}.{member}() called with {n_args} args, expects {f["min"]}..{f["max"]} ({tgt.rel}:{f["line"]})')
            for m in re.finditer(r'\b([a-z_]\w*)\.connect\(\s*([A-Za-z_][\w\.]*)\s*[,)]', st):
                handler = m.group(2)
                if '.' in handler:
                    owner, hm = handler.split('.', 1)
                    t2 = targets.get(owner)
                    if t2 and '.' not in hm and hm not in t2.members: E(s, ln, f'connect target {handler} does not exist')
                elif handler not in s.members and handler not in ENGINE_METHODS and handler[0].islower() and handler not in s.decl_types:
                    E(s, ln, f'connect target `{handler}` is not defined in this script')
            for m in re.finditer(r'\b(\w+)\.emit\(', st):
                sig = m.group(1)
                if sig in s.signals:
                    n = len(Script.split_args(arg_text_after(st, m.end() - 1)))
                    if n != s.signals[sig]: E(s, ln, f'signal {sig} emitted with {n} args, declared with {s.signals[sig]}')
            for m in re.finditer(r'"(res://[^"]+)"', st):
                path = m.group(1)
                if '%' in path or '{' in path: continue
                if not (ROOT / path[6:]).exists(): E(s, ln, f'missing resource {path}')
            # unknown plain function calls
            for m in re.finditer(r'(?<![\.\w])([a-z_]\w*)\s*\(', st):
                fn = m.group(1)
                if fn in KEYWORDS or fn in s.funcs or fn in GLOBAL_FUNCS or fn in ENGINE_METHODS or fn in s.members: continue
                if re.search(r'\bfunc\s+' + fn, st): continue
                W(s, ln, f'call to unknown function `{fn}()` (typo, or engine method missing from ENGINE_METHODS)')
        # duplicate functions
        names = [m.group(1) for c in s.code for m in [re.match(r'(?:static\s+)?func\s+(\w+)', c)] if m]
        for n in set(names):
            if names.count(n) > 1: E(s, 1, f'function {n} defined {names.count(n)} times')

    # ---- scenes / project resources
    for p in ROOT.rglob('*.tscn'):
        for m in re.finditer(r'path="(res://[^"]+)"', p.read_text()):
            if not (ROOT / m.group(1)[6:]).exists(): errors.append(f'{p.relative_to(ROOT)}: missing resource {m.group(1)}')
    for m in re.finditer(r'"(res://[^"]+)"', proj):
        if not (ROOT / m.group(1)[6:]).exists(): errors.append(f'project.godot: missing resource {m.group(1)}')
    return errors, warnings


def arg_text_after(text: str, open_index: int) -> str:
    depth = 0
    for j in range(open_index, len(text)):
        if text[j] == '(': depth += 1
        elif text[j] == ')':
            depth -= 1
            if depth == 0: return text[open_index + 1:j]
    return text[open_index + 1:]


def base_is_typed_indexable(base: str, s: Script) -> bool | None:
    """True: subscript yields a typed value. False: yields Variant. None: unknown."""
    leaf = base.split('.')[-1]
    if '.' in base and base.split('.')[0] not in ('self',):
        return None
    info = s.decl_types.get(leaf)
    if info is None:
        return None
    typ, rest = info.split('|', 1)
    if typ:
        if re.match(r'Array\[', typ) or re.match(r'Packed\w+Array', typ) or re.match(r'(Vector|Color|String|Basis|Transform)', typ): return True
        return False        # Array / Dictionary / Variant / ...
    rhs = rest.split('=', 1)[-1].strip()
    if re.match(r'(Packed\w+Array|Vector\d?i?|Color)\(', rhs) or rhs.startswith('"'): return True
    mm = re.match(r'^([A-Z]\w*)\.(\w+)\(', rhs)
    if mm and mm.group(1) in TARGETS and mm.group(2) in TARGETS[mm.group(1)].funcs:
        ret = TARGETS[mm.group(1)].funcs[mm.group(2)]['ret'] or ''
        return bool(re.match(r'Array\[|Packed\w+Array|Vector|String|Color', ret))
    return False


def rhs_check(rhs: str, s: Script, scripts, targets):
    r = rhs.strip()
    if r.startswith('null'): return ('E', 'cannot infer a type from null')
    if re.match(r'^(-?[\d\.]|"|\'|\[|\{|true\b|false\b|PI\b|TAU\b|INF\b|NAN\b|not\b|!)', r) or CTOR.match(r): return None
    if re.match(r'^[A-Z]\w*(\.\w+)*\.new\(', r): return None
    m = re.match(r'^(\w+)\(', r)
    if m:
        fn = m.group(1)
        if fn in VARIANT_BUILTINS: return ('E', f'`{fn}()` returns Variant; use {fn}i/{fn}f or an explicit type')
        if fn in s.funcs:
            ret = s.funcs[fn]['ret']
            if ret in (None, 'Variant'): return ('E', f'{fn}() has no return type annotation')
            return None
        return None
    m = re.match(r'^([A-Z]\w*)\.(\w+)\(', r)
    if m and m.group(1) in targets and m.group(2) in targets[m.group(1)].funcs:
        ret = targets[m.group(1)].funcs[m.group(2)]['ret']
        if ret in (None, 'Variant'): return ('E', f'{m.group(1)}.{m.group(2)}() has no return type annotation')
        return None
    # chained call/subscript ending in an index, e.g. foo.filter(...)[0]
    if r.endswith(']') and not r.startswith('('):
        m = re.match(r'^([A-Za-z_][\w\.]*)\[', r)
        if m and '(' not in m.group(1):
            t = base_is_typed_indexable(m.group(1), s)
            if t is False: return ('E', f'indexing `{m.group(1)}` yields Variant; add an explicit type')
            if t is None:
                if m.group(1).split('.')[0] in targets or m.group(1).split('.')[0] in ('SaveService',): return ('E', f'indexing `{m.group(1)}` yields Variant; add an explicit type')
                return ('W', 'subscript result may be Variant; add an explicit type')
        elif re.search(r'\)\[[^\]]*\]$', r):
            return ('E', 'indexing a call result yields Variant; add an explicit type')
    if re.search(r'\.get\([^()]*\)$', r) and not r.startswith('('):
        return ('W', '`.get()` returns Variant; add an explicit type')
    if re.search(r'\.(pop_front|pop_back|front|back|pick_random)\(\)$', r):
        return ('W', 'element accessor may return Variant for untyped arrays; add an explicit type')
    return None


def main():
    errors, warnings = check()
    show = '--warn' in sys.argv
    for e in errors: print('ERROR  ', e)
    if show:
        for w in warnings: print('warning', w)
    print(f'\n{len(errors)} error(s), {len(warnings)} warning(s) in {len(list(ROOT.rglob("*.gd")))} scripts')
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
