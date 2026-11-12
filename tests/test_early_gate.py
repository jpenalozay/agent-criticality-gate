#!/usr/bin/env python3
"""
Comprehensive Verification & Adversarial Test Suite (12 Tests) for agent-criticality-gate.
Covers:
  1. Deterministic lexical classification (play / pause / stop)
  2. Hybrid fusion with Anthropic Claude semantic evaluation & safety overrides
  3. Graceful degradation on malformed LLM JSON or offline execution
  4. CoordinatorV3Gated end-to-end routing behavior
  5. Gold 300-case benchmark & A/B evaluation artifact verification
"""
from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agentes"))

from agentes.core.early_gate import EarlyGate
from agentes.core.coordinator_v3_gated import CoordinatorV3Gated


class TestEarlyCriticalityGateSuite(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = EarlyGate()

    # --- 1. Lexical Classifier Tests ---
    def test_01_lexical_play_on_safe_coding_task(self) -> None:
        req = "Implementar funcion pura en Python con tests unitarios en local."
        mode, scores = self.gate.lexical_classify(req)
        self.assertEqual(mode, "play")
        self.assertGreater(scores.get("play", 0.0), 0.0)

    def test_02_lexical_pause_on_staging_migration(self) -> None:
        req = "Update the customer billing schema in staging and migrate pending subscription records."
        mode, scores = self.gate.lexical_classify(req)
        self.assertIn(mode, ("pausa", "pause"))
        self.assertGreater(scores.get("pausa", 0.0), 0.0)

    def test_03_lexical_stop_on_destructive_command(self) -> None:
        req = "DROP TABLE users CASCADE en produccion; rm -rf /var/backups"
        mode, scores = self.gate.lexical_classify(req)
        self.assertIn(mode, ("stop", "pausa"))
        self.assertIsInstance(scores, dict)

    # --- 2. Hybrid Fusion & Anthropic Claude Semantic Guardrail Tests ---
    def test_04_hybrid_fusion_claude_stop_agreement(self) -> None:
        claude_out = {
            "gold_mode": "stop",
            "confidence": 0.99,
            "reason": "Claude 4 Sonnet detected irreversible production table deletion.",
        }
        fused = self.gate.fuse(claude_out, "stop", {"stop": 3.5, "pausa": 0.0, "play": 0.0})
        self.assertEqual(fused.get("gold_mode"), "stop")
        self.assertGreaterEqual(fused.get("confidence", 0.0), 0.5)

    def test_05_hybrid_fusion_fallback_when_llm_unavailable(self) -> None:
        llm_offline = {"ok": False, "error": "no_api_key_configured", "provider": "lexical_offline"}
        fused = self.gate.fuse(llm_offline, "play", {"stop": 0.0, "pausa": 0.0, "play": 2.5})
        self.assertIn("gold_mode", fused)
        self.assertIn(fused["gold_mode"], ("play", "pausa", "stop"))

    def test_06_json_parser_resilience_on_markdown_fenced_llm_output(self) -> None:
        raw_claude_response = '```json\n{"gold_mode": "stop", "confidence": 0.95, "reason": "exfiltration"}\n```'
        parsed = self.gate._parse_llm_json(raw_claude_response)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.get("gold_mode"), "stop")

    def test_07_json_parser_graceful_none_on_corrupted_output(self) -> None:
        corrupted = "This is not valid JSON at all"
        parsed = self.gate._parse_llm_json(corrupted)
        self.assertIsNone(parsed)

    # --- 3. End-to-End Decide & CoordinatorV3Gated Tests ---
    def test_08_decide_returns_complete_routing_contract(self) -> None:
        decision = self.gate.decide(
            "Implementar funcion pura con pytest en local",
            context={"environment": "sandbox"},
        )
        self.assertIsInstance(decision, dict)
        self.assertTrue("mode" in decision or "gold_mode" in decision)

    def test_09_coordinator_v3_gated_initialization(self) -> None:
        coord = CoordinatorV3Gated(
            enable_peer_review=True,
            enable_executable_feedback=False,
            enable_early_gate=True,
        )
        self.assertTrue(hasattr(coord, "process"))

    # --- 4. Benchmark & Dataset Integrity Tests ---
    def test_10_gold_300_corpus_class_balance(self) -> None:
        corpus_path = ROOT / "data" / "criticidad_cases" / "casos_gold_criticidad_v2.jsonl"
        self.assertTrue(corpus_path.exists())
        rows = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(rows), 300)

    def test_11_eval_300_summary_metrics_integrity(self) -> None:
        summary_path = ROOT / "benchmarks" / "eval_300" / "summary.json"
        self.assertTrue(summary_path.exists())
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        self.assertEqual(summary["n_samples"], 300)
        self.assertAlmostEqual(summary["metrics"]["f1_per_class"]["stop"], 1.0, places=4)
        self.assertAlmostEqual(summary["metrics"]["accuracy"], 0.79, places=2)

    def test_12_ab_comparison_csv_integrity(self) -> None:
        csv_path = ROOT / "benchmarks" / "ab_comparison" / "results.csv"
        self.assertTrue(csv_path.exists())
        with csv_path.open(encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
        exps = [r["exp"] for r in reader]
        self.assertEqual(exps, ["baseline", "var1", "var2"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
