"""Computer-local view preferences, independent of device profiles and HTTP ports."""

import json

from .firmware_update import backup_root


def path():
    return backup_root().parent / "preferences.json"


def read():
    try:
        value = json.loads(path().read_text(encoding="utf-8"))
        angle = value.get("orientation")
        if type(angle) is int and angle in (0, 90, 180, 270):
            return {"orientation": angle}
    except (OSError, ValueError, AttributeError):
        pass
    return {"orientation": 0}


def write(value):
    angle = value.get("orientation")
    if type(angle) is not int or angle not in (0, 90, 180, 270):
        raise ValueError("Invalid view orientation")
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps({"orientation": angle}) + "\n", encoding="utf-8")
    temporary.replace(target)
    return {"orientation": angle}
