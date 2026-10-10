"""Bounded, layout-aware HID sequences; no host process is needed for playback."""
from .layouts import characters, alt_mask, canonical

MAX_TEXT = 512
MAX_EVENTS = 256
MAX_EXPANDED = 2048
MAX_DURATION = 120000


def integer(value, low, high, message):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(message)
    return value


def text_value(value):
    if not isinstance(value, str) or not 1 <= len(value) <= MAX_TEXT:
        raise ValueError("Text needs 1–512 characters")
    return value.replace("\r\n", "\n").replace("\r", "\n")


def clean_action(action):
    if action.get("kind") == "text":
        return {"kind": "text", "text": text_value(action.get("text"))}
    steps = action.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_EVENTS:
        raise ValueError("A macro needs 1–256 events")
    clean = []
    for step in steps:
        if not isinstance(step, dict):
            raise ValueError("Invalid macro event")
        kind = step.get("kind")
        if kind == "event":
            device = step.get("device")
            bounds = {"keyboard": (4, 115), "modifier": (0, 7), "media": (0, 7)}
            if device not in bounds or type(step.get("pressed")) is not bool:
                raise ValueError("Invalid recorded key event")
            usage = integer(step.get("usage"), *bounds[device], "Invalid recorded usage")
            clean.append({"kind": kind, "device": device, "usage": usage, "pressed": step["pressed"]})
        elif kind == "delay":
            clean.append({"kind": kind, "ms": integer(step.get("ms"), 0, MAX_DURATION, "Invalid macro delay")})
        elif kind == "text":
            clean.append({"kind": kind, "text": text_value(step.get("text"))})
        elif kind == "keyboard":
            clean.append({"kind": kind, "usage": integer(step.get("usage"), 4, 115, "Invalid shortcut key"),
                          "modifiers": integer(step.get("modifiers"), 0, 255, "Invalid shortcut modifiers")})
        elif kind == "media":
            clean.append({"kind": kind, "usage": integer(step.get("usage"), 0, 7, "Invalid media action")})
        else:
            raise ValueError("Unknown macro event")
    return {"kind": "macro", "steps": clean}


def event(device, usage, pressed):
    return {"kind": "event", "device": device, "usage": usage, "pressed": pressed}


def tap(usage, mask=0, device="keyboard"):
    modifiers = [event("modifier", bit, True) for bit in range(8) if mask & (1 << bit)]
    return modifiers + [event(device, usage, True), {"kind": "delay", "ms": 15},
                        event(device, usage, False)] + [dict(item, pressed=False) for item in reversed(modifiers)] + [{"kind": "delay", "ms": 15}]


def compile_text(value, layout):
    reverse = {}
    for (usage, shifted, option), character in characters(layout).items():
        reverse.setdefault(character, (usage, (2 if shifted else 0) | (alt_mask(layout) if option else 0)))
    reverse.update({" ": (44, 0), "\t": (43, 0), "\n": (40, 0)})
    result = []
    unsupported = []
    for character in value:
        chord = reverse.get(character)
        if chord is None:
            unsupported.append(repr(character))
            continue
        result.extend(tap(*chord))
        # German circumflex/acute/grave are dead keys. A following Space
        # produces the literal accent rather than modifying the next letter.
        if canonical(layout) != "us" and character in "^´`":
            result.extend(tap(44))
    if unsupported:
        raise ValueError("This layout cannot type: " + ", ".join(dict.fromkeys(unsupported)))
    return result


def compile_action(action, layout):
    action = clean_action(action)
    steps = [{"kind": "text", "text": action["text"]}] if action["kind"] == "text" else action["steps"]
    output, down = [], set()
    for step in steps:
        kind = step["kind"]
        if kind == "event":
            identity = (step["device"], step["usage"])
            if step["pressed"]:
                if identity in down:
                    raise ValueError("Macro presses an already held key")
                down.add(identity)
                if sum(device == "keyboard" for device, _ in down) > 12:
                    raise ValueError("A macro can hold at most 12 keyboard keys")
            else:
                if identity not in down:
                    raise ValueError("Macro releases a key that is not held")
                down.remove(identity)
            output.append(step)
        elif kind == "delay":
            output.append(step)
        else:
            if down:
                raise ValueError("Release recorded keys before inserting text, shortcuts, or media")
            output.extend(compile_text(step["text"], layout) if kind == "text" else
                          tap(step["usage"], step.get("modifiers", 0), "media" if kind == "media" else "keyboard"))
    if down:
        raise ValueError("Macro must release every pressed key and modifier")
    if len(output) > MAX_EXPANDED:
        raise ValueError("Sequence exceeds 2,048 playback events")
    # The scheduler emits at most one HID transition per millisecond tick.
    duration = sum(max(1, item.get("ms", 1)) for item in output)
    if duration > MAX_DURATION:
        raise ValueError("Sequence exceeds 120 seconds")
    return output


def has_sequences(profile):
    return any(key["kind"] in ("text", "macro") for layer in profile.get("layers", []) for key in layer["keys"])
