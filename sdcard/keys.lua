require "keybow"

local active_id = "default"
local file = io.open("profiles/active", "r")
if file then
    local candidate = file:read("*l")
    file:close()
    if candidate and candidate:match("^[a-z0-9%-]+$") and #candidate <= 32 then
        active_id = candidate
    end
end

local function install_layers(profile)
    assert(profile.version == 3 and type(profile.layers) == "table")
    local layers = {}
    for _, layer in ipairs(profile.layers) do
        assert(type(layer.id) == "string" and type(layer.keys) == "table" and #layer.keys == 12)
        layers[layer.id] = layer
    end
    assert(profile.layers[1] and profile.layers[1].id == "base")

    local active = layers.base
    local context = nil
    local physical, suppressed, held = {}, {}, {}
    local key_refs, mod_refs, media_refs = {}, {}, {}

    local function change(refs, code, pressed, setter)
        local before = refs[code] or 0
        local after = math.max(0, before + (pressed and 1 or -1))
        refs[code] = after
        if (before == 0) ~= (after == 0) then setter(code, after > 0) end
    end

    local function send_action(action, pressed)
        if action.kind == "keyboard" then
            if pressed then
                for bit = 0, 7 do
                    if (action.modifiers & (1 << bit)) ~= 0 then
                        change(mod_refs, bit, true, keybow.set_modifier)
                    end
                end
                change(key_refs, action.usage, true, keybow.set_key)
            else
                change(key_refs, action.usage, false, keybow.set_key)
                for bit = 0, 7 do
                    if (action.modifiers & (1 << bit)) ~= 0 then
                        change(mod_refs, bit, false, keybow.set_modifier)
                    end
                end
            end
        elseif action.kind == "media" then
            change(media_refs, action.usage, pressed, keybow.set_media_key)
        end
    end

    local function light(layer)
        local lighting = assert(layer.lighting)
        if lighting.mode == "static" then
            keybow.auto_lights(false)
            for index, color in ipairs(lighting.colors) do
                local red = tonumber(color:sub(2, 3), 16)
                local green = tonumber(color:sub(4, 5), 16)
                local blue = tonumber(color:sub(6, 7), 16)
                keybow.set_pixel(index - 1, red, green, blue)
            end
        else
            local path = lighting.preset == "default" and "default" or "patterns/" .. lighting.preset
            assert(keybow.load_pattern(path), "Pattern unavailable")
            keybow.auto_lights(true)
        end
    end

    local function switch_to(target_id, next_context)
        local target = layers[target_id]
        if not target or target == active then return false end
        local previous = active
        local ok = pcall(light, target)
        if not ok then
            pcall(light, previous)
            return false
        end
        for index = 1, 12 do
            if held[index] then send_action(held[index], false); held[index] = nil end
            if physical[index] then suppressed[index] = true end
        end
        active = target
        context = next_context
        return true
    end

    local function return_layer()
        if not context then return end
        local previous = context.previous
        local restore = context.restore
        switch_to(previous, restore)
    end

    local function handle(index, pressed)
        physical[index] = pressed
        if not pressed then
            if context and context.mode == "hold" and context.key == index then
                return_layer()
            elseif held[index] then
                send_action(held[index], false)
                held[index] = nil
            end
            suppressed[index] = nil
            return
        end
        if suppressed[index] then return end
        if context and context.mode == "toggle" and context.key == index then
            return_layer()
            return
        end
        local action = active.keys[index]
        if action.kind == "layer" then
            local next_context = {
                mode = action.mode, key = index, previous = active.id,
                restore = context and context.mode == "toggle" and context or nil,
            }
            if action.mode == "timed" then
                next_context.deadline = keybow_get_millis() + action.seconds * 1000
            end
            switch_to(action.target, next_context)
        elseif action.kind == "keyboard" or action.kind == "media" then
            send_action(action, true)
            held[index] = action
        end
    end

    for index = 0, 11 do
        _G[string.format("handle_key_%02d", index)] = function(pressed)
            handle(index + 1, pressed)
        end
    end
    function setup() light(active) end
    function tick(now)
        if context and context.mode == "timed" and now >= context.deadline then
            return_layer()
        end
    end
end

local function load(id)
    local ok, result = pcall(dofile, "profiles/" .. id .. ".lua")
    if not ok then return false, result end
    if result ~= nil then
        ok, result = pcall(install_layers, result)
        if not ok then return false, result end
    end
    return true
end

local ok, err = load(active_id)
if not ok and active_id ~= "default" then
    keybow_profile_fallback = true
    ok, err = load("default")
end
if not ok then error(err) end
