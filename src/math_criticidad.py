"""
Modelo matemático de criticidad (play / pausa / stop) para Sprint 6.

Combina scores léxicos (EarlyGate) con señales de texto (longitud, densidad de keywords).
"""

from __future__ import annotations

import re
import math
from collections import Counter
from typing import Any, Callable, Dict, Tuple

import numpy as np

LABELS = ("play", "pausa", "stop")

# Pesos documentados del risk_score ∈ [0, 1]
W_STOP = 0.40
W_PAUSA = 0.30
W_PLAY_INV = 0.30
W_KW_DENSITY = 0.05
LEX_SCORE_CAP = 6.0

# Umbrales de decisión sobre risk_score (calibrados al corpus gold v2 ES;
# el guion NASA usa 0.80/0.40 pero allí risk_score ∈ [0,1] con otra escala)
THRESHOLD_STOP = 0.45
THRESHOLD_PAUSA = 0.35

# Baseline: reglas simples en español (sin EarlyGate)
_STOP_KW = (
    "producción",
    "produccion",
    "pci",
    "gdpr",
    "hospital",
    "clínico",
    "clinico",
    "pago",
    "oauth",
    "jwt",
    "scada",
    "datos personales",
    "firmware",
)
_PAUSE_KW = ("staging", "integración", "integracion", "redis", "helm", "vpn", "sandbox", "microservicio")
_PLAY_KW = ("local", "sintético", "sintetico", "laboratorio", "jupyter", "educativo", "carpeta local", "toy")


def _count_keywords(text: str, keywords: tuple[str, ...]) -> int:
    t = text.lower()
    return sum(1 for kw in keywords if kw in t)


def keyword_density(text: str) -> float:
    n = max(len(text.split()), 1)
    hits = _count_keywords(text, _STOP_KW + _PAUSE_KW + _PLAY_KW)
    return hits / n


def baseline_rules_classify(requirement: str) -> str:
    """Reglas mínimas ES: prioridad stop > pausa > play."""
    t = requirement.lower()
    if any(k in t for k in _STOP_KW):
        return "stop"
    if any(k in t for k in _PAUSE_KW):
        return "pausa"
    if any(k in t for k in _PLAY_KW):
        return "play"
    return "pausa"  # conservador si no hay señal clara


def normalize_lex_scores(scores: Dict[str, float]) -> Dict[str, float]:
    return {k: min(float(scores.get(k, 0.0)) / LEX_SCORE_CAP, 1.0) for k in LABELS}


def risk_score(requirement: str, lex_scores: Dict[str, float]) -> float:
    """
    risk_score = 0.4·norm(stop) + 0.3·norm(pausa) + 0.3·(1−norm(play)) + 0.05·min(kw_density·10, 1)
    """
    n = normalize_lex_scores(lex_scores)
    kw = min(keyword_density(requirement) * 10.0, 1.0)
    raw = W_STOP * n["stop"] + W_PAUSA * n["pausa"] + W_PLAY_INV * (1.0 - n["play"]) + W_KW_DENSITY * kw
    return min(max(raw, 0.0), 1.0)


def math_classify_from_risk(
    risk: float,
    threshold_stop: float = THRESHOLD_STOP,
    threshold_pausa: float = THRESHOLD_PAUSA,
) -> str:
    if risk >= threshold_stop:
        return "stop"
    if risk >= threshold_pausa:
        return "pausa"
    return "play"


# --- Modelo 4D (I_db, I_mem, I_sec, I_dat) — Sprint 6 UNI ---
W_4D_DB = 0.30
W_4D_MEM = 0.15
W_4D_SEC = 0.30
W_4D_DAT = 0.25
W_4D_CTX_STOP = 0.35
W_4D_CTX_PAUSE = 0.18
DIM_SCORE_CAP = 2.0
PLAY_MITIGATION_STEP = 0.12
# Umbrales calibrados al gold v2 ES para risk_score_4d (≠ escala léxica NASA 0.80/0.40)
THRESHOLD_STOP_4D = 0.22
THRESHOLD_PAUSA_4D = 0.10

_DB_SIGNALS: tuple[tuple[str, float], ...] = (
    ("postgresql", 1.2),
    ("mysql", 1.0),
    ("mongodb", 0.9),
    ("sqlite", 0.4),
    ("redis", 0.8),
    ("caché distribuida", 1.0),
    ("cache distribuida", 1.0),
    ("esquema", 0.9),
    ("migración", 1.0),
    ("migracion", 1.0),
    ("facturación", 1.0),
    ("facturacion", 1.0),
    ("etl", 0.8),
    ("replica", 0.7),
    ("índices", 0.7),
    ("indices", 0.7),
    ("base de datos", 1.0),
    ("transaccional", 0.9),
    ("checkout", 0.9),
    ("catálogo público", 0.8),
    ("catalogo publico", 0.8),
)

_MEM_SIGNALS: tuple[tuple[str, float], ...] = (
    ("memoria ram", 0.8),
    ("caché", 0.7),
    ("cache", 0.7),
    ("ttl", 0.9),
    ("heap", 0.7),
    ("buffer", 0.5),
    ("rate limiting", 0.8),
    ("hipervisor", 0.7),
    ("pool", 0.5),
    ("latencias", 0.4),
    ("serialización", 0.6),
    ("serializacion", 0.6),
    ("failover", 0.9),
    ("caché distribuida global", 1.0),
)

_SEC_SIGNALS: tuple[tuple[str, float], ...] = (
    ("oauth", 1.2),
    ("jwt", 1.0),
    ("pci", 1.2),
    ("pci-dss", 1.3),
    ("gdpr", 1.1),
    ("tls", 0.9),
    ("certificados", 0.8),
    ("scada", 1.2),
    ("kms", 1.0),
    ("autenticación", 0.8),
    ("autenticacion", 0.8),
    ("tokenización", 1.0),
    ("tokenizacion", 1.0),
    ("claves maestras", 1.1),
    ("industrial", 0.9),
    ("nube", 0.6),
)

_DAT_SIGNALS: tuple[tuple[str, float], ...] = (
    ("datos personales", 1.2),
    ("datos de clientes", 1.1),
    ("datos de tarjeta", 1.1),
    ("tarjeta", 1.0),
    ("paciente", 1.1),
    ("hospital", 1.0),
    ("clínico", 1.0),
    ("clinico", 1.0),
    ("identificable", 1.0),
    ("pago", 0.9),
    ("pasarela", 1.0),
    ("liquidaciones", 0.9),
    ("adquirente", 0.8),
    ("ingresos", 0.7),
    ("cuadros de mando financieros", 0.8),
    ("retención", 0.9),
    ("retencion", 0.9),
    ("política", 0.7),
    ("politica", 0.7),
)

_CONTEXT_STOP: tuple[str, ...] = (
    "producción",
    "produccion",
    "productivo",
    "crítica",
    "critica",
    "impacto",
    "disponibilidad",
    "mercados",
    "público",
    "publico",
    "checkout",
    "pasarela",
    "industrial",
)

_CONTEXT_PAUSE: tuple[str, ...] = (
    "staging",
    "integración",
    "integracion",
    "feature flag",
    "pruebas",
    "interno",
    "desarrollo",
    "sandbox",
    "rollback",
    "microservicio",
    "helm",
    "vpn",
    "namespace de prueba",
    "pipeline ci",
)


def _context_score(text: str, keywords: tuple[str, ...], cap: int = 3) -> float:
    hits = _count_keywords(text, keywords)
    return min(hits / cap, 1.0)


def _weighted_dim_score(text: str, signals: tuple[tuple[str, float], ...]) -> float:
    raw = sum(w for kw, w in signals if kw in text.lower())
    return min(max(raw / DIM_SCORE_CAP, 0.0), 1.0)


def dimension_scores_4d(text: str) -> Dict[str, float]:
    """Scores normalizados ∈ [0,1] para las cuatro dimensiones de impacto."""
    t = text.lower()
    prod_boost = 0.2 * sum(1 for kw in _CONTEXT_STOP if kw in t)
    return {
        "I_db": min(_weighted_dim_score(text, _DB_SIGNALS) + prod_boost * 0.5, 1.0),
        "I_mem": _weighted_dim_score(text, _MEM_SIGNALS),
        "I_sec": min(_weighted_dim_score(text, _SEC_SIGNALS) + prod_boost * 0.4, 1.0),
        "I_dat": min(_weighted_dim_score(text, _DAT_SIGNALS) + prod_boost * 0.4, 1.0),
        "I_ctx_stop": _context_score(text, _CONTEXT_STOP),
        "I_ctx_pause": _context_score(text, _CONTEXT_PAUSE),
    }


def compute_risk_score_4d(text: str) -> Tuple[float, Dict[str, float]]:
    """
    risk_score_4d = 0.30·I_db + 0.15·I_mem + 0.30·I_sec + 0.25·I_dat
                    + 0.35·I_ctx_stop + 0.18·I_ctx_pause,
    atenuado por señales play (local/educativo).
    """
    dims = dimension_scores_4d(text)
    raw = (
        W_4D_DB * dims["I_db"]
        + W_4D_MEM * dims["I_mem"]
        + W_4D_SEC * dims["I_sec"]
        + W_4D_DAT * dims["I_dat"]
        + W_4D_CTX_STOP * dims["I_ctx_stop"]
        + W_4D_CTX_PAUSE * dims["I_ctx_pause"]
    )
    play_hits = _count_keywords(text, _PLAY_KW)
    mitigation = max(0.0, 1.0 - PLAY_MITIGATION_STEP * play_hits)
    risk = min(max(raw * mitigation, 0.0), 1.0)
    return risk, dims


def classify_4d(text: str, *, threshold_stop: float | None = None, threshold_pausa: float | None = None) -> str:
    risk, _ = compute_risk_score_4d(text)
    ts = THRESHOLD_STOP_4D if threshold_stop is None else threshold_stop
    tp = THRESHOLD_PAUSA_4D if threshold_pausa is None else threshold_pausa
    return math_classify_from_risk(risk, ts, tp)


def calibrate_thresholds_4d(
    texts: list[str],
    labels: list[str],
    *,
    stop_grid: tuple[float, ...] | None = None,
    pausa_grid: tuple[float, ...] | None = None,
) -> tuple[float, float, float]:
    """Busca umbrales maximizando F1-macro en el subconjunto dado (p. ej. train del holdout)."""
    from sklearn.metrics import f1_score

    risks = np.array([compute_risk_score_4d(t)[0] for t in texts])
    y = np.array(labels)
    stop_grid = stop_grid or tuple(round(x, 2) for x in np.arange(0.10, 0.55, 0.02))
    pausa_grid = pausa_grid or tuple(round(x, 2) for x in np.arange(0.04, 0.30, 0.02))
    best_ts, best_tp, best_f1 = THRESHOLD_STOP_4D, THRESHOLD_PAUSA_4D, -1.0
    for ts in stop_grid:
        for tp in pausa_grid:
            if tp >= ts:
                continue
            pred = np.array(["stop" if r >= ts else ("pausa" if r >= tp else "play") for r in risks])
            f1 = float(f1_score(y, pred, labels=list(LABELS), average="macro", zero_division=0))
            if f1 > best_f1:
                best_ts, best_tp, best_f1 = float(ts), float(tp), f1
    return best_ts, best_tp, best_f1


def make_math_predict(lexical_fn: Callable[[str], Tuple[str, Dict[str, float]]]) -> Callable[[str], str]:
    def predict(requirement: str) -> str:
        _, scores = lexical_fn(requirement)
        return math_classify_from_risk(risk_score(requirement, scores))

    return predict


# --- Sprint 6 v2 BugsRepo (inglés, Bugzilla short_desc) ---

_STOP_KW_EN = (
    "crash",
    "deadlock",
    "hang",
    "freeze",
    "unusable",
    "corrupt",
    "segfault",
    "fatal",
    "core dump",
    "data loss",
)
_PAUSE_KW_EN = (
    "api",
    "endpoint",
    "migration",
    "database",
    "query",
    "refactor",
    "controller",
    "service",
    "module",
    "memory leak",
    "overflow",
    "security",
)
_PLAY_KW_EN = ("typo", "cosmetic", "documentation", "doc ", "spelling", "ui polish", "test case", "unit test")

_DB_SIGNALS_EN: tuple[tuple[str, float], ...] = (
    ("deadlock", 1.2),
    ("crash", 1.0),
    ("hang", 1.0),
    ("freeze", 0.9),
    ("replica", 0.8),
    ("transaction", 0.9),
    ("rollback", 0.9),
    ("database", 0.8),
    ("query", 0.6),
    ("migration", 0.7),
)
_MEM_SIGNALS_EN: tuple[tuple[str, float], ...] = (
    ("memory leak", 1.2),
    ("out of memory", 1.1),
    ("heap overflow", 1.0),
    ("stack overflow", 1.0),
    ("buffer overflow", 1.0),
    ("null pointer", 0.9),
    ("oom", 1.0),
)
_SEC_SIGNALS_EN: tuple[tuple[str, float], ...] = (
    ("sql injection", 1.3),
    ("injection", 1.1),
    ("xss", 1.0),
    ("cross-site", 1.0),
    ("bypass", 1.0),
    ("privilege", 0.9),
    ("authentication", 0.8),
    ("exploit", 1.1),
    ("vulnerability", 1.0),
    ("rce", 1.1),
    ("csrf", 0.9),
)
_DAT_SIGNALS_EN: tuple[tuple[str, float], ...] = (
    ("data loss", 1.2),
    ("data corruption", 1.1),
    ("race condition", 0.9),
    ("integrity", 0.8),
    ("corruption", 0.9),
    ("inconsistent", 0.8),
)
_CONTEXT_STOP_EN: tuple[str, ...] = ("unusable", "blocker", "critical", "production", "fatal", "crash")
_CONTEXT_PAUSE_EN: tuple[str, ...] = ("api", "endpoint", "regression", "performance", "timeout", "update")

# Umbrales NASA/Bugzilla (escala 0–1 del guion Colab EN)
THRESHOLD_STOP_4D_EN = 0.70
THRESHOLD_PAUSA_4D_EN = 0.35

PESOS_EN = {"db": 0.40, "mem": 0.30, "sec": 0.20, "dat": 0.10}
KW_DB_EN = [s for s, _ in _DB_SIGNALS_EN] + ["unusable", "abort"]
KW_MEM_EN = [s for s, _ in _MEM_SIGNALS_EN]
KW_SEC_EN = [s for s, _ in _SEC_SIGNALS_EN]
KW_DAT_EN = [s for s, _ in _DAT_SIGNALS_EN]
KW_MEDIUM_EN = [
    "api",
    "endpoint",
    "route",
    "table",
    "controller",
    "migration",
    "service",
    "module",
    "plugin",
    "extension",
    "dependency",
    "refactor",
    "update",
    "query",
]


def dimension_scores_4d_en(text: str) -> Dict[str, float]:
    t = text.lower()
    prod_boost = 0.2 * sum(1 for kw in _CONTEXT_STOP_EN if kw in t)
    return {
        "I_db": min(_weighted_dim_score(text, _DB_SIGNALS_EN) + prod_boost * 0.5, 1.0),
        "I_mem": _weighted_dim_score(text, _MEM_SIGNALS_EN),
        "I_sec": min(_weighted_dim_score(text, _SEC_SIGNALS_EN) + prod_boost * 0.4, 1.0),
        "I_dat": min(_weighted_dim_score(text, _DAT_SIGNALS_EN) + prod_boost * 0.3, 1.0),
        "I_ctx_stop": _context_score(text, _CONTEXT_STOP_EN),
        "I_ctx_pause": _context_score(text, _CONTEXT_PAUSE_EN),
    }


def compute_risk_score_4d_en(text: str) -> Tuple[float, Dict[str, float]]:
    """Modelo 4D en inglés para short_desc Bugzilla (Sprint 6 v2)."""
    dims = dimension_scores_4d_en(text)
    raw = (
        W_4D_DB * dims["I_db"]
        + W_4D_MEM * dims["I_mem"]
        + W_4D_SEC * dims["I_sec"]
        + W_4D_DAT * dims["I_dat"]
        + W_4D_CTX_STOP * dims["I_ctx_stop"]
        + W_4D_CTX_PAUSE * dims["I_ctx_pause"]
    )
    play_hits = _count_keywords(text, _PLAY_KW_EN)
    mitigation = max(0.0, 1.0 - PLAY_MITIGATION_STEP * play_hits)
    risk = min(max(raw * mitigation, 0.0), 1.0)
    return risk, dims


def classify_4d_en(
    text: str,
    *,
    threshold_stop: float | None = None,
    threshold_pausa: float | None = None,
) -> str:
    risk, _ = compute_risk_score_4d_en(text)
    ts = THRESHOLD_STOP_4D_EN if threshold_stop is None else threshold_stop
    tp = THRESHOLD_PAUSA_4D_EN if threshold_pausa is None else threshold_pausa
    return math_classify_from_risk(risk, ts, tp)


def compute_risk_score_simple_en(desc: str) -> dict:
    """Risk score binario por dimensión (guion Colab VAR-2 simplificado)."""
    d = str(desc).lower()
    scores = {
        "db": 1.0 if any(k in d for k in KW_DB_EN) else 0.0,
        "mem": 1.0 if any(k in d for k in KW_MEM_EN) else 0.0,
        "sec": 1.0 if any(k in d for k in KW_SEC_EN) else 0.0,
        "dat": 1.0 if any(k in d for k in KW_DAT_EN) else 0.0,
    }
    if max(scores.values()) == 0 and any(k in d for k in KW_MEDIUM_EN):
        scores["db"] = 0.5
    risk = sum(PESOS_EN[dim] * scores[dim] for dim in PESOS_EN)
    return {"risk_score": round(risk, 4), "components": scores}


def simulate_baseline(desc: str) -> str:
    """Proxy zero-shot (NO es LLM real)."""
    d = str(desc).lower()
    if any(k in d for k in ["crash", "deadlock", "hang", "freeze", "unusable", "corrupt"]):
        return "stop"
    if any(
        k in d
        for k in [
            "api",
            "endpoint",
            "route",
            "controller",
            "service",
            "migration",
            "database",
            "query",
            "refactor",
            "table",
            "module",
        ]
    ):
        return "pausa"
    if any(k in d for k in ["memory leak", "injection", "bypass", "overflow", "xss", "security", "privilege", "exploit"]):
        return "pausa"
    return "play"


def simulate_var1_rag(desc: str) -> str:
    """Proxy VAR-1 RAG (NO es MetaGPT/pgvector real)."""
    d = str(desc).lower()
    if any(k in d for k in ["crash", "deadlock", "injection", "bypass", "exploit", "corruption"]):
        return "stop"
    if any(k in d for k in ["api", "endpoint", "route", "table", "migration", "controller"]):
        return "pausa"
    if any(k in d for k in ["memory leak", "overflow"]):
        return "pausa"
    if any(k in d for k in ["security", "plugin", "extension", "update", "version"]):
        return "stop"
    return "play"


def simulate_var2_math(desc: str) -> str:
    """VAR-2: modelo 4D EN (umbrales guion 0.70 / 0.35)."""
    rs = compute_risk_score_4d_en(desc)[0]
    if rs >= THRESHOLD_STOP_4D_EN:
        return "stop"
    if rs >= THRESHOLD_PAUSA_4D_EN:
        return "pausa"
    return "play"


def simulate_var2_math_simple(desc: str) -> str:
    """VAR-2 alternativo: risk_score simple del guion Colab."""
    rs = compute_risk_score_simple_en(desc)["risk_score"]
    if rs >= 0.70:
        return "stop"
    if rs >= 0.35:
        return "pausa"
    return "play"


# --- VAR-3 Camino B-lite: RAG + UQ + fuzzy + politica HITL ---


def _clip01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _triangular(value: float, left: float, peak: float, right: float) -> float:
    value = float(value)
    if value <= left or value >= right:
        return 0.0
    if value == peak:
        return 1.0
    if value < peak:
        return _clip01((value - left) / max(peak - left, 1e-9))
    return _clip01((right - value) / max(right - peak, 1e-9))


def _trapezoid(value: float, left: float, start: float, end: float, right: float) -> float:
    value = float(value)
    if value <= left or value >= right:
        return 0.0
    if start <= value <= end:
        return 1.0
    if value < start:
        return _clip01((value - left) / max(start - left, 1e-9))
    return _clip01((right - value) / max(right - end, 1e-9))


def label_distribution_from_votes(votes: dict[str, int] | None, *, labels: tuple[str, ...] = LABELS) -> dict[str, float]:
    """Convierte votos RAG top-k en una distribucion sobre play/pausa/stop."""
    counts = {label: int((votes or {}).get(label, 0)) for label in labels}
    total = sum(counts.values())
    if total <= 0:
        return {label: 1.0 / len(labels) for label in labels}
    return {label: counts[label] / total for label in labels}


def entropy01(probs: dict[str, float], *, labels: tuple[str, ...] = LABELS) -> float:
    """Entropia normalizada [0,1], usada como incertidumbre aleatorica barata."""
    values = [_clip01(float(probs.get(label, 0.0))) for label in labels]
    total = sum(values)
    if total <= 0:
        return 1.0
    normalized = [v / total for v in values]
    entropy = -sum(p * math.log(p) for p in normalized if p > 0)
    return _clip01(entropy / math.log(len(labels)))


def margin_uncertainty(probs: dict[str, float], *, labels: tuple[str, ...] = LABELS) -> float:
    """1 - margen entre las dos clases mas probables; alto implica decision fragil."""
    ordered = sorted((_clip01(float(probs.get(label, 0.0))) for label in labels), reverse=True)
    if len(ordered) < 2:
        return 1.0
    return _clip01(1.0 - (ordered[0] - ordered[1]))


def rag_similarity_confidence(neighbors: list[dict[str, Any]] | None) -> float:
    """
    Confianza epistemica proxy desde distancia RAG.

    pgvector con distancia coseno suele devolver 0 para identico y ~1 para lejano.
    Se promedian top-k y se invierte a similitud [0,1].
    """
    distances = [float(n.get("distance", 1.0)) for n in (neighbors or []) if n.get("distance") is not None]
    if not distances:
        return 0.0
    return _clip01(1.0 - float(np.mean(distances)))


def _votes_from_neighbors(neighbors: list[dict[str, Any]] | None) -> dict[str, int]:
    return dict(Counter(str(n.get("label")) for n in (neighbors or []) if str(n.get("label")) in LABELS))


def fuzzy_memberships_camino_b(
    *,
    risk_4d: float,
    uncertainty: float,
    rag_similarity: float,
    sec_dat_impact: float,
) -> dict[str, dict[str, float]]:
    """Memberships fuzzy-lite interpretables para impacto, incertidumbre y confianza RAG."""
    return {
        "risk_4d": {
            "low": _trapezoid(risk_4d, -0.01, 0.0, 0.16, 0.32),
            "medium": _triangular(risk_4d, 0.18, 0.42, 0.68),
            "high": _trapezoid(risk_4d, 0.45, 0.68, 1.0, 1.01),
        },
        "uncertainty": {
            "low": _trapezoid(uncertainty, -0.01, 0.0, 0.18, 0.36),
            "medium": _triangular(uncertainty, 0.22, 0.50, 0.78),
            "high": _trapezoid(uncertainty, 0.58, 0.78, 1.0, 1.01),
        },
        "rag_similarity": {
            "low": _trapezoid(rag_similarity, -0.01, 0.0, 0.28, 0.48),
            "medium": _triangular(rag_similarity, 0.34, 0.56, 0.78),
            "high": _trapezoid(rag_similarity, 0.66, 0.82, 1.0, 1.01),
        },
        "sec_dat_impact": {
            "low": _trapezoid(sec_dat_impact, -0.01, 0.0, 0.18, 0.36),
            "medium": _triangular(sec_dat_impact, 0.22, 0.50, 0.76),
            "high": _trapezoid(sec_dat_impact, 0.58, 0.78, 1.0, 1.01),
        },
    }


def _label_to_value(label: str) -> float:
    return {"play": 0.0, "pausa": 0.5, "stop": 1.0}.get(label, 0.5)


def criticidad_var3_camino_b_lite(
    text: str,
    *,
    base_label: str | None = None,
    neighbors: list[dict[str, Any]] | None = None,
    neighbor_votes: dict[str, int] | None = None,
    llm_confidence: float | None = None,
    llm_label: str | None = None,
    hitl_cost_pause: float = 0.08,
    hitl_cost_stop: float = 0.18,
    false_negative_stop_cost: float = 1.0,
) -> dict[str, Any]:
    """
    VAR-3 Camino B-lite sin usar etiquetas gold como feature.

    Integra 4D, incertidumbre por margen/entropia, confianza RAG por distancia,
    fuzzy-lite y una politica HITL con costo de escalar vs costo de falso negativo STOP.
    """
    risk_4d, dims = compute_risk_score_4d_en(text)
    votes = dict(neighbor_votes or _votes_from_neighbors(neighbors))
    probs = label_distribution_from_votes(votes)
    if llm_label in LABELS and llm_confidence is not None:
        conf = _clip01(float(llm_confidence))
        probs = {label: 0.30 * probs.get(label, 0.0) for label in LABELS}
        probs[str(llm_label)] = probs.get(str(llm_label), 0.0) + 0.70 * conf
        missing = max(1.0 - sum(probs.values()), 0.0)
        for label in LABELS:
            probs[label] += missing / len(LABELS)
    margin_u = margin_uncertainty(probs)
    entropy_u = entropy01(probs)
    retrieval_u = _clip01(1.0 - rag_similarity_confidence(neighbors))
    confidence_u = _clip01(1.0 - float(llm_confidence)) if llm_confidence is not None else 0.5
    uncertainty = _clip01(0.40 * margin_u + 0.30 * entropy_u + 0.20 * retrieval_u + 0.10 * confidence_u)
    rag_sim = rag_similarity_confidence(neighbors)
    sec_dat_impact = max(float(dims.get("I_sec", 0.0)), float(dims.get("I_dat", 0.0)))
    memberships = fuzzy_memberships_camino_b(
        risk_4d=risk_4d,
        uncertainty=uncertainty,
        rag_similarity=rag_sim,
        sec_dat_impact=sec_dat_impact,
    )

    base = base_label if base_label in LABELS else max(probs, key=probs.get)
    fuzzy_stop = max(
        memberships["risk_4d"]["high"],
        memberships["sec_dat_impact"]["high"],
        min(memberships["risk_4d"]["medium"], memberships["uncertainty"]["high"]),
    )
    fuzzy_pausa = max(
        memberships["risk_4d"]["medium"],
        memberships["uncertainty"]["medium"],
        min(memberships["rag_similarity"]["low"], memberships["uncertainty"]["high"]),
    )
    fuzzy_play = min(
        memberships["risk_4d"]["low"],
        memberships["uncertainty"]["low"],
        memberships["rag_similarity"]["high"],
    )

    expected_stop_miss_cost = false_negative_stop_cost * max(probs.get("stop", 0.0), fuzzy_stop) * (0.55 + 0.45 * uncertainty)
    score_value = (
        0.34 * _label_to_value(base)
        + 0.26 * risk_4d
        + 0.18 * fuzzy_stop
        + 0.12 * probs.get("stop", 0.0)
        + 0.10 * uncertainty
    )

    trace: list[str] = []
    if base == "stop":
        if risk_4d <= 0.02 and probs.get("stop", 0.0) <= 0.20 and uncertainty >= 0.74:
            label = "pausa"
            trace.append("PAUSA: STOP RAG debil con incertidumbre muy alta")
        else:
            label = "stop"
            trace.append("STOP: se conserva RAG ante posible falso negativo critico")
    elif expected_stop_miss_cost > hitl_cost_stop + 0.30 and (
        risk_4d >= 0.34 or fuzzy_stop >= 0.55 or probs.get("stop", 0.0) >= 0.60
    ):
        label = "stop"
        trace.append("STOP: costo esperado de falso negativo supera costo HITL")
    elif score_value >= 0.68 and (risk_4d >= 0.30 or fuzzy_stop >= 0.45):
        label = "stop"
        trace.append("STOP: score de riesgo combinado alto")
    elif (
        (base == "play" and risk_4d >= 0.24 and (uncertainty >= 0.46 or fuzzy_pausa >= 0.45))
        or (base == "play" and sec_dat_impact >= 0.60)
        or (base == "pausa" and expected_stop_miss_cost > hitl_cost_pause + 0.22 and risk_4d >= 0.20)
    ):
        label = "pausa"
        trace.append("PAUSA: incertidumbre/riesgo requiere revision humana")
    elif fuzzy_play >= 0.35 and probs.get("play", 0.0) >= 0.60:
        label = "play"
        trace.append("PLAY: baja incertidumbre y RAG consistente")
    else:
        label = base
        trace.append("BASE: se conserva decision RAG")

    return {
        "label": label,
        "base_label": base,
        "risk_score_4d": round(float(risk_4d), 6),
        "uncertainty": round(float(uncertainty), 6),
        "entropy_u": round(float(entropy_u), 6),
        "margin_u": round(float(margin_u), 6),
        "rag_similarity": round(float(rag_sim), 6),
        "expected_stop_miss_cost": round(float(expected_stop_miss_cost), 6),
        "score_value": round(float(score_value), 6),
        "probabilities": {label: round(float(probs.get(label, 0.0)), 6) for label in LABELS},
        "memberships": memberships,
        "trace": trace,
    }

