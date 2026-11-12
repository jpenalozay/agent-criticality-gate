"""Esquema de un caso gold de criticidad: solo `id`, `gold_mode` y `requirement` son obligatorios en consumo.

El resto de campos son opcionales en ingestión (pueden omitirse en JSONL reducido).
"""

from __future__ import annotations

from typing import Literal, NotRequired, Required, TypedDict

GoldMode = Literal["play", "pausa", "stop"]


class CriticidadCase(TypedDict, total=False):
    """Campos no marcados como Required son opcionales al cargar JSONL."""

    id: Required[str]
    gold_mode: Required[GoldMode]
    requirement: Required[str]
    rationale_gold: NotRequired[str]
    literature_axis: NotRequired[str]
    difficulty_hint: NotRequired[Literal["low", "medium", "high"]]
    tags: NotRequired[list[str]]
    template_index: NotRequired[int]
    schema_version: NotRequired[str]
