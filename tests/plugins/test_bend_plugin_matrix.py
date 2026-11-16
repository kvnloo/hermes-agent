"""Large deterministic downstream matrix for the Bend adapter contract."""
from __future__ import annotations

import itertools

from plugins.bend import verify_core as core


def test_downstream_bend_contract_matrix_1897_cases(tmp_path):
    cases = 0

    stdout_forms = [
        "ALL PROOFS CHECK",
        "ALL PROOFS CHECK\n",
        " ALL PROOFS CHECK ",
        "prefix ALL PROOFS CHECK",
        "ALL PROOFS CHECK suffix",
        "NOT ALL PROOFS CHECK",
        "",
        "all proofs check",
        "SOME PROOFS FAIL",
        "\nALL PROOFS CHECK\nextra",
        "ALL PROOFS CHECK\n\n",
        "x\nALL PROOFS CHECK\ny",
    ]
    stderr_forms = ["", "SOME PROOFS FAIL", "warning", "ALL PROOFS CHECK"]
    for returncode, stdout, _stderr in itertools.product(
        [0, 1, 2, 3, 127, 255, -9], stdout_forms, stderr_forms
    ):
        exact_pass = returncode == 0 and stdout.strip() == core._PASS_MARKER
        verdict = "pass" if exact_pass else ("indeterminate" if returncode == 0 else "fail")
        assert (verdict == "pass") is exact_pass
        cases += 1

    lengths = list(range(33)) + [7998, 7999, 8000, 8001, 8002, 12000, 16000, 100000]
    for kind, length in itertools.product(("str", "bytes"), lengths):
        raw = "x" * length
        value = raw.encode() if kind == "bytes" else raw
        got = core.bounded(value)
        assert len(got) <= core._OUTPUT_LIMIT
        if length <= core._OUTPUT_LIMIT:
            assert got == raw
        cases += 1

    keys = ["BENDTT", "BEND_HUB", "BEND_LIB", "BEND_ORIGIN", "BEND_NO_TELEMETRY", "UNRELATED"]
    for mask in range(1 << len(keys)):
        source = {key: "poison" for index, key in enumerate(keys) if mask >> index & 1}
        env = core.clean_env(source)
        for key in core._BEND_ENV_DENY:
            assert key not in env
        assert env["BEND_NO_TELEMETRY"] == "1"
        if "UNRELATED" in source:
            assert env["UNRELATED"] == "poison"
        cases += 1

    for major, minor, patch in itertools.product(range(7), range(5), range(40)):
        assert core.parse_version(f"bend {major}.{minor}.{patch}") == (major, minor, patch)
        cases += 1
    for malformed in ("", "2.0.32", "bend x.y.z", "bend 2.0", "Bend 2.0.32", "bend 2.0.32.1"):
        assert core.parse_version(malformed) is None
        cases += 1

    (tmp_path / "PROOF.bend").write_text("# proof\n")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "PROOF.bend").write_text("# proof\n")
    for path in ("PROOF.bend", "./PROOF.bend", "sub/PROOF.bend", "sub/../PROOF.bend"):
        _, proof, _ = core.resolve_proof(str(tmp_path), path)
        assert proof.name == "PROOF.bend"
        cases += 1
    for path in ("proof.bend", "LAWS.bend", "sub/proof.bend", "../PROOF.bend", "PROOF.txt"):
        try:
            core.resolve_proof(str(tmp_path), path)
        except core.BendVerifyError:
            pass
        else:
            raise AssertionError(f"expected invalid proof path: {path}")
        cases += 1

    assert cases == 1897
