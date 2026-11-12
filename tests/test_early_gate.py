#!/usr/bin/env python3
"""
Automated Verification Suite for agent-criticality-gate.
Tests deterministic lexical classification, hybrid fusion with a frontier LLM
(Anthropic Claude / OpenAI / DeepSeek), and the 300-case gold benchmark integrity.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agentes"))

from agentes.core.early_gate import EarlyGate


class TestEarlyCriticalityGate(unittest.TestCase):
    def setUp(self) -> None:
        self.gate = EarlyGate()

    def test_lexical_play_on_safe_unit_test_task(self) -> None:
        req = "Implementar funcion pura en Python con tests unitarios en local."
        mode, scores = self.gate.lexical_classify(req)
        self.assertEqual(mode, "play")
        self.assertGreater(scores.get("play", 0.0), 0.0)

    def test_lexical_pause_on_staging_schema_migration(self) -> None:
        req = "Update the customer billing schema in staging and migrate pending subscription records."
        mode, scores = self.gate.lexical_classify(req)
        self.assertIn(mode, ("pausa", "pause"))
        self.assertGreater(scores.get("pausa", 0.0), 0.0)

    def test_hybrid_fusion_respects_frontier_llm_stop_override(self) -> None:
        # Simulate frontier LLM (e.g., Claude 4 Sonnet/Opus) detecting subtle semantic exfiltration risk
        simulated_claude_output = {
            "ok": True,
            "parsed": {
                "mode": "stop",
                "confidence": 0.98,
                "reason": "Detected covert credential exfiltration via outbound webhook in build script.",
            },
            "mode": "stop",
            "confidence": 0.98,
        }
        lex_mode, lex_scores = "play", {"stop": 0.0, "pausa": 0.0, "play": 1.5}
        fused = self.gate.fuse(simulated_claude_output, lex_mode, lex_scores)
        resolved_mode = fused.get("mode") or fused.get("final_mode") or fused.get("decision")
        self.assertEqual(resolved_mode, "stop")

    def test_gold_300_corpus_integrity(self) -> None:
        corpus_path = ROOT / "data" / "criticidad_cases" / "casos_gold_criticidad_v2.jsonl"
        self.assertTrue(corpus_path.exists(), "Gold 300-case JSONL corpus must exist")
        lines = [json.loads(line) for line in corpus_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
