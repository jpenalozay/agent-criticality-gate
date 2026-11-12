"""
Gate temprano de criticidad (antes del Arquitecto).

Flujo:
1. LLM: clasificación play/pausa/stop con confianza y bandera de duda (sin contexto de blueprint).
2. Si hay duda o confianza baja → fallback: reglas léxicas en español (+ opcional segunda pasada LLM compacta).

No sustituye al Sentinel sobre blueprint; complementa el pipeline con una señal previa barata.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Umbrales (ajustables por entorno)
EARLY_GATE_CONFIDENCE_OK = float(os.getenv("EARLY_GATE_CONFIDENCE_OK", "0.62"))
EARLY_GATE_DOUBT_CONF = float(os.getenv("EARLY_GATE_DOUBT_CONF", "0.45"))

# Pesos léxicos (heurística; calibrar con corpus gold si se dispone de métricas)
STOP_PATTERNS = [
    (r"producci[oó]n|PCI|JWT|OAuth|GDPR|datos personales|hospital|clínico|SCADA|KMS"
     r"|transferencia|pasarela|tokenizaci", 3.0),
    (r"firmware|multicl[uú]ster|terraformaci[oó]n judicial|borrado masivo", 2.5),
]
PAUSE_PATTERNS = [
    (r"staging|integraci[oó]n|Redis|Prometheus|Helm|VPN|sandbox|Pact|feature flag", 2.0),
    (r"microservicio|pipeline CI|namespace de prueba", 1.5),
]
PLAY_PATTERNS = [
    (r"local|sint[eé]tico|laboratorio|sin red|jupyter|ejercicio acad[eé]mico|consola educativa", 2.5),
    (r"carpeta local|memoria RAM|toy", 2.0),
]


class EarlyGate:
    """Hybrid early criticality gate (play / pause / stop) combining LLM semantic evaluation with deterministic lexical fallback."""

    def __init__(self) -> None:
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            try:
                from core.llm_client_v3 import get_llm_client

                self._llm = get_llm_client("early_gate")
            except Exception as e:
                logger.warning("EarlyGate: LLM no disponible (%s)", e)
                self._llm = False
        return self._llm if self._llm else None

    def _score_patterns(self, text: str, patterns: List[Tuple[str, float]]) -> float:
        t = text.lower()
        s = 0.0
        for rx, w in patterns:
            if re.search(rx, t, re.I):
                s += w
        return s

    def lexical_classify(self, requirement: str) -> Tuple[str, Dict[str, float]]:
        """Clasificador por reglas léxicas ponderadas."""
        sp = self._score_patterns(requirement, STOP_PATTERNS)
        pp = self._score_patterns(requirement, PAUSE_PATTERNS)
        lp = self._score_patterns(requirement, PLAY_PATTERNS)
        scores = {"stop": sp, "pausa": pp, "play": lp}
        mode = max(scores, key=scores.get)
        return mode, scores

    def _parse_llm_json(self, raw: str) -> Optional[Dict[str, Any]]:
        raw = raw.strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    def llm_classify(self, requirement: str) -> Dict[str, Any]:
        """Una pasada LLM: modo, confianza, duda."""
        import os
        if not any(os.getenv(k) for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")):
            return {"ok": False, "error": "no_api_key_configured", "provider": "lexical_offline"}
        llm = self._get_llm()
        out: Dict[str, Any] = {
            "gold_mode": None,
            "confidence": 0.0,
            "doubt": True,
            "reason": "llm_no_disponible",
            "raw": None,
        }
        if not llm:
            return out

        system = (
            "Eres un clasificador de criticidad operativa para ingeniería de software. "
            "Sin acceso al repositorio ni al blueprint, solo el texto del requerimiento.\n"
            "Etiquetas: play (bajo impacto, local o acotado), pausa (integración media, no producción crítica), "
            "stop (producción, datos sensibles, pagos, regulación fuerte).\n"
            "Responde SOLO un JSON válido con las claves: "
            'gold_mode ("play"|"pausa"|"stop"), confidence (número 0-1), '
            'doubt (booleano, true si falta contexto del proyecto para decidir con seguridad), '
            'reason (string corto).'
        )
        prompt = f"Requerimiento:\n{requirement[:8000]}"
        try:
            raw = llm.generate(prompt, system_prompt=system, temperature=0.1, max_tokens=400)
            out["raw"] = raw[:2000]
            parsed = self._parse_llm_json(raw)
            if not parsed:
                out["reason"] = "json_parse_failed"
                return out
            gm = parsed.get("gold_mode") or parsed.get("mode")
            if gm not in ("play", "pausa", "stop"):
                out["reason"] = "invalid_gold_mode"
                return out
            conf = float(parsed.get("confidence", 0))
            doubt = bool(parsed.get("doubt", True))
            out["gold_mode"] = gm
            out["confidence"] = max(0.0, min(1.0, conf))
            out["doubt"] = doubt
            out["reason"] = str(parsed.get("reason", ""))[:500]
        except Exception as e:
            logger.exception("EarlyGate LLM error")
            out["reason"] = f"llm_error:{e}"
        return out

    def fuse(self, llm_out: Dict[str, Any], lex_mode: str, lex_scores: Dict[str, float]) -> Dict[str, Any]:
        """Combina LLM y léxico cuando hay duda o baja confianza."""
        doubt = llm_out.get("doubt", True)
        conf = float(llm_out.get("confidence") or 0)
        gm_llm = llm_out.get("gold_mode")

        if gm_llm and not doubt and conf >= EARLY_GATE_CONFIDENCE_OK:
            return {
                "gold_mode": gm_llm,
                "confidence": conf,
                "source": "llm",
                "lexical_scores": lex_scores,
                "doubt": False,
            }

        # Fusionar: si LLM dudoso, pesar léxico fuerte
        if lex_scores[lex_mode] >= 2.0:
            merged_mode = lex_mode
            merged_conf = min(0.85, 0.45 + lex_scores[lex_mode] * 0.12)
            src = "lexical"
            if gm_llm and gm_llm != lex_mode and conf >= EARLY_GATE_DOUBT_CONF:
                # conflicto: preferir conservador (stop > pausa > play)
                order = {"stop": 3, "pausa": 2, "play": 1}
                merged_mode = gm_llm if order.get(gm_llm, 0) >= order.get(lex_mode, 0) else lex_mode
                merged_conf = (conf + merged_conf) / 2
                src = "fusion_llm_lexicon"
            return {
                "gold_mode": merged_mode,
                "confidence": merged_conf,
                "source": src,
                "lexical_scores": lex_scores,
                "doubt": doubt or conf < EARLY_GATE_DOUBT_CONF,
                "llm_hint": gm_llm,
            }

        if gm_llm:
            return {
                "gold_mode": gm_llm,
                "confidence": max(conf, 0.35),
                "source": "llm_fallback",
                "lexical_scores": lex_scores,
                "doubt": True,
            }

        # Por defecto conservador medio
        return {
            "gold_mode": "pausa",
            "confidence": 0.4,
            "source": "default_pausa",
            "lexical_scores": lex_scores,
            "doubt": True,
        }

    def decide(self, requirement: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Ejecuta gate temprano completo.

        Returns:
            Dict con gold_mode final, confidence, source, doubt, detalles léxicos y salida LLM cruda (truncada).
        """
        lex_mode, lex_scores = self.lexical_classify(requirement)
        llm_out = self.llm_classify(requirement)
        fused = self.fuse(llm_out, lex_mode, lex_scores)
        fused["early_gate_version"] = "1.0"
        fused["llm_detail"] = {k: v for k, v in llm_out.items() if k != "raw"}
        return fused
