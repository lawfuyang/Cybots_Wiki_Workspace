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

-- Generate complete chassis overview table
function p.generateTable(frame)
    -- Try to reload data if it wasn't loaded initially
    local data = DATA
    if not data then
        -- Try primary path
        local ok, result = pcall(function() return mw.loadData('Module:Chassis/data') end)
        if ok and type(result) == 'table' then
            data = result
        else
            -- Try alternative path
            ok, result = pcall(function() return mw.loadData('Module:Chassis_data') end)
            if ok and type(result) == 'table' then
                data = result
            end
        end
    end
    
    -- Verify data exists and has entries
    if not data or type(data) ~= 'table' then
        return 'Error: Could not load data module. Check Module:Chassis/data or Module:Chassis_data exists.'
    end
    
    -- Check if it's an array-like table or needs iteration
    local hasEntries = false
    if #data > 0 then
        hasEntries = true
    else
        -- Check if there are any keyed entries
        for _ in pairs(data) do
            hasEntries = true
            break
        end
    end
    
    if not hasEntries then
        return 'Error: Data module is empty. Ensure data is properly formatted.'
    end
    
    local cols = {
        { title = 'Image', section = nil, key = 'image' },
        { title = 'Name', section = nil, key = 'name' },
        { title = 'Chassis Type', section = 'Unit Information', key = 'Chassis Type' },
        { title = 'Chassis Cost', section = 'Unit Information', key = 'Chassis Cost' },
        { title = 'Technology Required', section = 'Unit Information', key = 'Technology Required' },
        { title = 'Other Requirements', section = 'Unit Information', key = 'Other Requirements' },
        { title = 'Weapon Slots', section = 'Slots', key = 'Weapon Slots' },
        { title = 'Module Slots', section = 'Slots', key = 'Module Slots' },
        { title = 'Shield Slots', section = 'Slots', key = 'Shield Slots' },
        { title = 'Reactor Slots', section = 'Slots', key = 'Reactor Slots' },
        { title = 'Weapon Tech', section = 'Starting Tech Levels', key = 'Weapon Tech' },
        { title = 'Shield Tech', section = 'Starting Tech Levels', key = 'Shield Tech' },
        { title = 'Module Tech', section = 'Starting Tech Levels', key = 'Module Tech' },
        { title = 'Reactor Tech', section = 'Starting Tech Levels', key = 'Reactor Tech' },
        { title = 'Payload', section = 'Base Stats', key = 'Payload' },
        { title = 'Armor', section = 'Base Stats', key = 'Armor' },
        { title = 'Speed', section = 'Base Stats', key = 'Speed' },
        { title = 'Critical Hit Chance', section = 'Base Stats', key = 'Critical Hit Chance' },
        { title = 'Accuracy Adjusted', section = 'Base Stats', key = 'Accuracy Adjusted' },
        { title = 'Damage Adjusted', section = 'Base Stats', key = 'Damage Adjusted' },
        { title = 'Defensive Merit', section = 'Base Stats', key = 'Defensive Merit' },
        { title = 'Shield Projection', section = 'Unique Stats', key = 'Shield Projection' },
        { title = 'Module Uplink', section = 'Unique Stats', key = 'Module Uplink' },
        { title = 'Energy Distribution / Energy Share', section = 'Unique Stats', key = 'Energy Distribution / Energy Share' },
        { title = 'Energy Induction', section = 'Unique Stats', key = 'Energy Induction' },
        { title = 'Damage Boost', section = 'Hidden Stats', key = 'Damage Boost' },
        { title = 'Drain Boost', section = 'Hidden Stats', key = 'Drain Boost' },
    }
    
    local result = '{| class="wikitable sortable" style="width:100%;"\n'
    result = result .. '|+ Chassis overview\n'
    result = result .. '|-\n'
    
    -- Header row
    result = result .. '! Image !! Name'
    for i = 3, #cols do
        result = result .. ' !! ' .. cols[i].title
    end
    result = result .. '\n'
    
    -- Data rows - iterate as array first, fall back to key iteration
    if #data > 0 then
        for _, entry in ipairs(data) do
            if entry and entry.title then
                result = result .. '|-\n'
                -- Image cell
                local filename = entry.image1 or entry.image
                local imageVal = filename and ('[[File:' .. tostring(filename) .. '|60px]]') or '—'
                result = result .. '| ' .. imageVal .. ' || [[' .. entry.title .. ']]'
                
                -- Rest of cells
                for i = 3, #cols do
                    local col = cols[i]
                    local val = '—'
                    if col.section then
                        if entry.sections and entry.sections[col.section] and entry.sections[col.section][col.key] then
                            val = fmt(entry.sections[col.section][col.key])
                        end
                    end
                    result = result .. ' || ' .. val
                end
                result = result .. '\n'
            end
        end
    else
        -- Fallback for keyed tables
        for _, entry in pairs(data) do
            if type(entry) == 'table' and entry.title then
                result = result .. '|-\n'
                -- Image cell
                local filename = entry.image1 or entry.image
                local imageVal = filename and ('[[File:' .. tostring(filename) .. '|60px]]') or '—'
                result = result .. '| ' .. imageVal .. ' || [[' .. entry.title .. ']]'
                
                -- Rest of cells
                for i = 3, #cols do
                    local col = cols[i]
                    local val = '—'
                    if col.section then
                        if entry.sections and entry.sections[col.section] and entry.sections[col.section][col.key] then
                            val = fmt(entry.sections[col.section][col.key])
                        end
                    end
                    result = result .. ' || ' .. val
                end
                result = result .. '\n'
            end
        end
    end
    
    result = result .. '|}'
    return result
end

-- Test function to debug data loading
function p.testData(frame)
    local data = DATA
    if not data then
        local ok, result = pcall(function() return mw.loadData('Module:Chassis/data') end)
        if ok then
            data = result
            if type(data) == 'table' then
                if #data > 0 then
                    return 'SUCCESS: Loaded ' .. tostring(#data) .. ' entries from Module:Chassis/data'
                else
                    local count = 0
                    for _ in pairs(data) do count = count + 1 end
                    return 'PARTIAL: Module loaded but ' .. tostring(count) .. ' entries (may be keyed table)'
                end
            else
                return 'ERROR: Module loaded but not a table: ' .. type(result)
            end
        else
            return 'ERROR: Could not load Module:Chassis/data'
        end
    else
        return 'SUCCESS: Data already loaded (' .. tostring(#data) .. ' entries)'
    end
end

return p
