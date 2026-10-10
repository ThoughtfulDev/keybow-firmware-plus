require "keybow"
-- keybow-sequences-v1

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
    assert((profile.version == 3 or profile.version == 4) and type(profile.layers) == "table")
    local layers = {}
    for _, layer in ipairs(profile.layers) do
        assert(type(layer.id) == "string" and type(layer.keys) == "table" and #layer.keys == 12)
        for _, action in ipairs(layer.keys) do
            if action.kind == "sequence" then
                assert(profile.version == 4 and type(action.events) == "table" and #action.events > 0 and #action.events <= 2048, "Invalid sequence")
                local down, duration, count = {}, 0, 0
                for index, item in ipairs(action.events) do
                    if type(item) == "number" then
                        item = {ms = item}
                        action.events[index] = item
                    else
                        assert(type(item) == "table", "Invalid sequence event")
                        -- Compact arrays keep long text within the SD source limit.
                        assert(#item == 3 and (item[3] == 0 or item[3] == 1), "Invalid compact HID event")
                        item.device = ({[0] = "keyboard", "modifier", "media"})[item[1]]
                        item.usage, item.pressed = item[2], item[3] == 1
                    end
                    if item.ms ~= nil then
                        assert(type(item.ms) == "number" and item.ms % 1 == 0 and item.ms >= 0 and item.ms <= 120000, "Invalid delay")
                        duration = duration + math.max(1, item.ms)
                    else
                        local limit = item.device == "keyboard" and 115 or 7
                        local minimum = item.device == "keyboard" and 4 or 0
                        assert((item.device == "keyboard" or item.device == "modifier" or item.device == "media") and type(item.usage) == "number" and item.usage % 1 == 0 and item.usage >= minimum and item.usage <= limit and type(item.pressed) == "boolean", "Invalid HID event")
                        local identity = item.device .. ':' .. item.usage
                        assert(item.pressed ~= (down[identity] == true), "Unbalanced sequence")
                        down[identity] = item.pressed and true or nil
                        if item.device == "keyboard" then count = count + (item.pressed and 1 or -1); assert(count <= 12, "Too many held keys") end
                        duration = duration + 1
                    end
                end
                assert(next(down) == nil and duration <= 120000, "Invalid sequence end or duration")
            end
        end
        layers[layer.id] = layer
    end
    assert(profile.layers[1] and profile.layers[1].id == "base")

    local active = layers.base
    local context = nil
    local physical, suppressed, held = {}, {}, {}
    local key_refs, mod_refs, media_refs = {}, {}, {}
    local sequence = nil
    local sequence_down = {}
    local setters = {keyboard = keybow.set_key, modifier = keybow.set_modifier, media = keybow.set_media_key}

    local function cancel_sequence()
        sequence = nil
        for _, device in ipairs({"keyboard", "media", "modifier"}) do
            for identity, item in pairs(sequence_down) do
                if item.device == device then
                    pcall(setters[item.device], item.usage, false)
                    sequence_down[identity] = nil
                end
            end
        end
    end
    keybow_cancel_sequence = cancel_sequence


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

    local function release_physical()
        for index = 1, 12 do
            if held[index] then send_action(held[index], false); held[index] = nil end
            if physical[index] then suppressed[index] = true end
        end
    end

    local function start_sequence(action)
        release_physical()
        sequence = {events = action.events, index = 1, deadline = keybow_get_millis()}
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
        cancel_sequence()
        release_physical()
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
        elseif action.kind == "sequence" then
            if not sequence then start_sequence(action) end
        elseif sequence then
            suppressed[index] = true
        elseif not sequence and (action.kind == "keyboard" or action.kind == "media") then
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
        if sequence and now >= sequence.deadline then
            local current = sequence
            local item = current.events[current.index]
            if not item then
                cancel_sequence()
            else
                current.index = current.index + 1
                if item.ms then
                    current.deadline = now + item.ms
                else
                    local setter = setters[item.device]
                    local identity = item.device .. ':' .. item.usage
                    if item.pressed then sequence_down[identity] = item end
                    local ok = setter and pcall(setter, item.usage, item.pressed)
                    if not ok then
                        cancel_sequence()
                    else
                        sequence_down[identity] = item.pressed and item or nil
                        current.deadline = now + 1
                    end
                end
            end
        end
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
