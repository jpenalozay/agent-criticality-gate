"""
Ingesta reproducible (v0) de benchmarks de evaluación para el framework multi-agente.
Descarga HumanEval y MBPP desde Hugging Face, exporta a JSONL y genera manifiesto con integridad.
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Raíz del repositorio (Tesis/): un nivel arriba de src/
REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "data" / "raw"
LOGS_DIR = REPO_ROOT / "logs"
MANIFEST_PATH = RAW_DIR / "manifest_v0.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _file_stats(path: Path) -> dict:
    size = path.stat().st_size
    return {
        "path": str(path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "size_bytes": size,
        "sha256": _sha256_file(path),
    }


def _export_split(ds, out_path: Path) -> int:
    """Escribe un split de HuggingFace datasets como JSONL (una fila = un registro)."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for row in ds:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def _configure_logging() -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logfile = LOGS_DIR / "ingesta.log"
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(logfile, encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(sh)
    root.addHandler(fh)


def main() -> int:
    _configure_logging()
    started = datetime.now(timezone.utc)
    logging.info("Inicio de ingesta v0. Fecha/hora (UTC): %s", started.isoformat())

    try:
        from datasets import load_dataset
    except ImportError as e:
        logging.error("Falta la dependencia 'datasets'. Instale: pip install -r requirements.txt")
        raise SystemExit(1) from e

    RAW_DIR.mkdir(parents=True, exist_ok=True)

    artifacts: list[dict] = []
    total_rows: dict[str, int] = {}

    # HumanEval (164 problemas de programación en Python, benchmark estándar)
    logging.info("Cargando openai_humaneval (split test)...")
    he = load_dataset("openai_humaneval", split="test")
    he_path = RAW_DIR / "humaneval" / "openai_humaneval_test.jsonl"
    total_rows["humaneval"] = _export_split(he, he_path)
    artifacts.append(_file_stats(he_path))
    logging.info("HumanEval: %d filas → %s", total_rows["humaneval"], he_path)

    # MBPP (Mostly Basic Python Problems; split test para evaluación reutilizable)
    logging.info("Cargando mbpp (split test)...")
    mbpp = load_dataset("mbpp")
    if "test" in mbpp:
        m_split = mbpp["test"]
    else:
        name = list(mbpp.keys())[0]
        m_split = mbpp[name]
        logging.info("Usando split '%s' de MBPP (no hay 'test')", name)

    mbpp_path = RAW_DIR / "mbpp" / "mbpp.jsonl"
    total_rows["mbpp"] = _export_split(m_split, mbpp_path)
    artifacts.append(_file_stats(mbpp_path))
    logging.info("MBPP: %d filas → %s", total_rows["mbpp"], mbpp_path)

    finished = datetime.now(timezone.utc)
    manifest = {
        "ingestion_version": "0",
        "execution_started_utc": started.isoformat(),
        "execution_finished_utc": finished.isoformat(),
        "huggingface_datasets": {
            "humaneval": "openai_humaneval (split=test)",
            "mbpp": "mbpp (split=test)",
        },
        "row_counts": total_rows,
        "artifacts": artifacts,
    }
    with MANIFEST_PATH.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    logging.info("Manifiesto con SHA-256 y tamaños: %s", MANIFEST_PATH)
    logging.info("Ingesta finalizada correctamente.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
