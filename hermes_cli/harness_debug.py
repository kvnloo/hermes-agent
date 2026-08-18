"""Public facade for the fail-closed Harness Debug controller."""

from hermes_cli.harness_debug_secure import (
    HarnessDebugController,
    HarnessDebugRefused,
    aggregate_status,
    build_parser,
    fixture_seed,
    guard_debug_db,
    make_local_receipt,
    render_markdown,
    run_argv,
    run_command,
)

__all__ = [
    "HarnessDebugController",
    "HarnessDebugRefused",
    "aggregate_status",
    "build_parser",
    "fixture_seed",
    "guard_debug_db",
    "make_local_receipt",
    "render_markdown",
    "run_argv",
    "run_command",
]