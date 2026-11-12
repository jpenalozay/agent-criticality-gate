"""
LLM Client v3.0 - Multi-Provider Support (FIXED)

Versión corregida que usa variables de entorno directamente.
"""

import os
import logging
from typing import Optional, List
from dataclasses import dataclass
import requests
import time

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Configuración de un LLM."""
    provider: str
    model: str
    api_key: str
    base_url: str
    temperature: float = 0.3
    max_tokens: int = 4000
    timeout: int = 60


class LLMClient:
    """Cliente unificado para LLM (DeepSeek)."""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Inicializa cliente LLM."""
        if config:
            self.config = config
        else:
            self.config = self._load_default_config()
        
        logger.info(
            f"LLM Client initialized: {self.config.provider}/{self.config.model}"
        )
    
    def _load_default_config(self) -> LLMConfig:
        """Carga configuración desde variables de entorno."""
        return LLMConfig(
            provider="deepseek",
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4000"))
        )
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None
    ) -> str:
        """Genera respuesta del LLM."""
        if self.config.provider == "deepseek":
            return self._generate_deepseek(
                prompt, system_prompt, temperature, max_tokens, stop
            )
        else:
            raise ValueError(f"Provider no soportado: {self.config.provider}")
    
    def _generate_deepseek(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: Optional[float],
        max_tokens: Optional[int],
        stop: Optional[List[str]]
    ) -> str:
        """Genera respuesta usando DeepSeek API."""
        
        # Preparar mensajes
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # Preparar request
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.config.model,
            "messages": messages,
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
        }
        
        if stop:
            data["stop"] = stop
        
        # Hacer request
        try:
            response = requests.post(
                url,
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            logger.debug(
                f"DeepSeek response: {len(content)} chars, "
                f"tokens: {result.get('usage', {}).get('total_tokens', 'N/A')}"
            )
            
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling DeepSeek API: {e}")
            raise
    
    def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> str:
        """Genera respuesta con reintentos automáticos."""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
        
        raise Exception(f"Failed after {max_retries} attempts: {last_error}")


def get_llm_client(
    agent_id: Optional[str] = None,
    model: Optional[str] = None
) -> LLMClient:
    """
    Factory function para obtener cliente LLM.
    
    Args:
        agent_id: ID del agente (para logging)
        model: Modelo a usar (deepseek-chat o deepseek-coder)
        
    Returns:
        Cliente LLM configurado
    """
    # Determinar modelo según agente
    if model is None:
        if agent_id == "coder":
            model = "deepseek-coder"
        else:
            model = "deepseek-chat"
    
    config = LLMConfig(
        provider="deepseek",
        model=model,
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.3,
        max_tokens=4000
    )
    
    return LLMClient(config)


def get_reviewer_llm_client(
    agent_id: str
) -> Optional[LLMClient]:
    """
    Obtiene cliente LLM para reviewer (peer review).
    
    Para simplificar, usa el mismo modelo pero con temperatura más baja.
    """
    config = LLMConfig(
        provider="deepseek",
        model="deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        temperature=0.1,  # Más conservador para review
        max_tokens=4000
    )
    
    return LLMClient(config)
