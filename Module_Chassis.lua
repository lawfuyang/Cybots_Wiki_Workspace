-- Module_Chassis.lua
-- MediaWiki/Scribunto module for rendering Chassis information.
-- Expects a data module at `Module:Chassis/data` containing a Lua table
-- converted from `chassis_data.json` (either an array of entries or a
-- table keyed by title/normalized-title).
--
-- Usage on wiki pages:
--   {{#invoke:Chassis|show|Bulwark}}
--   {{#invoke:Chassis|list}}
-- Optional argument `dataModule` lets you point at a different data module:
--   {{#invoke:Chassis|show|Bulwark|dataModule=Module:MyChassisData}}

local p = {}

local function fmt(v)
    if v == nil then return "—" end
    local t = type(v)
    if t == "table" then
        if v.value ~= nil and v.unit ~= nil then
            return tostring(v.value) .. " " .. tostring(v.unit)
        elseif v.value ~= nil then
            return tostring(v.value)
        else
            local parts = {}
            for kk, vv in pairs(v) do
                table.insert(parts, tostring(kk) .. ": " .. tostring(vv))
            end
            return table.concat(parts, ", ")
        end
    else
        return tostring(v)
    end
end

local function normalize(s)
    if not s then return "" end
    s = mw.ustring.lower(tostring(s))
    s = mw.ustring.gsub(s, "[^%w%s]", "")
    s = mw.ustring.gsub(s, "%s+", " ")
    s = mw.ustring.gsub(s, "^%s+", "")
    s = mw.ustring.gsub(s, "%s+$", "")
    return s
end

local function findEntry(data, key)
    if not data or not key then return nil end
    if data[key] then return data[key] end
    local nk = normalize(key)
    if type(data) == "table" and #data > 0 then
        for _, item in ipairs(data) do
            if item and item.title and normalize(item.title) == nk then
                return item
            end
        end
    end
    for k, v in pairs(data) do
        if normalize(k) == nk then return v end
        if type(v) == "table" and v.title and normalize(v.title) == nk then
            return v
        end
    end
    return nil
end


    -- URL/title helpers ------------------------------------------------------
    local function urldecode(s)
        if not s then return s end
        return s:gsub('%%(%x%x)', function(h) return string.char(tonumber(h, 16)) end)
    end

    local function title_from_url(url)
        if not url then return nil end
        local m = url:match('/wiki/([^#%?]+)')
        if not m then m = url end
        m = urldecode(m)
        m = mw.ustring.gsub(m, '_', ' ')
        m = mw.ustring.gsub(m, '^%s+', '')
        m = mw.ustring.gsub(m, '%s+$', '')
        return m
    end


    -- Template function: image
    function p.image(frame)
        local args = (frame and frame.args) and frame.args or {}
        local name = args[1] or args.name or args.title or args.chassis
        if not name and args.url then
            name = title_from_url(args.url)
        end
        if not name then return '' end

        local dataModule = args.dataModule or "Module:Chassis/data"
        local ok, data = pcall(function() return mw.loadData(dataModule) end)
        if not ok or not data then return '' end
        local entry = findEntry(data, name)
        if not entry then
            entry = findEntry(data, title_from_url(name))
        end
        if not entry then return '' end

        local filename = entry.image1 or entry.image
        if not filename then return '' end
        local size = args.size or args.imageSize or "60px"
        return "[[File:" .. tostring(filename) .. "|" .. tostring(size) .. "]]"
    end

local function renderSection(name, sec, out)
    table.insert(out, "=== " .. tostring(name) .. " ===\n")
    if sec == nil then
        table.insert(out, "* —\n")
        return
    end
    local keys = {}
    for k in pairs(sec) do table.insert(keys, k) end
    table.sort(keys)
    for _, k in ipairs(keys) do
        local v = sec[k]
        table.insert(out, "* '''" .. tostring(k) .. "''': " .. fmt(v) .. "\n")
    end
end

local function renderEntry(entry)
    local out = {}
    table.insert(out, "== " .. (entry.title or "Unknown") .. " ==\n\n")
    -- show image if present (uses `image1` filename from data module)
    if entry.image1 then
        -- allow callers to control size via a global default; modules/pages can pass size by replacing this string
        local size = "200px"
        table.insert(out, "[[File:" .. tostring(entry.image1) .. "|" .. size .. "]]\n\n")
    end
    if entry.url then
        table.insert(out, "[" .. tostring(entry.url) .. "]\n\n")
    end
    if entry.sections then
        local sectionNames = {}
        for sname in pairs(entry.sections) do table.insert(sectionNames, sname) end
        table.sort(sectionNames)
        for _, sname in ipairs(sectionNames) do
            renderSection(sname, entry.sections[sname], out)
            table.insert(out, "\n")
        end
    end
    return table.concat(out, "")
end

function p.show(frame)
    local args = frame.args or {}
    local name = args[1] or args.name or args.chassis
    local dataModule = args.dataModule or "Module:Chassis/data"
    if not name then
        return "Usage: {{#invoke:Chassis|show|Chassis Name}}"
    end
    local ok, data = pcall(function() return mw.loadData(dataModule) end)
    if not ok or not data then
        return "Error: could not load data module '" .. dataModule .. "'. Create a data module (Module:Chassis/data) containing a Lua table converted from chassis_data.json."
    end
    local entry = findEntry(data, name)
    if not entry then
        return "Chassis '" .. tostring(name) .. "' not found in data module '" .. dataModule .. "'."
    end
    -- pass the frame so callers can be extended later (e.g., image size via args)
    return renderEntry(entry)
end

function p.list(frame)
    local dataModule = (frame.args and frame.args.dataModule) or "Module:Chassis/data"
    local ok, data = pcall(function() return mw.loadData(dataModule) end)
    if not ok or not data then return "Error: could not load data module '" .. dataModule .. "'." end
    local names = {}
    if type(data) == "table" and #data > 0 then
        for _, v in ipairs(data) do
            if v and v.title then table.insert(names, v.title) end
        end
    else
        for k, v in pairs(data) do
            if type(v) == "table" and v.title then table.insert(names, v.title) end
        end
    end
    table.sort(names)
    local out = {}
    for _, n in ipairs(names) do
        table.insert(out, "* [[" .. n .. "]]\n")
    end
    return table.concat(out, "")
end

return p
