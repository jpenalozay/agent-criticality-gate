"""
Criticidad SOTA-lite para Play/Pausa/Stop.

Integra stacking ligero, calibracion train-only, abstencion conforme/selectiva,
features 4D, incertidumbre RAG y reglas fuzzy-lite. No usa etiquetas gold como
feature en inferencia; las etiquetas solo se consumen durante fit/calibracion.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from src.math_criticidad import (
    LABELS,
    compute_risk_score_4d_en,
    compute_risk_score_simple_en,
    entropy01,
    fuzzy_memberships_camino_b,
    label_distribution_from_votes,
    margin_uncertainty,
    rag_similarity_confidence,
    simulate_baseline,
)

LABEL_TO_IDX = {label: idx for idx, label in enumerate(LABELS)}
IDX_TO_LABEL = {idx: label for label, idx in LABEL_TO_IDX.items()}


@dataclass
class SotaDecisionConfig:
    """Parametros aprendidos solo en train/calibration."""

    conformal_alpha: float = 0.20
    conformal_qhat: float = 0.70
    min_confidence: float = 0.48
    stop_probability_threshold: float = 0.36
    stop_risk_threshold: float = 0.20
    pause_uncertainty_threshold: float = 0.54
    false_negative_stop_cost: float = 5.0
    human_pause_cost: float = 0.35
    false_stop_cost: float = 1.10


def _clip01(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _votes_from_neighbors(neighbors: list[dict[str, Any]] | None) -> dict[str, int]:
    votes = {label: 0 for label in LABELS}
    for item in neighbors or []:
        label = str(item.get("label", ""))
        if label in votes:
            votes[label] += 1
    return votes


def _distribution_from_label(label: str, confidence: float | None = None) -> dict[str, float]:
    conf = _clip01(_safe_float(confidence, 0.74))
    if label not in LABELS:
        return {item: 1.0 / len(LABELS) for item in LABELS}
    remainder = max(1.0 - conf, 0.0)
    out = {item: remainder / (len(LABELS) - 1) for item in LABELS}
    out[label] = conf
    return out


def _keyword_count(text: str, keywords: tuple[str, ...]) -> int:
    lowered = str(text).lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def extract_sota_features(
    text: str,
    *,
    base_label: str | None = None,
    neighbors: list[dict[str, Any]] | None = None,
    llm_label: str | None = None,
    llm_confidence: float | None = None,
) -> dict[str, float]:
    """
    Features interpretables para stacking.

    Las etiquetas de vecinos provienen solo del history/train usado por RAG. La
    etiqueta real del ejemplo evaluado nunca entra aqui.
    """
    text = str(text)
    risk_4d, dims = compute_risk_score_4d_en(text)
    simple = compute_risk_score_simple_en(text)
    votes = _votes_from_neighbors(neighbors)
    rag_probs = label_distribution_from_votes(votes)
    rag_sim = rag_similarity_confidence(neighbors)
    base = base_label if base_label in LABELS else simulate_baseline(text)
    base_probs = _distribution_from_label(base, 0.76)
    llm_probs = _distribution_from_label(str(llm_label), llm_confidence) if llm_label in LABELS else base_probs
    combined_probs = {
        label: 0.45 * rag_probs.get(label, 0.0) + 0.35 * base_probs.get(label, 0.0) + 0.20 * llm_probs.get(label, 0.0)
        for label in LABELS
    }
    total = sum(combined_probs.values()) or 1.0
    combined_probs = {label: value / total for label, value in combined_probs.items()}

    margin_u = margin_uncertainty(combined_probs)
    entropy_u = entropy01(combined_probs)
    retrieval_u = _clip01(1.0 - rag_sim)
    llm_u = _clip01(1.0 - _safe_float(llm_confidence, 0.50))
    uncertainty = _clip01(0.34 * margin_u + 0.30 * entropy_u + 0.24 * retrieval_u + 0.12 * llm_u)
    sec_dat_impact = max(float(dims.get("I_sec", 0.0)), float(dims.get("I_dat", 0.0)))
    memberships = fuzzy_memberships_camino_b(
        risk_4d=risk_4d,
        uncertainty=uncertainty,
        rag_similarity=rag_sim,
        sec_dat_impact=sec_dat_impact,
    )
    fuzzy_stop = max(
        memberships["risk_4d"]["high"],
        memberships["sec_dat_impact"]["high"],
        min(memberships["risk_4d"]["medium"], memberships["uncertainty"]["high"]),
    )
    fuzzy_pause = max(
        memberships["risk_4d"]["medium"],
        memberships["uncertainty"]["medium"],
        min(memberships["rag_similarity"]["low"], memberships["uncertainty"]["high"]),
    )
    fuzzy_play = min(
        memberships["risk_4d"]["low"],
        memberships["uncertainty"]["low"],
        memberships["rag_similarity"]["high"],
    )
    distances = np.array([_safe_float(item.get("distance"), 1.0) for item in neighbors or []], dtype=float)
    if len(distances) == 0:
        distances = np.array([1.0], dtype=float)

    stop_terms = ("crash", "deadlock", "hang", "freeze", "corrupt", "fatal", "data loss", "unusable")
    security_terms = ("security", "injection", "xss", "csrf", "bypass", "privilege", "exploit", "vulnerability")
    medium_terms = ("api", "endpoint", "database", "query", "migration", "performance", "timeout", "regression")
    play_terms = ("typo", "cosmetic", "documentation", "spelling", "test", "minor")
    token_count = max(len(text.split()), 1)

    features: dict[str, float] = {
        "risk_4d": float(risk_4d),
        "risk_simple": float(simple["risk_score"]),
        "I_db": float(dims.get("I_db", 0.0)),
        "I_mem": float(dims.get("I_mem", 0.0)),
        "I_sec": float(dims.get("I_sec", 0.0)),
        "I_dat": float(dims.get("I_dat", 0.0)),
        "I_ctx_stop": float(dims.get("I_ctx_stop", 0.0)),
        "I_ctx_pause": float(dims.get("I_ctx_pause", 0.0)),
        "sec_dat_impact": sec_dat_impact,
        "rag_similarity": float(rag_sim),
        "rag_distance_mean": float(np.mean(distances)),
        "rag_distance_min": float(np.min(distances)),
        "rag_distance_std": float(np.std(distances)),
        "rag_entropy": entropy01(rag_probs),
        "rag_margin_u": margin_uncertainty(rag_probs),
        "uncertainty": uncertainty,
        "entropy_u": entropy_u,
        "margin_u": margin_u,
        "retrieval_u": retrieval_u,
        "llm_u": llm_u,
        "fuzzy_stop": float(fuzzy_stop),
        "fuzzy_pause": float(fuzzy_pause),
        "fuzzy_play": float(fuzzy_play),
        "text_log_len": float(math.log1p(len(text))),
        "token_log_len": float(math.log1p(token_count)),
        "stop_kw_density": _keyword_count(text, stop_terms) / token_count,
        "security_kw_density": _keyword_count(text, security_terms) / token_count,
        "medium_kw_density": _keyword_count(text, medium_terms) / token_count,
        "play_kw_density": _keyword_count(text, play_terms) / token_count,
    }
    for label in LABELS:
        features[f"base_is_{label}"] = 1.0 if base == label else 0.0
        features[f"rag_p_{label}"] = float(rag_probs.get(label, 0.0))
        features[f"combo_p_{label}"] = float(combined_probs.get(label, 0.0))
    return features


class SotaCriticidadModel:
    """Stacking + calibracion + decision cost-sensitive Play/Pausa/Stop."""

    def __init__(self, random_state: int = 42, config: SotaDecisionConfig | None = None):
        self.random_state = random_state
        self.config = config or SotaDecisionConfig()
        self.feature_names_: list[str] = []
        self.model_: Any | None = None
        self.calibration_report_: dict[str, Any] = {}

    def _matrix(self, rows: list[dict[str, float]]) -> np.ndarray:
        if not self.feature_names_:
            self.feature_names_ = sorted(rows[0].keys())
        return np.array([[float(row.get(name, 0.0)) for name in self.feature_names_] for row in rows], dtype=float)

    def fit(
        self,
        train_features: list[dict[str, float]],
        train_labels: list[str],
        calibration_features: list[dict[str, float]],
        calibration_labels: list[str],
    ) -> "SotaCriticidadModel":
        x_train = self._matrix(train_features)
        y_train = np.array(train_labels)
        class_weight = {"play": 1.0, "pausa": 1.15, "stop": 2.60}
        base_model = Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        C=1.4,
                        max_iter=2000,
                        class_weight=class_weight,
                        random_state=self.random_state,
                    ),
                ),
            ]
        )
        # CalibratedClassifierCV con cv=3 usa solo train; calibration externa queda
        # reservada para conformal/umbrales, evitando tocar test.
        self.model_ = CalibratedClassifierCV(base_model, method="sigmoid", cv=3)
        try:
            self.model_.fit(x_train, y_train)
        except ValueError:
            fallback = HistGradientBoostingClassifier(random_state=self.random_state, max_iter=80, learning_rate=0.06)
            self.model_ = CalibratedClassifierCV(fallback, method="sigmoid", cv=3)
            self.model_.fit(x_train, y_train)
        self._calibrate_decision(calibration_features, calibration_labels)
        return self

    def predict_proba(self, features: list[dict[str, float]]) -> np.ndarray:
        if self.model_ is None:
            raise RuntimeError("SotaCriticidadModel must be fitted before predict.")
        probs_raw = self.model_.predict_proba(self._matrix(features))
        class_order = list(self.model_.classes_)
        out = np.zeros((len(features), len(LABELS)), dtype=float)
        for src_idx, label in enumerate(class_order):
            out[:, LABEL_TO_IDX[str(label)]] = probs_raw[:, src_idx]
        row_sums = out.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0.0] = 1.0
        return out / row_sums

    def _calibrate_decision(self, calibration_features: list[dict[str, float]], calibration_labels: list[str]) -> None:
        probs = self.predict_proba(calibration_features)
        y = np.array(calibration_labels)
        y_idx = np.array([LABEL_TO_IDX[label] for label in y])
        nonconformity = 1.0 - probs[np.arange(len(probs)), y_idx]
        alpha = self.config.conformal_alpha
        q_level = min(max(math.ceil((len(nonconformity) + 1) * (1 - alpha)) / max(len(nonconformity), 1), 0.0), 1.0)
        qhat = float(np.quantile(nonconformity, q_level, method="higher")) if len(nonconformity) else self.config.conformal_qhat

        best = asdict(self.config)
        best["conformal_qhat"] = qhat
        best_score = -1e9
        for min_conf in np.arange(0.38, 0.66, 0.04):
            for stop_prob in np.arange(0.28, 0.56, 0.04):
                for stop_risk in np.arange(0.10, 0.34, 0.04):
                    candidate = SotaDecisionConfig(
                        conformal_alpha=alpha,
                        conformal_qhat=qhat,
                        min_confidence=float(min_conf),
                        stop_probability_threshold=float(stop_prob),
                        stop_risk_threshold=float(stop_risk),
                    )
                    preds = [self._decide_one(row, prob, candidate)["label"] for row, prob in zip(calibration_features, probs)]
                    macro = f1_score(y, preds, labels=list(LABELS), average="macro", zero_division=0)
                    f1_each = f1_score(y, preds, labels=list(LABELS), average=None, zero_division=0)
                    cost = np.mean([policy_cost(true, pred) for true, pred in zip(y, preds)])
                    score = float(macro + 0.18 * f1_each[LABEL_TO_IDX["stop"]] - 0.035 * cost)
                    if score > best_score:
                        best_score = score
                        best.update(
                            {
                                "min_confidence": float(min_conf),
                                "stop_probability_threshold": float(stop_prob),
                                "stop_risk_threshold": float(stop_risk),
                            }
                        )
        self.config = SotaDecisionConfig(**best)
        final_preds = [self._decide_one(row, prob, self.config)["label"] for row, prob in zip(calibration_features, probs)]
        self.calibration_report_ = {
            "config": asdict(self.config),
            "calibration_n": int(len(calibration_labels)),
            "calibration_macro_f1": float(f1_score(y, final_preds, labels=list(LABELS), average="macro", zero_division=0)),
            "calibration_stop_f1": float(
                f1_score(y, final_preds, labels=list(LABELS), average=None, zero_division=0)[LABEL_TO_IDX["stop"]]
            ),
            "calibration_policy_cost": float(np.mean([policy_cost(true, pred) for true, pred in zip(y, final_preds)])),
            "selection_note": "Grid search train/calibration-only; test labels not used.",
        }

    def _decide_one(self, feature: dict[str, float], probs: np.ndarray, config: SotaDecisionConfig) -> dict[str, Any]:
        top_idx = int(np.argmax(probs))
        top_label = IDX_TO_LABEL[top_idx]
        top_conf = float(probs[top_idx])
        nonconformity = 1.0 - probs
        conformal_set = [IDX_TO_LABEL[idx] for idx, score in enumerate(nonconformity) if score <= config.conformal_qhat]
        if not conformal_set:
            conformal_set = [top_label]
        risk = float(feature.get("risk_4d", 0.0))
        uncertainty = float(feature.get("uncertainty", 0.0))
        fuzzy_stop = float(feature.get("fuzzy_stop", 0.0))
        p_stop = float(probs[LABEL_TO_IDX["stop"]])
        p_pausa = float(probs[LABEL_TO_IDX["pausa"]])
        trace: list[str] = []
        if (
            p_stop >= config.stop_probability_threshold
            and (risk >= config.stop_risk_threshold or fuzzy_stop >= 0.42 or "stop" in conformal_set)
        ):
            label = "stop"
            trace.append("STOP por costo asimetrico y probabilidad calibrada")
        elif "stop" in conformal_set and (risk >= 0.18 or fuzzy_stop >= 0.38) and top_label != "play":
            label = "stop"
            trace.append("STOP por conjunto conforme con riesgo suficiente")
        elif (
            top_conf < config.min_confidence
            or uncertainty >= config.pause_uncertainty_threshold + 0.10
            or (len(conformal_set) > 1 and uncertainty >= config.pause_uncertainty_threshold)
        ):
            label = "pausa"
            trace.append("PAUSA por abstencion selectiva/incertidumbre")
        elif top_label == "play" and (risk >= 0.26 or p_pausa >= 0.42):
            label = "pausa"
            trace.append("PAUSA por riesgo residual pese a top play")
        else:
            label = top_label
            trace.append("Prediccion calibrada directa")
        return {
            "label": label,
            "top_label": top_label,
            "confidence": round(top_conf, 6),
            "p_play": round(float(probs[LABEL_TO_IDX["play"]]), 6),
            "p_pausa": round(float(probs[LABEL_TO_IDX["pausa"]]), 6),
            "p_stop": round(p_stop, 6),
            "conformal_set": conformal_set,
            "trace": trace,
        }

    def predict(self, features: list[dict[str, float]]) -> list[dict[str, Any]]:
        probs = self.predict_proba(features)
        return [self._decide_one(row, prob, self.config) for row, prob in zip(features, probs)]

    def to_json(self) -> str:
        return json.dumps(
            {
                "feature_names": self.feature_names_,
                "calibration_report": self.calibration_report_,
            },
            ensure_ascii=False,
            indent=2,
        )


def policy_cost(true_label: str, pred_label: str) -> float:
    """Costo operativo: falso negativo STOP domina; PAUSA representa HITL."""
    if true_label == pred_label:
        return 0.35 if pred_label == "pausa" else 0.0
    if true_label == "stop" and pred_label == "play":
        return 5.0
    if true_label == "stop" and pred_label == "pausa":
        return 1.25
    if true_label != "stop" and pred_label == "stop":
        return 1.10
    if pred_label == "pausa":
        return 0.55
    return 1.0

