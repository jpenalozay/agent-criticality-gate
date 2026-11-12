"""
Agente Arquitecto

Convierte requerimientos en lenguaje natural a blueprints TOON.
Identifica componentes, tecnologías, dependencias y criticidad.
"""

import logging
from typing import Dict, Any, Optional
from agentes.core.llm_client import get_llm_client
from agentes.core.toon_parser import to_toon

logger = logging.getLogger(__name__)


class ArquitectoAgent:
    """Agente que diseña la arquitectura del software."""
    
    def __init__(self):
        """Inicializa el agente arquitecto."""
        self.llm = get_llm_client()
        self.agent_id = "arquitecto"
    
    def process(self, requirement: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Procesa un requerimiento y genera un blueprint.
        
        Args:
            requirement: Requerimiento en lenguaje natural
            context: Contexto adicional (opcional)
            
        Returns:
            Blueprint en formato dict
        """
        logger.info(f"Arquitecto processing requirement: {requirement[:100]}...")
        
        # Construir prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(requirement, context)
        
        # Generar blueprint con LLM
        try:
            response = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=4000
            )
            
            # Parsear respuesta a blueprint estructurado
            blueprint = self._parse_response(response, requirement)
            
            logger.info(f"Blueprint generated: {blueprint.get('name', 'unnamed')}")
            return blueprint
            
        except Exception as e:
            logger.error(f"Error generating blueprint: {e}")
            raise
    
    def _build_system_prompt(self) -> str:
        """Construye el system prompt para el LLM."""
        return """Eres un arquitecto de software senior experto en diseño de sistemas.

Tu tarea es analizar requerimientos y generar blueprints técnicos detallados.

Debes identificar:
1. Componentes principales del sistema
2. Tecnologías apropiadas para cada componente
3. Relaciones y dependencias entre componentes
4. Nivel de criticidad de cada componente
5. Tipos de datos que se manejarán
6. Consideraciones de seguridad

Responde SOLO con un objeto JSON válido con esta estructura:
{
  "name": "nombre_del_sistema",
  "type": "tipo_de_sistema (api, web_app, service, etc)",
  "description": "descripción breve",
  "components": {
    "component_name": {
      "type": "tipo (frontend, backend, database, etc)",
      "tech": "tecnología específica",
      "criticality": "HIGH|MEDIUM|LOW",
      "description": "descripción del componente"
    }
  },
  "dependencies": [
    {"from": "component_a", "to": "component_b", "type": "uses|depends_on"}
  ],
  "data": ["tipo_de_dato_1", "tipo_de_dato_2"],
  "security": ["consideración_1", "consideración_2"]
}

NO incluyas explicaciones adicionales, solo el JSON."""
    
    def _build_user_prompt(self, requirement: str, context: Optional[Dict[str, Any]]) -> str:
        """Construye el user prompt."""
        prompt = f"Requerimiento:\n{requirement}\n"
        
        if context:
            prompt += f"\nContexto adicional:\n{context}\n"
        
        prompt += "\nGenera el blueprint en formato JSON:"
        
        return prompt
    
    def _parse_response(self, response: str, requirement: str) -> Dict[str, Any]:
        """
        Parsea la respuesta del LLM a un blueprint estructurado.
        
        Args:
            response: Respuesta del LLM
            requirement: Requerimiento original
            
        Returns:
            Blueprint estructurado
        """
        import json
        
        try:
            # Intentar parsear como JSON
            # Limpiar respuesta (remover markdown si existe)
            clean_response = response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.startswith("```"):
                clean_response = clean_response[3:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            blueprint = json.loads(clean_response)
            
            # Validar estructura básica
            if "name" not in blueprint:
                blueprint["name"] = "generated_system"
            if "type" not in blueprint:
                blueprint["type"] = "service"
            if "components" not in blueprint:
                blueprint["components"] = {}
            
            return blueprint
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM response as JSON: {e}")
            
            # Fallback: crear blueprint básico
            return {
                "name": "generated_system",
                "type": "service",
                "description": requirement[:200],
                "components": {
                    "main_component": {
                        "type": "service",
                        "tech": "python",
                        "criticality": "MEDIUM",
                        "description": "Main component"
                    }
                },
                "dependencies": [],
                "data": ["internal"],
                "security": ["basic_validation"]
            }
    
    def to_toon(self, blueprint: Dict[str, Any]) -> str:
        """
        Convierte un blueprint a formato TOON.
        
        Args:
            blueprint: Blueprint en formato dict
            
        Returns:
            Blueprint en formato TOON
        """
        return to_toon(blueprint)
