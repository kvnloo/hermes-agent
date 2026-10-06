--!strict

local function focused_cwd(cx): string?
    local focused = cx.session:focused()
    if focused == nil then
        return nil
    end

    for _, pane in cx.session:panes() do
        if pane.pane == focused and pane.cwd and pane.cwd ~= "" then
            return pane.cwd
        end
    end

    return nil
end

local function repo_root_from(dir: string): string?
    local at = dir

    while at ~= "" and at ~= "/" do
        if tern.fs.exists(at .. "/ui-tui/package.json") and tern.fs.exists(at .. "/AGENTS.md") then
            return at
        end

        at = string.match(at, "^(.*)/[^/]*$") or ""
    end

    return nil
end

tern.command({
    id = "open-lab",
    title = "Open Hermes UX lab",
    icon = "sparkle",
    keys = { "ctrl+alt+shift+h" },
    run = function(cx)
        local cwd = focused_cwd(cx)
        local root = cwd and repo_root_from(cwd) or nil

        if root == nil then
            cx:toast(
                "error",
                "Hermes UX lab needs a Hermes checkout",
                "Focus a pane somewhere inside hermes-agent, then run the command again."
            )
            return
        end

        local _tab, err = cx.layout:tab({
            name = "Hermes UX",
            cwd = root,
            split = "right",
            {
                launch = {
                    command = "hermes --tui --native",
                },
            },
            {
                split = "down",
                {
                    launch = {
                        command = "npm test --workspace ui-tui -- src/tern; exec ${SHELL:-/bin/sh} -l",
                    },
                },
                {},
            },
        })

        if err then
            cx:toast("error", "Hermes UX workspace opened incomplete", err)
            return
        end

        cx:toast(
            "success",
            "Hermes UX lab ready",
            "Hermes left · TSP tests upper-right · scratch shell lower-right"
        )
    end,
})
