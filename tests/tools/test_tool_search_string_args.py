"""String-encoded deferred arguments survive strict tool-call schemas (issue #96610)."""

import json

from jsonschema import Draft202012Validator

from agent.moonshot_schema import sanitize_moonshot_tool_parameters
from tools.tool_search import bridge_tool_schemas
from tools.tool_search_validation import normalize_tool_call_entries


def test_string_arguments_survive_moonshot_schema_and_bridge_dispatch():
    bridge = next(
        definition for definition in bridge_tool_schemas(1)
        if definition["function"]["name"] == "tool_call"
    )
    target = "mcp__example__knowledge_read"
    tool_args = {"id": "106ec784", "filter": {"tags": ["one", "two"]}}
    call = {"calls": [{"name": target, "arguments": json.dumps(tool_args)}]}

    # The model-facing schema must permit an encoded payload, not force {}.
    parameters = sanitize_moonshot_tool_parameters(bridge["function"]["parameters"])
    Draft202012Validator(parameters).validate(call)

    # The existing bridge parser must recover the original typed object.
    entries, error = normalize_tool_call_entries(call)
    assert error is None
    assert entries == [{"name": target, "arguments": tool_args}]
