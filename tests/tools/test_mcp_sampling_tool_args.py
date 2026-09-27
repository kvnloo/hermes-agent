"""Tests for _parse_tool_call_arguments in tools.mcp_tool_sampling.

The sampling callback feeds the parsed value into the MCP SDK's
``ToolUseContent(input=...)``; the docstring promises a dict for every input
shape. A JSON string that parses to a non-object (array/scalar) is valid
JSON but not an object -- it must be wrapped as ``{"_raw": ...}`` like every
other non-dict, not passed through as a list/str/int (which violates the
declared ``-> dict`` contract and the SDK's field type).
"""

import pytest

from tools.mcp_tool_sampling import _parse_tool_call_arguments


def parse(args):
    return _parse_tool_call_arguments("srv", args)


def test_object_string_parses_to_dict():
    assert parse('{"a": 1}') == {"a": 1}


def test_array_string_wrapped_as_raw():
    # Red on base: returned [1, 2], violating the -> dict contract.
    assert parse("[1, 2]") == {"_raw": "[1, 2]"}


def test_scalar_strings_wrapped_as_raw():
    assert parse("42") == {"_raw": "42"}
    assert parse('"just a string"') == {"_raw": '"just a string"'}
    assert parse("null") == {"_raw": "null"}


def test_malformed_json_wrapped_as_raw():
    assert parse("{not json") == {"_raw": "{not json"}


def test_dict_passthrough():
    assert parse({"a": 1}) == {"a": 1}


def test_non_string_non_dict_wrapped_as_raw():
    assert parse(42) == {"_raw": "42"}
    assert parse(None) == {"_raw": "None"}


def test_all_outputs_are_dicts():
    for args in ('{"a":1}', "[1]", "1", '"x"', "null", "{bad", None, 5, {"a": 1}, [1]):
        assert isinstance(parse(args), dict), args
