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
    title = "Open Hermes A fixture lab",
    icon = "sparkle",
    keys = { "ctrl+alt+shift+h" },
    run = function(cx)
        local cwd = focused_cwd(cx)
        local root = cwd and repo_root_from(cwd) or nil

        if root == nil or not tern.fs.exists(root .. "/ui-tui/scripts/tern-ux/preview.ts") then
            cx:toast(
                "error",
                "Hermes A fixture needs its experiment checkout",
                "Focus a pane inside exp/tern-ux-omp-baseline with dependencies installed."
            )
            return
        end

        local _tab, err = cx.layout:tab({
            name = "Hermes A fixture",
            cwd = root,
            split = "right",
            {
                launch = {
                    command = "npm run tern:ux:preview --workspace ui-tui",
                },
            },
            {
                split = "down",
                {
                    launch = {
                        command = "npm run tern:ux:manifest --workspace ui-tui; npm test --workspace ui-tui -- src/tern; exec ${SHELL:-/bin/sh} -l",
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
            "Hermes A fixture workspace opened",
            "Fixture left · manifest/tests upper-right · scratch shell lower-right"
        )
    end,
})
