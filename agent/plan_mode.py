"""Execution-time planning policy. Keep schemas and the cached prompt byte-stable."""

# Unknown tools (including shell, delegation, MCP and wrapper batches) fail closed.
# Shell commands cannot be reliably classified read-only by string inspection.
PLAN_READ_TOOLS = frozenset({"read_file", "search_files", "web_search", "web_extract", "skill_view", "skills_list"})


def plan_tool_block(agent, name: str) -> str | None:
    if getattr(agent, "_plan_mode", False) and name not in PLAN_READ_TOOLS:
        return "Plan mode is active: execution is blocked. Return a plan for revision-bound review, or use a read-only tool."
    return None
