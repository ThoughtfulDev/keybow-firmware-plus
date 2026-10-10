import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "editor"))
from keybow_editor.profile import default_profile, upgrade, generate_lua, parse_lua, validate
from keybow_editor.sequences import compile_action, compile_text, event, tap
from keybow_editor.layouts import translate

ROOT = Path(__file__).resolve().parents[1]


def profile(action, layout="us"):
    result = upgrade(default_profile())
    result["layout"] = layout
    result["layers"][0]["keys"][0] = action
    return result


class Sequences(unittest.TestCase):
    def test_roundtrip_and_old_versions(self):
        for version in (1, 2, 3, 4, 5):
            old = default_profile() if version < 3 else upgrade(default_profile())
            old["version"] = version
            if version == 2: old["layout"] = "us"
            modern = upgrade(old)
            self.assertEqual(modern["version"], 5)
            self.assertEqual(parse_lua(generate_lua(old)), old)
        for action in ({"kind":"text", "text":"Hello\n"},
                       {"kind":"macro", "steps":[{"kind":"keyboard", "usage":4,"modifiers":1}, {"kind":"text","text":"test"}]}):
            p = profile(action)
            source = generate_lua(p)
            self.assertIn("return {version=4,layers={", source)
            self.assertEqual(parse_lua(source), p)
        old = profile({"kind":"text", "text":"Hello"}); old["version"] = 4
        with self.assertRaises(ValueError): validate(old)

    def test_text_layouts_and_deadkeys(self):
        for layout in ("us", "de-macos", "de-windows", "de-linux"):
            sequence = compile_action({"kind":"text", "text":"Az @!\t\n"}, layout)
            self.assertTrue(any(item.get("usage") == 43 for item in sequence))
            self.assertTrue(any(item.get("usage") == 40 for item in sequence))
            self.assertEqual(sum(item.get("device") == "keyboard" and item.get("pressed") for item in sequence), 7)
        for layout in ("de-macos", "de-windows", "de-linux"):
            self.assertTrue(compile_text("äÖüß€", layout))
            accents = compile_text("^´`", layout)
            self.assertEqual(sum(item.get("usage") == 44 and item.get("pressed") for item in accents), 3)
        for text in ("ä", "🙂", "\x00"):
            with self.assertRaises(ValueError): compile_action({"kind":"text", "text":text}, "us")
        with self.assertRaisesRegex(ValueError, "key 01"):
            validate(profile({"kind":"text", "text":"🙂"}))
        p = profile({"kind":"text", "text":"Yz @"})
        self.assertEqual(translate(p, "de-windows")["layers"][0]["keys"][0]["text"], "Yz @")

    def test_event_validation_and_limits(self):
        down, up = event("keyboard",4,True), event("keyboard",4,False)
        steps = [down, event("keyboard",5,True), {"kind":"delay","ms":10}, up, event("keyboard",5,False)]
        self.assertEqual(compile_action({"kind":"macro","steps":steps}, "us"), steps)
        for invalid in ([down], [up], [down,down,up], [down, {"kind":"text","text":"a"}, up],
                        [{"kind":"delay","ms":120000}, down,up], [{"kind":"delay","ms":True}],
                        [{"kind":"event","device":"shell","usage":4,"pressed":True}],
                        [{"kind":"delay","ms":0}]*257):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                compile_action({"kind":"macro","steps":invalid}, "us")
        for text in ("", "a"*513, "A"*512):
            with self.assertRaises(ValueError): compile_action({"kind":"text","text":text}, "us")
        oversized = profile({"kind":"text","text":"a"*150})
        for i in range(3):
            additional = copy.deepcopy(oversized["layers"][0])
            additional.update(id=f"extra-{i}",name=f"Extra {i}")
            oversized["layers"].append(additional)
        with self.assertRaisesRegex(ValueError, "device limit"):
            generate_lua(oversized)
        self.assertLess(len(generate_lua(profile({"kind":"text","text":"a"*512})).encode()), 15000)

    def test_recording_translation(self):
        steps = [event("modifier",0,True), event("keyboard",29,True), {"kind":"delay","ms":25},
                 event("keyboard",29,False),event("modifier",0,False)]
        p = profile({"kind":"macro","steps":steps})
        for layout in ("de-macos", "de-windows", "de-linux"):
            converted = translate(p, layout)
            translated = converted["layers"][0]["keys"][0]["steps"]
            self.assertEqual(translated[1]["usage"], 28)
            self.assertEqual(translated[2], steps[2])
            self.assertEqual(translate(converted,"us")["layers"],p["layers"])
        shifted = profile({"kind":"macro","steps":[event("modifier",1,True), event("keyboard",31,True),
            {"kind":"delay","ms":20},event("keyboard",31,False),event("modifier",1,False)]})
        changed = translate(shifted,"de-windows")
        self.assertIn(event("modifier",6,True), changed["layers"][0]["keys"][0]["steps"])
        compile_action(changed["layers"][0]["keys"][0], "de-windows")
        shifted["layers"][0]["keys"][0]["steps"].insert(2,event("keyboard",4,True))
        shifted["layers"][0]["keys"][0]["steps"].insert(4,event("keyboard",4,False))
        with self.assertRaisesRegex(ValueError,"key 01.*overlapping"):
            translate(shifted,"de-windows")

    @unittest.skipUnless(shutil.which("node"), "Node unavailable")
    def test_recorder(self):
        subprocess.run(["node", "tests/sequence-recorder-test.js"],cwd=ROOT,check=True)

    @unittest.skipUnless(shutil.which("lua"), "Lua unavailable")
    def test_scheduler(self):
        steps = [event("modifier",0,True), event("keyboard",4,True), {"kind":"delay","ms":100},
                 event("keyboard",4,False),event("modifier",0,False)]
        p = profile({"kind":"macro","steps":steps})
        p["layers"][0]["keys"][2] = {"kind":"layer", "target":"other", "mode":"toggle"}
        p["layers"][0]["keys"][3] = {"kind":"text", "text":"B"}
        p["layers"].append({"id":"other", "name":"Other","keys":[{"kind":"none"} for _ in range(12)],"lighting":{"mode":"static","colors":["#123456"]*12}})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);(root/"profiles").mkdir()
            (root/"profiles/default.lua").write_text(generate_lua(p))
            script = '''
local now, transitions, down, lights, fail = 0, {}, {}, 0, false
keybow_get_millis = function() return now end
local function setter(device)
    return function(code, pressed)
        down[device..code] = pressed and true or nil
        transitions[#transitions+1] = device..code..tostring(pressed)
        if fail and pressed then error('HID error') end
    end
end
keybow_set_key = setter('k'); keybow_set_modifier = setter('m'); keybow_set_media_key = setter('c')
keybow_auto_lights = function() lights = lights + 1 end
keybow_set_pixel = function() lights = lights + 1 end
keybow_load_pattern = function() return true end
LOADER
setup()
local function advance(t) now=t; tick(now) end
handle_key_01(true) -- keypad key held before macro
assert(down.k89)
handle_key_00(true); handle_key_00(false) -- trigger release does not stop playback
assert(not down.k89)
advance(0); assert(down.m0)
advance(1); assert(down.k4)
advance(2)
handle_key_00(true); handle_key_00(false) -- additional trigger ignored
handle_key_01(false); handle_key_01(true) -- ordinary key suppressed
advance(101); assert(down.k4)
advance(102); assert(not down.k4)
advance(103); assert(not down.m0)
advance(104); assert(next(down)==nil)
handle_key_01(false); handle_key_01(true); assert(down.k89); handle_key_01(false)
handle_key_00(true); handle_key_00(false); advance(105); advance(106); assert(down.k4)
local before=lights
handle_key_02(true); handle_key_02(false) -- layer switch cancels
assert(next(down)==nil and lights>before)
advance(500); assert(next(down)==nil)
handle_key_02(true); handle_key_02(false) -- return to base
handle_key_03(true); handle_key_03(false); advance(501); assert(down.m1)
advance(502); assert(down.k5)
keybow_cancel_sequence(); assert(next(down)==nil)
handle_key_00(true); handle_key_00(false); fail=true; advance(503)
assert(next(down)==nil) -- partially failed keydown is released too
fail=false; advance(1000); assert(next(down)==nil)
'''
            script = "package.path = "+json.dumps(str(ROOT/"sdcard/?.lua"))+"..';'..package.path\n"+script.replace("LOADER", "dofile("+json.dumps(str(ROOT/"sdcard/keys.lua"))+")")
            subprocess.run(["lua","-"],cwd=root,input=script,text=True,check=True)

if __name__ == "__main__": unittest.main()
