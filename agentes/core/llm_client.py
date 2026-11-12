"""
DeepSeek LLM Client

Cliente para interactuar con la API de DeepSeek.
Maneja autenticación, rate limits, retries y streaming.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Cliente para DeepSeek LLM."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
        timeout: int = 30
    ):
        """
        Inicializa el cliente DeepSeek.
        
        Args:
            api_key: API key de DeepSeek (o desde .env)
            base_url: URL base de la API (o desde .env)
            model: Modelo a usar (o desde .env)
            temperature: Temperatura para generación
            max_tokens: Máximo de tokens a generar
            timeout: Timeout en segundos
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "claude-sonnet-4-20250514")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY no configurada")
        
        # Inicializar cliente OpenAI compatible
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        logger.info(f"DeepSeek client initialized: model={self.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Genera texto usando DeepSeek.
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt del sistema (opcional)
            temperature: Override de temperatura
            max_tokens: Override de max tokens
            **kwargs: Argumentos adicionales para la API
            
        Returns:
            Texto generado
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs
            )
            
            result = response.choices[0].message.content
            logger.debug(f"Generated {len(result)} characters")
            return result
            
        except Exception as e:
            logger.error(f"Error generating with DeepSeek: {e}")
            raise
    
    def generate_with_retry(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_retries: int = 3,
        backoff_multiplier: float = 2.0,
        **kwargs
    ) -> str:
        """
        Genera texto con retry automático.
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt del sistema
            max_retries: Número máximo de reintentos
            backoff_multiplier: Multiplicador para backoff exponencial
            **kwargs: Argumentos adicionales
            
        Returns:
            Texto generado
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, system_prompt, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    wait_time = backoff_multiplier ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} attempts failed")
        
        raise last_error
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Chat multi-turn con DeepSeek.
        
        Args:
            messages: Lista de mensajes [{"role": "user/assistant", "content": "..."}]
            temperature: Override de temperatura
            max_tokens: Override de max tokens
            **kwargs: Argumentos adicionales
            
        Returns:
            Respuesta del asistente
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in chat: {e}")
            raise
    
    def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ):
        """
        Genera texto con streaming.
        
        Args:
            prompt: Prompt del usuario
            system_prompt: Prompt del sistema
            temperature: Override de temperatura
            max_tokens: Override de max tokens
            **kwargs: Argumentos adicionales
            
        Yields:
            Chunks de texto generado
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
                **kwargs
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            logger.error(f"Error in streaming: {e}")
            raise


# Singleton global
_global_client: Optional[DeepSeekClient] = None


def get_llm_client() -> DeepSeekClient:
    """Obtiene el cliente LLM global (singleton)."""
    global _global_client
    if _global_client is None:
        _global_client = DeepSeekClient()
    return _global_client


def set_llm_client(client: DeepSeekClient):
    """Establece el cliente LLM global."""
    global _global_client
    _global_client = client
