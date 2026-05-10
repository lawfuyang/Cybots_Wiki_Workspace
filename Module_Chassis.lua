local p = {}

local ok, DATA = pcall(function() return mw.loadData('Module:Chassis/data') end)
if not ok or type(DATA) ~= 'table' then DATA = nil end

local function fmt(v)
    if v == nil then return '—' end
    if type(v) == 'table' then
        if v.value ~= nil then
            if v.unit then return tostring(v.value) .. ' ' .. tostring(v.unit) end
            return tostring(v.value)
        end
        return tostring(v)
    end
    return tostring(v)
end

local function title_from_url(url)
    if not url then return nil end
    local m = url:match('/wiki/([^#%?]+)') or url
    m = mw.ustring.gsub(m, '_', ' ')
    m = mw.ustring.gsub(m, '^%s+', '')
    m = mw.ustring.gsub(m, '%s+$', '')
    return m
end

local function findEntry(name)
    if not DATA or not name then return nil end
    if DATA[name] then return DATA[name] end
    local norm = tostring(name):gsub('_', ' ')
    if #DATA > 0 then
        for _, v in ipairs(DATA) do
            if v and v.title and (v.title == name or v.title == norm) then return v end
        end
    else
        for k, v in pairs(DATA) do
            if type(k) == 'string' and (k == name or k == norm) then return v end
            if type(v) == 'table' and v.title and (v.title == name or v.title == norm) then return v end
        end
    end
    local tname = title_from_url(name)
    if tname and tname ~= norm and tname ~= name then
        if #DATA > 0 then
            for _, v in ipairs(DATA) do
                if v and v.title == tname then return v end
            end
        else
            for _, v in pairs(DATA) do
                if type(v) == 'table' and v.title == tname then return v end
            end
        end
    end
    return nil
end

function p.get(frame)
    local args = (frame and frame.args) or {}
    local name = args[1] or args.name or args.title or args.chassis
    if not name and args.url then name = title_from_url(args.url) end
    if not name then return '' end
    local entry = findEntry(name)
    if not entry then return '' end
    local prop = args.prop or args.field or args.p or args[2]
    if prop and (prop == 'image' or prop == 'image1' or prop == 'file') then
        local filename = entry.image1 or entry.image
        if not filename then return '' end
        local size = args.size or args.imageSize or '60px'
        return '[[File:' .. tostring(filename) .. '|' .. tostring(size) .. ']]'
    end
    if prop and entry[prop] ~= nil then return fmt(entry[prop]) end
    local section = args.section or args.s
    local key = args.key or args.k
    if section and entry.sections and type(entry.sections) == 'table' and entry.sections[section] then
        if key then return fmt(entry.sections[section][key]) end
        return fmt(entry.sections[section])
    end
    return entry.title or ''
end

return p
