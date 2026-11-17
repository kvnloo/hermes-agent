"""Regression for NousResearch/hermes-agent#156347: doctor output must respect TTY mode."""

from __future__ import annotations

import io
import sys

from hermes_cli import doctor
from hermes_cli.doctor_connectivity import ProbeResult


def _run_connectivity(monkeypatch, stdout):
    result = ProbeResult("OpenRouter API", [("✓", "OpenRouter API", "")], [])
    monkeypatch.setattr(doctor, "build_probes", lambda: [("OpenRouter API", lambda: result)])
    monkeypatch.setattr(doctor, "run_probes", lambda probes: [result])
    monkeypatch.setattr(sys, "stdout", stdout)
    return doctor._check_api_connectivity(False)


def test_redirected_connectivity_output_has_no_carriage_returns(monkeypatch):
    output = io.StringIO()  # redirected file/pipe: isatty() is false

    finding = _run_connectivity(monkeypatch, output)

    rendered = output.getvalue()
    assert "\r" not in rendered
    assert "Running 1 connectivity checks in parallel" in rendered
    assert "OpenRouter API" in rendered
    assert rendered.endswith("\n")
    assert finding.issues == []

    # An interactive TTY must still clear its progress line in place.
    class _Tty(io.StringIO):
        def isatty(self):
            return True

    interactive_output = _Tty()
    _run_connectivity(monkeypatch, interactive_output)
    assert "\r" in interactive_output.getvalue()
