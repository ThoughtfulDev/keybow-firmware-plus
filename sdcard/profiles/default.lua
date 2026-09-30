-- keybow-profile-v1:eyJ2ZXJzaW9uIjoxLCJpZCI6ImRlZmF1bHQiLCJuYW1lIjoiTnVtYmVyIHBhZCIsImtleXMiOlt7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5OCwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo4OSwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5MCwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5MSwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5MiwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5MywibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5NCwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5NSwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5NiwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5NywibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjo5OSwibW9kaWZpZXJzIjowfSx7ImtpbmQiOiJrZXlib2FyZCIsInVzYWdlIjoxMDMsIm1vZGlmaWVycyI6MH1dLCJsaWdodGluZyI6eyJtb2RlIjoicHJlc2V0IiwicHJlc2V0IjoiZGVmYXVsdCJ9fQ
require "keybow"
local key_refs, mod_refs, media_refs = {}, {}, {}
local function change(refs, code, pressed, setter)
  local before = refs[code] or 0
  local after = math.max(0, before + (pressed and 1 or -1))
  refs[code] = after
  if (before == 0) ~= (after == 0) then setter(code, after > 0) end
end
local function keyboard(usage, mask, pressed)
  if pressed then
    for bit = 0, 7 do if (mask & (1 << bit)) ~= 0 then
      change(mod_refs, bit, true, keybow.set_modifier)
    end end
    change(key_refs, usage, true, keybow.set_key)
  else
    change(key_refs, usage, false, keybow.set_key)
    for bit = 0, 7 do if (mask & (1 << bit)) ~= 0 then
      change(mod_refs, bit, false, keybow.set_modifier)
    end end
  end
end
function handle_key_00(pressed) keyboard(98, 0, pressed) end
function handle_key_01(pressed) keyboard(89, 0, pressed) end
function handle_key_02(pressed) keyboard(90, 0, pressed) end
function handle_key_03(pressed) keyboard(91, 0, pressed) end
function handle_key_04(pressed) keyboard(92, 0, pressed) end
function handle_key_05(pressed) keyboard(93, 0, pressed) end
function handle_key_06(pressed) keyboard(94, 0, pressed) end
function handle_key_07(pressed) keyboard(95, 0, pressed) end
function handle_key_08(pressed) keyboard(96, 0, pressed) end
function handle_key_09(pressed) keyboard(97, 0, pressed) end
function handle_key_10(pressed) keyboard(99, 0, pressed) end
function handle_key_11(pressed) keyboard(103, 0, pressed) end
function setup()
  assert(keybow.load_pattern("default"), "Pattern unavailable")
  keybow.auto_lights(true)
end
