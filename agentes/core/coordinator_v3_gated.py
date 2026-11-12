"""
Coordinator v3 con gate temprano de criticidad (EarlyGate).

Extiende el flujo estándar añadiendo una clasificación play/pausa/stop *antes*
del Arquitecto, usando LLM + fallback léxico cuando hay duda.

El Sentinel sobre blueprint se ejecuta igual que en v3; esta señal es complementaria.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.coordinator_v3 import CoordinatorV3
from core.early_gate import EarlyGate

logger = logging.getLogger(__name__)


class CoordinatorV3Gated(CoordinatorV3):
    """
    Igual que CoordinatorV3, pero encapsula el resultado de `EarlyGate` en la respuesta.

    Args adicionales respecto al padre:
        enable_early_gate: si False, comportamiento idéntico a CoordinatorV3.
    """

    def __init__(
        self,
        enable_peer_review: bool = True,
        enable_executable_feedback: bool = True,
        *,
        enable_early_gate: bool = True,
    ) -> None:
        super().__init__(
            enable_peer_review=enable_peer_review,
            enable_executable_feedback=enable_executable_feedback,
        )
        self.enable_early_gate = enable_early_gate
        self._early_gate = EarlyGate() if enable_early_gate else None
        logger.info("CoordinatorV3Gated initialized (early_gate=%s)", enable_early_gate)

    def process(self, requirement: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        early_result: Optional[Dict[str, Any]] = None
        if self._early_gate is not None:
            logger.info("[0/8] Running EarlyGate...")
            early_result = self._early_gate.decide(requirement, context)

        base = super().process(requirement, context)

        if early_result is not None and isinstance(base, dict):
            base.setdefault("early_gate", early_result)
            agents = base.get("agents")
            if isinstance(agents, dict):
                agents["early_gate"] = early_result

        return base
