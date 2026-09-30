"""Validated visual profiles and deterministic Lua generation."""

import base64
import json
import re

from .layouts import LAYOUTS, canonical, labels

MAX_SOURCE = 15000
PROFILE_ID = re.compile(r"[a-z0-9-]{1,32}\Z")
PRESETS = (
    "default", "animated-pastel-rainbow", "animated-rainbow",
    "animated-tropical", "blue-pulse", "heartbeat", "rainbow", "snow",
    "static-blue-red-green", "static-rainbow", "static-tropical", "tropical",
)
MEDIA = (
    "Next track", "Previous track", "Stop", "Eject", "Play / pause",
    "Mute", "Volume up", "Volume down",
)


def key_options(layout="us"):
    options = [
        {"usage": index, "label": chr(65 + index - 4)} for index in range(4, 30)
    ]
    options += [{"usage": 30 + i, "label": str((i + 1) % 10)} for i in range(10)]
    options += [
        {"usage": 40, "label": "Enter"}, {"usage": 41, "label": "Escape"},
        {"usage": 42, "label": "Backspace"}, {"usage": 43, "label": "Tab"},
        {"usage": 44, "label": "Space"}, {"usage": 57, "label": "Caps Lock"},
        {"usage": 45, "label": "-"}, {"usage": 46, "label": "="},
        {"usage": 47, "label": "["}, {"usage": 48, "label": "]"},
        {"usage": 49, "label": "Backslash"}, {"usage": 51, "label": ";"},
        {"usage": 52, "label": "Apostrophe"}, {"usage": 53, "label": "Grave accent"},
        {"usage": 54, "label": ","}, {"usage": 55, "label": "."},
        {"usage": 56, "label": "/"},
        {"usage": 100, "label": "ISO key"},
        {"usage": 73, "label": "Insert"}, {"usage": 74, "label": "Home"},
        {"usage": 75, "label": "Page up"}, {"usage": 76, "label": "Delete"},
        {"usage": 77, "label": "End"}, {"usage": 78, "label": "Page down"},
        {"usage": 79, "label": "Right arrow"}, {"usage": 80, "label": "Left arrow"},
        {"usage": 81, "label": "Down arrow"}, {"usage": 82, "label": "Up arrow"},
    ]
    options += [{"usage": 58 + i, "label": f"F{i + 1}"} for i in range(12)]
    options += [{"usage": 104 + i, "label": f"F{i + 13}"} for i in range(12)]
    options += [{"usage": 89 + i, "label": f"Keypad {i + 1}"} for i in range(9)]
    options += [
        {"usage": 84, "label": "Keypad /"},
        {"usage": 85, "label": "Keypad *"},
        {"usage": 86, "label": "Keypad -"},
        {"usage": 87, "label": "Keypad +"},
        {"usage": 88, "label": "Keypad Enter"},
        {"usage": 98, "label": "Keypad 0"},
        {"usage": 99, "label": "Keypad ."},
        {"usage": 103, "label": "Keypad ="},
    ]
    return labels(layout, options)


def default_profile():
    usages = [98, 89, 90, 91, 92, 93, 94, 95, 96, 97, 99, 103]
    return {
        "version": 1,
        "id": "default",
        "name": "Number pad",
        "keys": [
            {"kind": "keyboard", "usage": usage, "modifiers": 0}
            for usage in usages
        ],
        "lighting": {"mode": "preset", "preset": "default"},
    }


def validate(profile):
    if not isinstance(profile, dict) or profile.get("version") not in (1, 2, 3, 4):
        raise ValueError("Unsupported profile version")
    version = profile["version"]
    if version >= 2 and profile.get("layout") not in (LAYOUTS if version == 4 else ("us", "de")):
        raise ValueError("Unknown keyboard layout")
    identifier = profile.get("id")
    name = profile.get("name")
    if not isinstance(identifier, str) or not PROFILE_ID.fullmatch(identifier):
        raise ValueError("Profile ID must contain lowercase letters, digits, or hyphens")
    if not isinstance(name, str) or not 1 <= len(name) <= 48 or any(ord(c) < 32 for c in name):
        raise ValueError("Profile name must be 1–48 printable characters")
    if version >= 3:
        layers = profile.get("layers")
        if not isinstance(layers, list) or not 1 <= len(layers) <= 4:
            raise ValueError("A profile needs one to four layers")
        clean_layers = []
        for layer in layers:
            if not isinstance(layer, dict):
                raise ValueError("Invalid layer")
            layer_id, layer_name = layer.get("id"), layer.get("name")
            if not isinstance(layer_id, str) or not PROFILE_ID.fullmatch(layer_id):
                raise ValueError("Invalid layer ID")
            if not isinstance(layer_name, str) or not 1 <= len(layer_name) <= 48 or any(ord(c) < 32 for c in layer_name):
                raise ValueError("Layer name must be 1–48 printable characters")
            clean = _validate_contents(layer, allow_layers=True)
            clean_layers.append({"id": layer_id, "name": layer_name, **clean})
        ids = [layer["id"] for layer in clean_layers]
        if ids[0] != "base" or len(set(ids)) != len(ids):
            raise ValueError("The first layer must be the unique base layer")
        by_id = {layer["id"]: layer for layer in clean_layers}
        for layer in clean_layers:
            for index, action in enumerate(layer["keys"]):
                if action["kind"] != "layer":
                    continue
                target = action["target"]
                if target not in by_id or target == layer["id"]:
                    raise ValueError(f"Invalid layer target on key {index + 1:02}")
                if action["mode"] == "toggle" and by_id[target]["keys"][index]["kind"] != "none":
                    raise ValueError(f"Key {index + 1:02} on {by_id[target]['name']} must be unassigned for toggle return")
        return {"version": version, "id": identifier, "name": name,
                "layout": profile["layout"], "layers": clean_layers}
    clean = _validate_contents(profile, allow_layers=False)
    result = {"version": version, "id": identifier, "name": name, **clean}
    if version == 2:
        result["layout"] = profile["layout"]
    return result


def _validate_contents(profile, allow_layers):
    keys = profile.get("keys")
    if not isinstance(keys, list) or len(keys) != 12:
        raise ValueError("A profile needs exactly 12 keys")
    clean_keys = []
    for action in keys:
        if not isinstance(action, dict):
            raise ValueError("Invalid key action")
        kind = action.get("kind")
        if kind == "keyboard":
            usage, modifiers = action.get("usage"), action.get("modifiers")
            if type(usage) is not int or not 4 <= usage <= 231:
                raise ValueError("Invalid keyboard usage")
            if type(modifiers) is not int or not 0 <= modifiers <= 255:
                raise ValueError("Invalid modifier mask")
            clean_keys.append({"kind": kind, "usage": usage, "modifiers": modifiers})
        elif kind == "media":
            usage = action.get("usage")
            if type(usage) is not int or not 0 <= usage < len(MEDIA):
                raise ValueError("Invalid media usage")
            clean_keys.append({"kind": kind, "usage": usage})
        elif kind == "none":
            clean_keys.append({"kind": kind})
        elif kind == "layer" and allow_layers:
            target, mode = action.get("target"), action.get("mode")
            if not isinstance(target, str) or not PROFILE_ID.fullmatch(target) or mode not in ("toggle", "hold", "timed"):
                raise ValueError("Invalid layer switch")
            clean_action = {"kind": "layer", "target": target, "mode": mode}
            if mode == "timed":
                seconds = action.get("seconds")
                if type(seconds) is not int or not 1 <= seconds <= 3600:
                    raise ValueError("Timed layers need 1–3600 seconds")
                clean_action["seconds"] = seconds
            clean_keys.append(clean_action)
        else:
            raise ValueError("Invalid key action")
    lighting = profile.get("lighting")
    if not isinstance(lighting, dict):
        raise ValueError("Invalid lighting")
    if lighting.get("mode") == "preset":
        if lighting.get("preset") not in PRESETS:
            raise ValueError("Unknown lighting preset")
        clean_lighting = {"mode": "preset", "preset": lighting["preset"]}
    elif lighting.get("mode") == "static":
        colors = lighting.get("colors")
        if not isinstance(colors, list) or len(colors) != 12 or any(
            not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color)
            for color in colors
        ):
            raise ValueError("Static lighting needs 12 hex colors")
        clean_lighting = {"mode": "static", "colors": [c.lower() for c in colors]}
    else:
        raise ValueError("Invalid lighting mode")
    return {"keys": clean_keys, "lighting": clean_lighting}


def upgrade(profile):
    """Convert an old profile in memory; the device changes only on save."""
    profile = validate(profile)
    if profile["version"] < 3:
        profile = {"version": 4, "id": profile["id"], "name": profile["name"],
                   "layout": canonical(profile.get("layout", "us")),
                   "layers": [{"id": "base", "name": "Base", "keys": profile["keys"],
                               "lighting": profile["lighting"]}]}
    elif profile["version"] == 3:
        profile["version"] = 4
        profile["layout"] = canonical(profile["layout"])
    return profile


def generate_lua(profile):
    profile = validate(profile)
    metadata = base64.urlsafe_b64encode(
        json.dumps(profile, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).decode("ascii").rstrip("=")
    if profile["version"] >= 3:
        lines = [f"-- keybow-profile-v{profile['version']}:{metadata}", "return {version=3,layers={"]
        for layer in profile["layers"]:
            lines.append(f'{{id="{layer["id"]}",keys={{')
            for action in layer["keys"]:
                if action["kind"] == "none":
                    lines.append('{kind="none"},')
                elif action["kind"] == "keyboard":
                    lines.append(f'{{kind="keyboard",usage={action["usage"]},modifiers={action["modifiers"]}}},')
                elif action["kind"] == "media":
                    lines.append(f'{{kind="media",usage={action["usage"]}}},')
                else:
                    duration = f',seconds={action["seconds"]}' if action["mode"] == "timed" else ""
                    lines.append(f'{{kind="layer",target="{action["target"]}",mode="{action["mode"]}"{duration}}},')
            lighting = layer["lighting"]
            if lighting["mode"] == "preset":
                lines.append(f'}},lighting={{mode="preset",preset="{lighting["preset"]}"}}}},')
            else:
                colors = ",".join(f'"{color}"' for color in lighting["colors"])
                lines.append(f'}},lighting={{mode="static",colors={{{colors}}}}}}},')
        lines.extend(["}}", ""])
        source = "\n".join(lines)
        if len(source.encode("utf-8")) > MAX_SOURCE:
            raise ValueError("Profile exceeds device limit")
        return source
    lines = [
        f"-- keybow-profile-v{profile['version']}:{metadata}",
        'require "keybow"',
        "local key_refs, mod_refs, media_refs = {}, {}, {}",
        "local function change(refs, code, pressed, setter)",
        "  local before = refs[code] or 0",
        "  local after = math.max(0, before + (pressed and 1 or -1))",
        "  refs[code] = after",
        "  if (before == 0) ~= (after == 0) then setter(code, after > 0) end",
        "end",
        "local function keyboard(usage, mask, pressed)",
        "  if pressed then",
        "    for bit = 0, 7 do if (mask & (1 << bit)) ~= 0 then",
        "      change(mod_refs, bit, true, keybow.set_modifier)",
        "    end end",
        "    change(key_refs, usage, true, keybow.set_key)",
        "  else",
        "    change(key_refs, usage, false, keybow.set_key)",
        "    for bit = 0, 7 do if (mask & (1 << bit)) ~= 0 then",
        "      change(mod_refs, bit, false, keybow.set_modifier)",
        "    end end",
        "  end",
        "end",
    ]
    for index, action in enumerate(profile["keys"]):
        if action["kind"] == "keyboard":
            body = f'keyboard({action["usage"]}, {action["modifiers"]}, pressed)'
        elif action["kind"] == "media":
            body = f'change(media_refs, {action["usage"]}, pressed, keybow.set_media_key)'
        else:
            body = ""  # A comment here would swallow the function's `end`.
        lines.append(f"function handle_key_{index:02}(pressed) {body} end")
    lines.append("function setup()")
    lighting = profile["lighting"]
    if lighting["mode"] == "static":
        lines.append("  keybow.auto_lights(false)")
        for index, color in enumerate(lighting["colors"]):
            rgb = [int(color[offset:offset + 2], 16) for offset in (1, 3, 5)]
            lines.append(f"  keybow.set_pixel({index}, {rgb[0]}, {rgb[1]}, {rgb[2]})")
    else:
        pattern = lighting["preset"]
        path = "default" if pattern == "default" else f"patterns/{pattern}"
        lines.append(f'  assert(keybow.load_pattern("{path}"), "Pattern unavailable")')
        lines.append("  keybow.auto_lights(true)")
    lines += ["end", ""]
    source = "\n".join(lines)
    if len(source.encode("utf-8")) > MAX_SOURCE:
        raise ValueError("Profile exceeds device limit")
    return source


def parse_lua(source):
    first = source.splitlines()[0]
    match = re.fullmatch(r"-- keybow-profile-v([1234]):([A-Za-z0-9_-]+)", first)
    if not match:
        raise ValueError("This profile was not generated by the visual editor")
    encoded = match.group(2)
    profile = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    profile = validate(profile)
    if profile["version"] != int(match.group(1)):
        raise ValueError("Profile metadata version differs from source")
    if generate_lua(profile) != source:
        raise ValueError("Profile metadata and Lua source differ")
    return profile
