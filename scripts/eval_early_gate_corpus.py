#!/usr/bin/env python3
"""
Evalúa `EarlyGate.decide` frente a `gold_mode` en casos_gold_criticidad_v2.jsonl (300 filas).

Métricas: accuracy, F1-macro / por clase, matriz de confusión, Cohen's κ.
Salidas: JSON de resumen, CSV de predicciones, figuras (confusión, barras por clase).

Requisitos:
  - Variable de entorno DEEPSEEK_API_KEY (no commitear la clave).
  - Ejecutar desde cualquier cwd; el script resuelve rutas respecto a `agent-criticality-gate/`.

Uso:
  python scripts/eval_early_gate_corpus.py
  python scripts/eval_early_gate_corpus.py --limit 10
  $env:DEEPSEEK_API_KEY="..."   # PowerShell
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Raíz del bloque tesis (directorio padre de scripts/)
TESIS2_ROOT = Path(__file__).resolve().parent.parent
AGENTES_DIR = TESIS2_ROOT / "agentes"
CORPUS = TESIS2_ROOT / "data" / "criticidad_cases" / "casos_gold_criticidad_v2.jsonl"
REPORTS_DIR = TESIS2_ROOT / "reports"


def _load_env_file() -> None:
    """Carga `agent-criticality-gate/.env` si existe (python-dotenv opcional)."""
    try:
        from dotenv import load_dotenv

        load_dotenv(TESIS2_ROOT / ".env")
    except ImportError:
        pass


def _ensure_agentes_path() -> None:
    sys.path.insert(0, str(AGENTES_DIR))


def load_jsonl(path: Path, limit: int | None) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
            if limit is not None and len(rows) >= limit:
                break
    return rows


def main() -> int:
    _load_env_file()

    parser = argparse.ArgumentParser(description="Evaluar EarlyGate vs gold_mode")
    parser.add_argument("--limit", type=int, default=None, help="Solo N primeras filas (prueba rápida)")
    parser.add_argument(
        "--delay",
        type=float,
        default=float(os.getenv("EARLY_EVAL_DELAY_SEC", "0.35")),
        help="Pausa entre llamadas LLM (segundos)",
    )
    parser.add_argument("--no-plots", action="store_true", help="No generar PNG")
    args = parser.parse_args()

    if not os.getenv("DEEPSEEK_API_KEY", "").strip():
        print(
            "ERROR: Defina DEEPSEEK_API_KEY en el entorno (no la guarde en el repo).\n"
            "  PowerShell example: $env:DEEPSEEK_API_KEY='your_api_key_here'\n"
            "  Ejemplo bash: export DEEPSEEK_API_KEY=...",
            file=sys.stderr,
        )
        return 2

    if not CORPUS.is_file():
        print(f"ERROR: No existe el corpus: {CORPUS}", file=sys.stderr)
        return 2

    _ensure_agentes_path()

    try:
        from sklearn.metrics import (
            accuracy_score,
            classification_report,
            cohen_kappa_score,
            confusion_matrix,
            f1_score,
            precision_recall_fscore_support,
        )
    except ImportError as e:
        print("ERROR: instale scikit-learn: pip install scikit-learn", e, file=sys.stderr)
        return 2

    rows = load_jsonl(CORPUS, args.limit)
    if not rows:
        print("ERROR: corpus vacío", file=sys.stderr)
        return 2

    try:
        from tqdm import tqdm
    except ImportError:
        tqdm = None  # type: ignore[misc, assignment]

    from core.early_gate import EarlyGate

    gate = EarlyGate()
    labels = ["play", "pausa", "stop"]
    y_true: list[str] = []
    y_pred: list[str] = []
    details: list[dict] = []

    iterator = rows
    if tqdm is not None:
        iterator = tqdm(rows, desc="EarlyGate.decide", unit="caso")

    t0 = time.perf_counter()
    for i, row in enumerate(iterator):
        req = row.get("requirement", "")
        gold = row.get("gold_mode", "")
        rid = row.get("id", str(i))

        out = gate.decide(req)
        pred = out.get("gold_mode", "pausa")
        if pred not in labels:
            pred = "pausa"

        y_true.append(gold)
        y_pred.append(pred)
        details.append({
            "id": rid,
            "gold_mode": gold,
            "predicted_mode": pred,
            "match": gold == pred,
            "source": out.get("source"),
            "confidence": out.get("confidence"),
            "doubt": out.get("doubt"),
            "llm_detail": out.get("llm_detail"),
        })

        if i + 1 < len(rows) and args.delay > 0:
            time.sleep(args.delay)

    elapsed = time.perf_counter() - t0

    acc = accuracy_score(y_true, y_pred)
    f1_macro = f1_score(y_true, y_pred, labels=labels, average="macro", zero_division=0)
    f1_per = f1_score(y_true, y_pred, labels=labels, average=None, zero_division=0)
    kappa = cohen_kappa_score(y_true, y_pred, labels=labels)
    cm = confusion_matrix(y_true, y_pred, labels=labels)
    report = classification_report(
        y_true, y_pred, labels=labels, zero_division=0, digits=4
    )

    prec, rec, f1_prf, support_vec = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    per_class_rows = [
        {
            "class": labels[j],
            "precision": float(prec[j]),
            "recall": float(rec[j]),
            "f1": float(f1_prf[j]),
            "support": int(support_vec[j]),
        }
        for j in range(len(labels))
    ]

    by_source: dict[str, dict[str, float | int]] = {}
    for d in details:
        src = str(d.get("source") or "unknown")
        if src not in by_source:
            by_source[src] = {"n": 0, "correct": 0}
        by_source[src]["n"] += 1
        if d.get("match"):
            by_source[src]["correct"] += 1
    for src in list(by_source.keys()):
        n = int(by_source[src]["n"])
        c = int(by_source[src]["correct"])
        by_source[src]["accuracy"] = float(c / n) if n else 0.0

    corpus_rel = str(CORPUS.relative_to(TESIS2_ROOT)).replace("\\", "/")
    summary = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "corpus": corpus_rel,
        "n_samples": len(rows),
        "elapsed_sec": round(elapsed, 2),
        "delay_sec": args.delay,
        "metrics": {
            "accuracy": float(acc),
            "f1_macro": float(f1_macro),
            "cohen_kappa": float(kappa),
            "f1_per_class": {lab: float(f1_per[j]) for j, lab in enumerate(labels)},
        },
        "confusion_matrix": {labels[i]: {labels[j]: int(cm[i, j]) for j in range(3)} for i in range(3)},
        "classification_report_text": report,
        "analysis_second_pass": {
            "per_class_precision_recall_support": per_class_rows,
            "by_decision_source": by_source,
            "interpretation": (
                "Primera pasada: métricas globales y matriz de confusión. "
                "Segunda pasada: desglose por clase (precisión/recall/F1 y soporte) "
                "y acierto condicionado a la fuente (LLM puro, léxico, fusión, etc.)."
            ),
        },
        "note": "ROC-AUC multiclase omitido: EarlyGate no entrega un vector de probabilidad por clase; F1 y κ son las métricas centrales del informe.",
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = REPORTS_DIR / f"early_gate_eval_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "classification_report.txt").write_text(report, encoding="utf-8")

    with (out_dir / "predictions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["id", "gold_mode", "predicted_mode", "match", "source", "confidence", "doubt"],
        )
        w.writeheader()
        for d in details:
            w.writerow({
                "id": d["id"],
                "gold_mode": d["gold_mode"],
                "predicted_mode": d["predicted_mode"],
                "match": d["match"],
                "source": d["source"],
                "confidence": d["confidence"],
                "doubt": d["doubt"],
            })

    # Markdown ejecutivo
    md_lines = [
        "# Informe — EarlyGate vs gold (`casos_gold_criticidad_v2`)",
        "",
        f"- **Muestras:** {len(rows)}",
        f"- **Tiempo total:** {elapsed:.1f} s (delay {args.delay}s entre casos)",
        f"- **Accuracy:** {acc:.4f}",
        f"- **F1-macro:** {f1_macro:.4f}",
        f"- **Cohen κ:** {kappa:.4f}",
        "",
        "## F1 por clase",
        "",
        "| Clase | F1 |",
        "|-------|-----|",
    ]
    for j, lab in enumerate(labels):
        md_lines.append(f"| {lab} | {f1_per[j]:.4f} |")
    md_lines.extend(
        [
            "",
            "## Segunda pasada — precisión / recall / soporte por clase",
            "",
            "| Clase | Precisión | Recall | Soporte |",
            "|-------|-----------|--------|---------|",
        ]
    )
    for row in per_class_rows:
        md_lines.append(
            f"| {row['class']} | {row['precision']:.4f} | {row['recall']:.4f} | {row['support']} |"
        )
    md_lines.extend(["", "## Segunda pasada — acierto por `source`", "", "| Fuente | n | correctos | accuracy |", "|--------|---|-----------|----------|"])
    for src, st in sorted(by_source.items(), key=lambda x: -x[1]["n"]):
        md_lines.append(
            f"| `{src}` | {st['n']} | {st['correct']} | {st['accuracy']:.4f} |"
        )
    md_lines.extend(["", "## Matriz de confusión (filas=gold, columnas=pred)", "", "```"])
    md_lines.append(str(cm))
    md_lines.extend(["```", "", "## Nota metodológica", "", summary["note"], ""])
    (out_dir / "informe.md").write_text("\n".join(md_lines), encoding="utf-8")

    if not args.no_plots:
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            import numpy as np
            import seaborn as sns

            fig, ax = plt.subplots(figsize=(6, 5))
            sns.heatmap(
                cm,
                annot=True,
                fmt="d",
                cmap="Blues",
                xticklabels=labels,
                yticklabels=labels,
                ax=ax,
            )
            ax.set_xlabel("Predicho (EarlyGate)")
            ax.set_ylabel("Gold")
            ax.set_title("Matriz de confusión")
            plt.tight_layout()
            plt.savefig(out_dir / "confusion_matrix.png", dpi=150)
            plt.close()

            fig2, ax2 = plt.subplots(figsize=(7, 4))
            x = np.arange(len(labels))
            ax2.bar(x - 0.2, [f1_per[i] for i in range(3)], width=0.4, label="F1 por clase")
            ax2.set_xticks(x)
            ax2.set_xticklabels(labels)
            ax2.set_ylim(0, 1.05)
            ax2.set_ylabel("F1")
            ax2.set_title("Desempeño por clase (baseline EarlyGate)")
            ax2.legend()
            plt.tight_layout()
            plt.savefig(out_dir / "f1_per_class.png", dpi=150)
            plt.close()
        except Exception as e:
            print(f"Advertencia: no se pudieron guardar figuras: {e}", file=sys.stderr)

    print(f"OK — Informe en: {out_dir}")
    print(f"   accuracy={acc:.4f}  f1_macro={f1_macro:.4f}  kappa={kappa:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
