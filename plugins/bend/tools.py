"""Hermes tool surface for experimental Bend proof verification."""
from __future__ import annotations

import shutil
from typing import Any

from tools.registry import tool_error, tool_result
from .session_kernel import verify_with_session_kernel
from .verify_core import BendVerifyError

BEND_VERIFY_SCHEMA = {
    "name": "bend_verify",
    "description": (
        "Run experimental verification of a local project's PROOF.bend. "
        "Preserves compiler evidence but does not report a qualified proof pass "
        "until an exact compiler/kernel release has cleared qualification. "
        "Remote imports are refused; project files are not edited."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "project_dir": {
                "type": "string",
                "description": "Absolute or relative path to the Bend project directory.",
            },
            "proof_file": {
                "type": "string",
                "description": (
                    "Path to a file named PROOF.bend inside project_dir. "
                    "Defaults to PROOF.bend."
                ),
            },
        },
        "required": ["project_dir"],
    },
}


def check_bend_available() -> bool:
    return shutil.which("bend") is not None


def _hold_unqualified_pass(result: dict[str, Any]) -> dict[str, Any]:
    """Keep raw experiment evidence without admitting an unqualified proof pass.

    No compiler/kernel release identity has been admitted for this plugin yet.
    Version compatibility and process-local hash stability are not qualification.
    This hold has no project, environment, or tool-argument override. Replacing
    it requires evidence-backed admission of the complete verifier distribution,
    including Base and the kernel, not simply a newer minimum version.
    """
    evidence = dict(result)
    evidence["qualified"] = False
    evidence["qualification_status"] = "pending_release_qualification"
    if evidence.get("success") is True or evidence.get("verdict") == "pass":
        evidence["success"] = False
        evidence["verdict"] = "unqualified"
        evidence["code"] = "unqualified_bend_release"
        evidence["message"] = (
            "Bend reported a raw execution pass, but this compiler/kernel release "
            "has not cleared qualification. Do not treat this as a verified proof."
        )
    return evidence


def handle_bend_verify(args: dict[str, Any]) -> str:
    try:
        result = verify_with_session_kernel(
            project_dir=str(args.get("project_dir") or ""),
            proof_file=str(args.get("proof_file") or "PROOF.bend"),
        )
    except BendVerifyError as exc:
        return tool_error(str(exc), code=exc.code)
    return tool_result(_hold_unqualified_pass(result))
