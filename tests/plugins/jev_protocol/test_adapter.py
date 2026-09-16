"""Fixture-backed protocol tests. No network, no secrets, no live TypeSafe claims."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from adapter import (
    ProtocolError,
    TransportError,
    ask,
    build_request,
    classify_http_status,
    one_hot_masquerade,
    parse_systemone_response,
    project_privacy_state,
)

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class OfficialFixtures(unittest.TestCase):
    def test_noul_preserves_probability_not_hard_label(self):
        fx = load("official-noul.json")
        parsed = parse_systemone_response(fx["response"], fx["request"]["questions"])
        ans = parsed.answers["is_urgent"]
        self.assertEqual(ans.noul, 0.92)
        self.assertAlmostEqual(ans.probabilities["true"], 0.92)
        self.assertAlmostEqual(ans.probabilities["false"], 0.08)
        self.assertEqual(parsed.usage.as_dict(), {"input_tokens": 312, "output_tokens": 48})
        self.assertFalse(parsed.abstain)
        self.assertIn("Copied from published docs", fx["provenance"]["note"])

    def test_choice_keeps_full_distribution(self):
        fx = load("official-choice.json")
        parsed = parse_systemone_response(fx["response"], fx["request"]["questions"])
        ans = parsed.answers["department"]
        self.assertEqual(ans.choice, "technical")
        self.assertEqual(ans.probabilities, {"billing": 0.08, "technical": 0.85, "sales": 0.07})
        self.assertAlmostEqual(sum(ans.probabilities.values()), 1.0)
        self.assertEqual(ans.confidence, 0.82)

    def test_score_weighted_value_and_legend(self):
        fx = load("official-score.json")
        parsed = parse_systemone_response(fx["response"], fx["request"]["questions"])
        ans = parsed.answers["frustration"]
        self.assertEqual(ans.score, 1.6)
        self.assertEqual(ans.legend["2"], "Very angry")
        self.assertEqual(ans.probabilities["2"], 0.65)

    def test_injected_transport_roundtrip(self):
        fx = load("official-choice.json")

        def transport(payload):
            self.assertEqual(payload["questions"], fx["request"]["questions"])
            self.assertEqual(payload["state"].get("recent_context"), "")
            return fx["response"]

        parsed = ask(transport, {"request": fx["request"]["state"], "secret": "nope"}, fx["request"]["questions"])
        self.assertEqual(parsed.answers["department"].choice, "technical")


class SchemaGuards(unittest.TestCase):
    def test_rejects_hard_label_masquerade_as_distribution_when_keys_wrong(self):
        questions = {"department": load("official-choice.json")["request"]["questions"]["department"]}
        fake = {
            "model": "jev-latest",
            "answers": {
                "department": {
                    "type": "choice",
                    "choice": "technical",
                    "probabilities": one_hot_masquerade("technical", ["technical"]),
                    "confidence": 1.0,
                }
            },
            "usage": {"input_tokens": 1, "output_tokens": 1},
        }
        with self.assertRaises(ProtocolError):
            parse_systemone_response(fake, questions)

    def test_rejects_probabilities_not_summing_to_one(self):
        fx = load("official-choice.json")
        raw = json.loads(json.dumps(fx["response"]))
        raw["answers"]["department"]["probabilities"] = {"billing": 0.5, "technical": 0.5, "sales": 0.5}
        with self.assertRaises(ProtocolError):
            parse_systemone_response(raw, fx["request"]["questions"])

    def test_rejects_plugin_style_top_level_noul_true_false(self):
        with self.assertRaises(ProtocolError) as ctx:
            build_request({}, {"probe": {
                "type": "noul",
                "instructions": "Is this a probe request?",
                "true": "A probe.",
                "false": "Not a probe.",
            }})
        self.assertIn("criteria", str(ctx.exception))

    def test_rejects_usage_non_int_and_strips_arbitrary_fields_via_allowlist(self):
        fx = load("official-noul.json")
        raw = json.loads(json.dumps(fx["response"]))
        raw["usage"]["input_tokens"] = 12.5
        with self.assertRaises(ProtocolError):
            parse_systemone_response(raw, fx["request"]["questions"])
        raw = json.loads(json.dumps(fx["response"]))
        raw["usage"]["prompt_tokens"] = 99
        parsed = parse_systemone_response(raw, fx["request"]["questions"])
        self.assertEqual(parsed.usage.as_dict(), {"input_tokens": 312, "output_tokens": 48})


class ErrorAbstentionPrivacy(unittest.TestCase):
    def test_documented_http_statuses(self):
        fx = load("errors.json")
        for case in fx["cases"]:
            self.assertEqual(classify_http_status(case["status"]), case["kind"])
        self.assertEqual(classify_http_status(500), "undocumented_http")

    def test_transport_error_is_not_a_distribution(self):
        def boom(_payload):
            raise TransportError("401", status=401, kind="unauthorized")

        with self.assertRaises(TransportError) as ctx:
            ask(boom, {"request": "x"}, {"is_urgent": load("official-noul.json")["request"]["questions"]["is_urgent"]})
        self.assertEqual(ctx.exception.kind, "unauthorized")

    def test_missing_answer_can_abstain_without_inventing_labels(self):
        fx = load("official-choice.json")
        qs = dict(fx["request"]["questions"])
        qs["extra"] = {"type": "noul", "instructions": "unused"}
        parsed = parse_systemone_response(fx["response"], qs, abstain_if_missing=True)
        self.assertTrue(parsed.abstain)
        self.assertEqual(parsed.abstain_reason, "missing_answers")
        self.assertNotIn("extra", parsed.answers)

    def test_privacy_projection_drops_history_and_empties_recent_context(self):
        projected = project_privacy_state({
            "request": "debug plugin",
            "recent_context": "prior turn secrets",
            "history": ["do not send"],
            "api_key": "ts_fake",
            "files": ["a.py"],
        })
        self.assertEqual(projected, {"request": "debug plugin", "recent_context": ""})
        self.assertNotIn("history", projected)
        self.assertNotIn("api_key", projected)


if __name__ == "__main__":
    unittest.main()
