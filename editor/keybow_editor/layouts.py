"""US and German host key legends and safe profile translation."""

import copy
import locale
import re
import subprocess
import sys

LAYOUTS = {"us": "US English", "de-macos": "German (macOS)",
           "de-windows": "German (Windows)", "de-linux": "German (Linux)"}
LEGACY_LAYOUTS = {"de": "de-macos"}

def host_layout(platform=None, language=None):
    platform = sys.platform if platform is None else platform
    if language is None:
        language = active_language(platform) or locale.getlocale()[0] or ""
    if not language.lower().startswith("de"):
        return "us"
    return "de-windows" if platform == "win32" else "de-macos" if platform == "darwin" else "de-linux"

def active_language(platform):
    """Best-effort active keyboard input source; None means use the locale."""
    try:
        if platform == "darwin":
            value = subprocess.run(
                ["defaults", "read", "com.apple.HIToolbox", "AppleCurrentKeyboardLayoutInputSourceID"],
                capture_output=True, text=True, timeout=2, check=True).stdout.strip()
            return "de" if ".German" in value else "us" if ".US" in value or ".ABC" in value else None
        if platform == "win32":
            import ctypes
            language_id = ctypes.windll.user32.GetKeyboardLayout(0) & 0x3ff
            return "de" if language_id == 0x07 else "us" if language_id == 0x09 else None
        if platform.startswith("linux"):
            for command in (["gsettings", "get", "org.gnome.desktop.input-sources", "mru-sources"],
                            ["setxkbmap", "-query"]):
                try:
                    value = subprocess.run(command, capture_output=True, text=True,
                                           timeout=2, check=True).stdout
                except (OSError, subprocess.SubprocessError):
                    continue
                if command[0] == "gsettings":
                    layouts = re.findall(r"\('xkb',\s*'([^']+)'\)", value)
                    if not layouts:
                        continue
                    layout = layouts[0].split("+")[0]
                else:
                    match = re.search(r"^layout:\s*([^\s,]+)", value, re.M)
                    if not match:
                        continue
                    layout = match.group(1)
                return "de" if layout == "de" else "us" if layout == "us" else None
    except (OSError, subprocess.SubprocessError, AttributeError):
        pass
    return None

def canonical(layout):
    return LEGACY_LAYOUTS.get(layout, layout)

def alt_mask(layout):
    return 0x04 if canonical(layout) == "de-macos" else 0x40 if canonical(layout) in ("de-windows", "de-linux") else 0x04

# USB keyboard usages describe key positions. These tables describe the
# characters produced by the supported input sources for these chords.
BASE = {
    "us": {
        30: ("1", "!"), 31: ("2", "@"), 32: ("3", "#"),
        33: ("4", "$"), 34: ("5", "%"), 35: ("6", "^"),
        36: ("7", "&"), 37: ("8", "*"), 38: ("9", "("),
        39: ("0", ")"), 45: ("-", "_"), 46: ("=", "+"),
        47: ("[", "{"), 48: ("]", "}"), 49: ("\\", "|"),
        51: (";", ":"), 52: ("'", '"'), 53: ("`", "~"),
        54: (",", "<"), 55: (".", ">"), 56: ("/", "?"),
    },
    "de-macos": {
        30: ("1", "!"), 31: ("2", '"'), 32: ("3", "§"),
        33: ("4", "$"), 34: ("5", "%"), 35: ("6", "&"),
        36: ("7", "/"), 37: ("8", "("), 38: ("9", ")"),
        39: ("0", "="), 45: ("ß", "?"), 46: ("´", "`"),
        47: ("ü", "Ü"), 48: ("+", "*"), 49: ("#", "'"),
        51: ("ö", "Ö"), 52: ("ä", "Ä"), 53: ("^", "°"),
        54: (",", ";"), 55: (".", ":"), 56: ("-", "_"),
        100: ("<", ">"),
    },
}

# The German Mac layout has these direct Option chords. Dead-key sequences
# are deliberately omitted because one key action cannot type them safely.
OPTION = {
    "de-macos": {(15, False): "@", (8, False): "€", (34, False): "[",
           (35, False): "]", (36, False): "|", (37, False): "{",
           (38, False): "}", (36, True): "\\"},
    "de-windows": {(20, False): "@", (8, False): "€", (36, False): "{",
                   (37, False): "[", (38, False): "]", (39, False): "}",
                   (45, False): "\\"},
    "de-linux": {(20, False): "@", (8, False): "€", (36, False): "{",
                 (37, False): "[", (38, False): "]", (39, False): "}",
                 (45, False): "\\"},
    "us": {},
}


def characters(layout):
    layout = canonical(layout)
    if layout not in LAYOUTS:
        raise ValueError("Unknown keyboard layout")
    result = {}
    for usage in range(4, 30):
        letter = chr(ord("a") + usage - 4)
        if layout != "us" and letter in "yz":
            letter = "z" if letter == "y" else "y"
        result[(usage, False, False)] = letter
        result[(usage, True, False)] = letter.upper()
    for usage, pair in BASE["de-macos" if layout != "us" else "us"].items():
        result[(usage, False, False)] = pair[0]
        result[(usage, True, False)] = pair[1]
    for (usage, shifted), character in OPTION[layout].items():
        result[(usage, shifted, True)] = character
    return result


def labels(layout, options):
    table = characters(layout)
    result = []
    for entry in options:
        item = dict(entry)
        character = table.get((item["usage"], False, False))
        if character:
            item["label"] = character if character == "ß" else character.upper() if character.isalpha() else character
        result.append(item)
    return result


def translate(profile, target):
    """Return a translated copy, or raise with one-based untranslatable keys."""
    source = canonical(profile.get("layout", "us"))
    target = canonical(target)
    if target not in LAYOUTS or source not in LAYOUTS:
        raise ValueError("Unknown keyboard layout")
    result = copy.deepcopy(profile)
    if source == target:
        result["layout"] = target
        return result
    old = characters(source)
    new = characters(target)
    reverse = {}
    for chord, character in new.items():
        reverse.setdefault(character, chord)
    unsupported = []
    if result["version"] >= 3:
        groups = ((layer["name"], layer["keys"]) for layer in result["layers"])
    else:
        groups = (("Profile", result["keys"]),)
    for layer_name, keys in groups:
        for index, action in enumerate(keys, 1):
            if action["kind"] != "keyboard":
                continue
            mask = action["modifiers"]
            shift = bool(mask & 0x22)
            option = bool(mask & alt_mask(source))
            if ((source == "de-macos" and target in ("de-windows", "de-linux")
                 or target == "de-macos" and source in ("de-windows", "de-linux"))
                    and mask & 0x88):
                unsupported.append(f"{layer_name} key {index:02}")
                continue
            # A PC's left Alt is a shortcut modifier, not German AltGr. A
            # Mac's Option is a character modifier. Do not silently convert
            # an ambiguous Alt shortcut when crossing that boundary.
            if (source != "de-macos" and target == "de-macos" and mask & 0x04
                    or source == "us" and mask & 0x40):
                unsupported.append(f"{layer_name} key {index:02}")
                continue
            chord = (action["usage"], shift, option)
            if chord not in old:
                if action["usage"] in {40, 41, 42, 43, 44, 57, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82} or 58 <= action["usage"] <= 99 or 101 <= action["usage"] <= 115:
                    continue
                unsupported.append(f"{layer_name} key {index:02}")
                continue
            replacement = reverse.get(old[chord])
            if replacement is None:
                unsupported.append(f"{layer_name} key {index:02}")
                continue
            usage, new_shift, new_option = replacement
            # Keep Control and Command, while replacing only the modifiers needed
            # to produce the same printable character in the target input source.
            new_mask = mask & ~(0x22 | alt_mask(source))
            if new_shift:
                new_mask |= 0x02
            if new_option:
                new_mask |= alt_mask(target)
            action["usage"] = usage
            action["modifiers"] = new_mask
    if unsupported:
        keys = ", ".join(unsupported)
        raise ValueError(f"Cannot preserve {keys} in {LAYOUTS[target]}; change those assignments first")
    result["layout"] = target
    return result
