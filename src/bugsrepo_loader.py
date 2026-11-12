"""
Carga y pipeline de limpieza BugsRepo / Bugzilla (Sprint 6 v2).

Fuentes (en orden):
1. CSV cache en data/external/bugsrepo/
2. HuggingFace AliArshad/Bug_Reports_with_Sentiments (si severity es taxonomía Bugzilla)
3. HuggingFace AliArshad/Bugzilla_Eclipse_Bug_Reports_Dataset (fallback con severities reales)
4. Zenodo BugsRepo local (opcional, ruta documentada)
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

RANDOM_SEED = 42

# Mapeo canónico Bugzilla → play/pausa/stop (Sprint 6 v2)
SEVERITY_MAP = {
    "blocker": "stop",
    "critical": "stop",
    "major": "pausa",
    "normal": "pausa",
    "minor": "play",
    "trivial": "play",
}

SEVERITY_EXCLUIR = {"enhancement", "n/a", "nan", "--", "unspecified", ""}
RESOLUTION_KEEP = {"FIXED", "VERIFIED", "RESOLVED"}

HF_PRIMARY = "AliArshad/Bug_Reports_with_Sentiments"
HF_FALLBACK = "AliArshad/Bugzilla_Eclipse_Bug_Reports_Dataset"

BUGSREPO_COLS_VARIANTS = [
    {
        "text": "Short Description",
        "severity": "Severity Label",
        "resolution": "Resolution Status",
        "product": "Project",
    },
    {
        "text": "short_desc",
        "severity": "severity",
        "resolution": "resolution",
        "product": "product",
    },
    {
        "text": "text",
        "severity": "severity",
        "resolution": "resolution",
        "product": "product",
    },
]


def _normalize_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    out = pd.DataFrame()
    for std, src in mapping.items():
        if src in df.columns:
            out[std] = df[src]
        elif std in df.columns:
            out[std] = df[std]
    return out


def _has_bugzilla_severity(series: pd.Series) -> bool:
    vals = set(series.astype(str).str.lower().str.strip().unique())
    return bool(vals & set(SEVERITY_MAP.keys()))


def load_from_huggingface(dataset_name: str) -> tuple[pd.DataFrame, str]:
    from datasets import load_dataset

    ds = load_dataset(dataset_name, split="train")
    df = ds.to_pandas()
    for mapping in BUGSREPO_COLS_VARIANTS:
        if mapping["text"] in df.columns and mapping["severity"] in df.columns:
            std = _normalize_columns(df, mapping)
            label = f"HuggingFace:{dataset_name}"
            return std, label
    raise ValueError(f"No se pudo mapear columnas en {dataset_name}: {list(df.columns)}")


def load_from_cache(cache_path: Path) -> tuple[pd.DataFrame, str]:
    df = pd.read_csv(cache_path)
    for mapping in BUGSREPO_COLS_VARIANTS:
        if mapping["text"] in df.columns or "text" in df.columns:
            if "text" not in df.columns:
                std = _normalize_columns(df, mapping)
            else:
                std = df.copy()
                for c in ("severity", "resolution", "product"):
                    if c not in std.columns:
                        std[c] = np.nan
            return std, f"cache:{cache_path.name}"


def load_bugsrepo_dataframe(
    agent-criticality-gate_root: Path,
    *,
    prefer_hf_primary: bool = True,
) -> tuple[pd.DataFrame, str]:
    """
    Devuelve DataFrame con columnas: text, severity, resolution, product (opcional).
    """
    cache_dir = agent-criticality-gate_root / "data" / "external" / "bugsrepo"
    cache_dir.mkdir(parents=True, exist_ok=True)
    for name in ("bugsrepo_mapped.csv", "bugzilla_eclipse_mapped.csv"):
        p = cache_dir / name
        if p.is_file():
            return load_from_cache(p)

    zenodo = cache_dir / "bugsrepo_zenodo.csv"
    if zenodo.is_file():
        return load_from_cache(zenodo)

    if prefer_hf_primary:
        try:
            df, label = load_from_huggingface(HF_PRIMARY)
            if _has_bugzilla_severity(df["severity"]):
                return df, label
        except Exception:
            pass

    df, label = load_from_huggingface(HF_FALLBACK)
    # Guardar cache para ejecución offline
    out = cache_dir / "bugzilla_eclipse_mapped.csv"
    df.to_csv(out, index=False)
    return df, label


def sha256_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text).lower().strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def registrar_funnel(funnel: list[dict[str, Any]], nombre: str, df_in: pd.DataFrame, df_out: pd.DataFrame, detalle: str = "") -> None:
    eliminados = len(df_in) - len(df_out)
    pct = len(df_out) / len(df_in) * 100 if len(df_in) > 0 else 0.0
    funnel.append(
        {
            "Fase": nombre,
            "Antes": len(df_in),
            "Después": len(df_out),
            "Eliminados": eliminados,
            "% Retenido": round(pct, 1),
            "Detalle": detalle,
        }
    )


def run_cleaning_pipeline(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]], int]:
    """Pipeline 5 fases (+ fase 0 campos vacíos)."""
    funnel: list[dict[str, Any]] = []
    n_raw = len(df_raw)

    df = df_raw.copy()
    df["severity"] = df["severity"].astype(str).str.lower().str.strip()
    if "resolution" in df.columns:
        df["resolution"] = df["resolution"].astype(str).str.upper().str.strip()
    else:
        df["resolution"] = "FIXED"

    # FASE 0
    df_f0 = df[
        df["severity"].notna()
        & df["severity"].ne("nan")
        & df["severity"].ne("")
        & df["text"].notna()
        & (df["text"].astype(str).str.len() > 3)
    ].copy()
    registrar_funnel(funnel, "FASE 0 — Eliminar registros sin severity/texto", df, df_f0, "Campos vacíos o nulos")
    df = df_f0

    # FASE 1
    if "resolution" in df.columns and df["resolution"].nunique() > 1:
        df_f1 = df[df["resolution"].isin(RESOLUTION_KEEP)].copy()
        detalle = "Solo resolution IN [FIXED, VERIFIED, RESOLVED]"
    else:
        df_f1 = df.copy()
        detalle = "Resolution no aplica o ya curado"
    registrar_funnel(funnel, "FASE 1 — Filtro Resolution=FIXED", df, df_f1, detalle)
    df = df_f1

    # FASE 2
    df_f2 = df[~df["severity"].isin(SEVERITY_EXCLUIR)].copy()
    registrar_funnel(funnel, "FASE 2 — Exclusión de Enhancement", df, df_f2, str(SEVERITY_EXCLUIR))
    df = df_f2

    # FASE 3
    df["text_hash"] = df["text"].apply(sha256_text)
    df_f3 = df.drop_duplicates(subset="text_hash").copy()
    registrar_funnel(funnel, "FASE 3 — Deduplicación SHA-256", df, df_f3, "Texto normalizado idéntico")
    df = df_f3

    # FASE 4
    df["thesis_class"] = df["severity"].map(SEVERITY_MAP)
    df_f4 = df[df["thesis_class"].notna()].copy()
    unmapped = df.loc[df["thesis_class"].isna(), "severity"].unique().tolist()
    registrar_funnel(
        funnel,
        "FASE 4 — Mapeo Bugzilla → Play/Pausa/Stop",
        df,
        df_f4,
        f"Sin mapeo: {unmapped}" if unmapped else "ninguna",
    )
    df = df_f4

    return df, funnel, n_raw


def sample_stratified(
    df: pd.DataFrame,
    n_per_class: int = 100,
    *,
    seed: int = RANDOM_SEED,
    classes: tuple[str, ...] = ("play", "pausa", "stop"),
) -> tuple[pd.DataFrame, int]:
    """Muestreo 100×3 (o menos si pool insuficiente)."""
    n_use = n_per_class
    parts = []
    for cls in classes:
        pool = df[df["thesis_class"] == cls]
        n_cls = len(pool)
        if n_cls < n_use:
            n_use = min(n_use, n_cls)
        if n_cls == 0:
            raise ValueError(f"Sin registros para clase {cls} tras pipeline")
        parts.append(pool.sample(n=min(n_use, n_cls), random_state=seed))
    out = pd.concat(parts).sample(frac=1, random_state=seed).reset_index(drop=True)
    return out, n_use
