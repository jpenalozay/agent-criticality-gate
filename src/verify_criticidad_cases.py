"""Verifica coherencia del JSONL de casos de criticidad (gramática, claves, etiquetas, duplicados).

Uso: python src/verify_criticidad_cases.py [ruta/casos_gold_criticidad_v2.jsonl]
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT = REPO_ROOT / "data" / "criticidad_cases" / "casos_gold_criticidad_v2.jsonl"

REQUIRED_KEYS = frozenset({"id", "gold_mode", "requirement"})
OPTIONAL_KEYS = frozenset({
    "rationale_gold", "literature_axis", "difficulty_hint",
    "tags", "template_index", "schema_version",
})
VALID_MODES = frozenset({"play", "pausa", "stop"})

# Patrones de redacción incorrecta (control de calidad del texto; regresión).
BAD_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bpara\s+(renombra|convierte|genera|cuenta|implementa|indenta|simula|valida|grafica|traduce)\b", re.I),
     "uso incorrecto de «para» + forma verbal (debe ser «que …» o infinitivo)"),
    (re.compile(r"\bDockerfile\s+de\s+equipo\s+para\s+(instala|expone|ejecuta|registra|separa|procesa|replica|activa|despliega|verifica)\b", re.I),
     "Dockerfile + «para» + verbo en forma incorrecta"),
    (re.compile(r"en\s+contexto\s+(migra|reconfigura|altera|expone|procesa|bloquea|puede|afecta|requiere|implica)\b", re.I),
     "plantilla ML rota: «en contexto» + verbo"),
]


def load_rows(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for ln, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Línea {ln}: JSON inválido: {e}") from e
    return rows


def _row_errors(i: int, row: dict, seen_ids: set[str]) -> tuple[list[str], str | None]:
    loc = f"fila {i + 1}"
    out: list[str] = []
    bad_keys = set(row) - REQUIRED_KEYS - OPTIONAL_KEYS
    if bad_keys:
        out.append(f"{loc}: claves desconocidas {sorted(bad_keys)}")
    missing = REQUIRED_KEYS - set(row)
    if missing:
        return out + [f"{loc}: faltan claves obligatorias {sorted(missing)}"], None

    rid = row["id"]
    if rid in seen_ids:
        out.append(f"{loc}: id duplicado {rid!r}")
    seen_ids.add(rid)
    mode = row["gold_mode"]
    if mode not in VALID_MODES:
        out.append(f"{loc}: gold_mode inválido {mode!r}")

    req = row["requirement"]
    req_ok: str | None = None
    if not isinstance(req, str) or not req.strip():
        out.append(f"{loc}: requirement vacío o no string")
    else:
        req_ok = req
        for rx, msg in BAD_PATTERNS:
            if rx.search(req):
                out.append(f"{loc} ({rid}): {msg}: …{req[:80]}…")

    parts = str(row["id"]).split("-")
    prefix = parts[1] if len(parts) >= 2 else ""
    expected_prefix = {"play": "PLAY", "pausa": "PAUSE", "stop": "STOP"}.get(str(mode), "")
    if expected_prefix and prefix != expected_prefix:
        out.append(f"{loc}: prefijo de id {prefix!r} no coincide con gold_mode {mode!r}")

    if "difficulty_hint" in row:
        dh = row["difficulty_hint"]
        exp = {"play": "low", "pausa": "medium", "stop": "high"}.get(str(mode))
        if exp and dh != exp:
            out.append(f"{loc}: difficulty_hint {dh!r} no coincide con lo esperado para {mode} ({exp!r})")

    if "tags" in row and row["tags"] is not None and not isinstance(row["tags"], list):
        out.append(f"{loc}: tags debe ser lista o ausente")

    return out, req_ok


def verify(rows: list[dict], *, path: Path) -> list[str]:
    errors: list[str] = []
    if len(rows) != 300:
        errors.append(f"Se esperaban 300 filas, hay {len(rows)}.")

    seen_ids: set[str] = set()
    reqs: list[str] = []

    for i, row in enumerate(rows):
        row_errs, req_ok = _row_errors(i, row, seen_ids)
        errors.extend(row_errs)
        if req_ok is not None:
            reqs.append(req_ok)

    if len(reqs) != len(set(reqs)):
        errors.append(f"requirements duplicados: {len(reqs) - len(set(reqs))} repeticiones.")

    vc = Counter(r["gold_mode"] for r in rows)
    for m in sorted(VALID_MODES):
        if vc.get(m, 0) != 100:
            errors.append(f"gold_mode {m!r}: se esperaban 100 casos, hay {vc.get(m, 0)}.")

    if not errors:
        errors.append(f"OK: {path.name} — 300 casos, ids únicos, requirements únicos, modos balanceados.")
    return errors


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    if not path.is_file():
        print(f"No existe {path}", file=sys.stderr)
        sys.exit(2)
    rows = load_rows(path)
    msgs = verify(rows, path=path)
    for m in msgs:
        print(m)
    sys.exit(0 if len(msgs) == 1 and msgs[0].startswith("OK:") else 1)


if __name__ == "__main__":
    main()
