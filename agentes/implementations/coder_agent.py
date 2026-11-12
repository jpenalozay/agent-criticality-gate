"""
Agente Coder

Genera código basado en blueprints.
Soporta múltiples lenguajes y patrones arquitectónicos.
"""

import logging
from typing import Dict, Any, List, Optional
from agentes.core.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class CoderAgent:
    """Agente que genera código."""
    
    def __init__(self):
        """Inicializa el agente coder."""
        self.llm = get_llm_client()
        self.agent_id = "coder"
        
        # Templates de código por patrón
        self.patterns = {
            "repository": self._get_repository_pattern(),
            "service_layer": self._get_service_pattern(),
            "mvc": self._get_mvc_pattern()
        }
    
    def process(
        self,
        blueprint: Dict[str, Any],
        language: str = "python"
    ) -> Dict[str, Any]:
        """
        Genera código basado en un blueprint.
        
        Args:
            blueprint: Blueprint del sistema
            language: Lenguaje de programación
            
        Returns:
            Dict con archivos generados
        """
        logger.info(f"Coder generating code for: {blueprint.get('name', 'unnamed')}")
        
        artifacts = {
            "files": {},
            "structure": [],
            "language": language,
            "blueprint_name": blueprint.get("name", "unnamed")
        }
        
        # Generar código por componente
        components = blueprint.get("components", {})
        
        for comp_name, comp_data in components.items():
            comp_type = comp_data.get("type", "service")
            
            # Generar archivos según tipo de componente
            if comp_type in ["backend", "service", "api"]:
                files = self._generate_service_code(comp_name, comp_data, language)
                artifacts["files"].update(files)
            
            elif comp_type in ["frontend", "ui"]:
                files = self._generate_frontend_code(comp_name, comp_data, language)
                artifacts["files"].update(files)
            
            elif comp_type == "database":
                files = self._generate_database_code(comp_name, comp_data, language)
                artifacts["files"].update(files)
            
            else:
                # Generar código genérico
                files = self._generate_generic_code(comp_name, comp_data, language)
                artifacts["files"].update(files)
        
        # Generar estructura de directorios
        artifacts["structure"] = self._generate_directory_structure(artifacts["files"])
        
        logger.info(f"Generated {len(artifacts['files'])} files")
        return artifacts
    
    def _generate_service_code(
        self,
        name: str,
        component: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Genera código para un servicio."""
        files = {}
        
        if language == "python":
            # Service
            service_code = self._generate_python_service(name, component)
            files[f"src/services/{name}_service.py"] = service_code
            
            # Repository
            repo_code = self._generate_python_repository(name, component)
            files[f"src/repositories/{name}_repository.py"] = repo_code
            
            # DTOs
            dto_code = self._generate_python_dto(name, component)
            files[f"src/dtos/{name}_dto.py"] = dto_code
            
            # Tests
            test_code = self._generate_python_tests(name, component)
            files[f"tests/test_{name}.py"] = test_code
        
        return files
    
    def _generate_python_service(self, name: str, component: Dict[str, Any]) -> str:
        """Genera código de servicio en Python."""
        description = component.get("description", f"{name} service")
        
        system_prompt = """Eres un desarrollador Python experto. Genera código limpio, bien documentado y siguiendo mejores prácticas."""
        
        user_prompt = f"""Genera un servicio Python para: {description}

Requisitos:
- Usar type hints
- Incluir docstrings
- Seguir PEP 8
- Manejo de errores apropiado
- Logging cuando sea necesario
- Patrón Service Layer

Nombre del servicio: {name.title()}Service

Genera SOLO el código Python, sin explicaciones adicionales."""
        
        try:
            code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2000
            )
            
            # Limpiar código (remover markdown si existe)
            code = self._clean_code(code)
            return code
            
        except Exception as e:
            logger.error(f"Error generating service code: {e}")
            # Fallback a template básico
            return self._get_basic_service_template(name, description)
    
    def _generate_python_repository(self, name: str, component: Dict[str, Any]) -> str:
        """Genera código de repository en Python."""
        system_prompt = """Eres un desarrollador Python experto. Genera código limpio siguiendo el patrón Repository."""
        
        user_prompt = f"""Genera un Repository Python para: {name}

Requisitos:
- Patrón Repository
- Type hints
- Docstrings
- Métodos CRUD básicos (create, read, update, delete)
- Manejo de excepciones

Nombre: {name.title()}Repository

Genera SOLO el código Python."""
        
        try:
            code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2000
            )
            return self._clean_code(code)
        except Exception as e:
            logger.error(f"Error generating repository: {e}")
            return self._get_basic_repository_template(name)
    
    def _generate_python_dto(self, name: str, component: Dict[str, Any]) -> str:
        """Genera DTOs en Python."""
        system_prompt = """Eres un desarrollador Python experto. Genera DTOs usando Pydantic."""
        
        user_prompt = f"""Genera DTOs (Data Transfer Objects) para: {name}

Requisitos:
- Usar Pydantic BaseModel
- Type hints completos
- Validaciones apropiadas
- Docstrings

Genera al menos 2 DTOs:
- {name.title()}Create (para crear)
- {name.title()}Response (para respuestas)

Genera SOLO el código Python."""
        
        try:
            code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1500
            )
            return self._clean_code(code)
        except Exception as e:
            logger.error(f"Error generating DTOs: {e}")
            return self._get_basic_dto_template(name)
    
    def _generate_python_tests(self, name: str, component: Dict[str, Any]) -> str:
        """Genera tests en Python."""
        system_prompt = """Eres un desarrollador Python experto en testing. Genera tests comprehensivos usando pytest."""
        
        user_prompt = f"""Genera tests unitarios para el servicio: {name}

Requisitos:
- Usar pytest
- Fixtures apropiados
- Mocks cuando sea necesario
- Patrón AAA (Arrange, Act, Assert)
- Casos normales y edge cases
- Nombres descriptivos

Genera SOLO el código Python de tests."""
        
        try:
            code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=2000
            )
            return self._clean_code(code)
        except Exception as e:
            logger.error(f"Error generating tests: {e}")
            return self._get_basic_test_template(name)
    
    def _generate_frontend_code(
        self,
        name: str,
        component: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Genera código frontend."""
        # Por ahora, retornar placeholder
        return {
            f"src/components/{name}.html": f"<!-- {name} component -->\n<div>{name}</div>"
        }
    
    def _generate_database_code(
        self,
        name: str,
        component: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Genera código de base de datos."""
        files = {}
        
        if language == "python":
            # Modelo SQLAlchemy
            model_code = self._generate_sqlalchemy_model(name, component)
            files[f"src/models/{name}_model.py"] = model_code
        
        return files
    
    def _generate_sqlalchemy_model(self, name: str, component: Dict[str, Any]) -> str:
        """Genera modelo SQLAlchemy."""
        system_prompt = """Eres un desarrollador Python experto en SQLAlchemy."""
        
        user_prompt = f"""Genera un modelo SQLAlchemy para: {name}

Requisitos:
- Usar SQLAlchemy ORM
- Type hints
- Docstrings
- Campos apropiados con tipos correctos
- Relaciones si son necesarias
- Timestamps (created_at, updated_at)

Genera SOLO el código Python."""
        
        try:
            code = self.llm.generate_with_retry(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2,
                max_tokens=1500
            )
            return self._clean_code(code)
        except Exception as e:
            logger.error(f"Error generating model: {e}")
            return self._get_basic_model_template(name)
    
    def _generate_generic_code(
        self,
        name: str,
        component: Dict[str, Any],
        language: str
    ) -> Dict[str, str]:
        """Genera código genérico."""
        description = component.get("description", f"{name} component")
        
        if language == "python":
            code = f'''"""
{name.title()} Component

{description}
"""

class {name.title()}:
    """Main class for {name}."""
    
    def __init__(self):
        """Initialize {name}."""
        pass
    
    def process(self):
        """Main processing method."""
        pass
'''
            return {f"src/{name}.py": code}
        
        return {}
    
    def _generate_directory_structure(self, files: Dict[str, str]) -> List[str]:
        """Genera estructura de directorios."""
        dirs = set()
        for filepath in files.keys():
            parts = filepath.split("/")
            for i in range(1, len(parts)):
                dirs.add("/".join(parts[:i]))
        return sorted(dirs)
    
    def _clean_code(self, code: str) -> str:
        """Limpia código generado (remueve markdown, etc)."""
        code = code.strip()
        
        # Remover bloques de código markdown
        if code.startswith("```python"):
            code = code[9:]
        elif code.startswith("```"):
            code = code[3:]
        
        if code.endswith("```"):
            code = code[:-3]
        
        return code.strip()
    
    # Templates básicos de fallback
    
    def _get_basic_service_template(self, name: str, description: str) -> str:
        return f'''"""
{name.title()} Service

{description}
"""

import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class {name.title()}Service:
    """Service for {name}."""
    
    def __init__(self):
        """Initialize service."""
        self.logger = logger
    
    def process(self, data: dict) -> dict:
        """
        Process data.
        
        Args:
            data: Input data
            
        Returns:
            Processed result
        """
        self.logger.info(f"Processing {{name}}")
        # TODO: Implement logic
        return {{"status": "success"}}
'''
    
    def _get_basic_repository_template(self, name: str) -> str:
        return f'''"""
{name.title()} Repository
"""

from typing import Optional, List


class {name.title()}Repository:
    """Repository for {name}."""
    
    def __init__(self, db):
        """Initialize repository."""
        self.db = db
    
    def create(self, data: dict) -> dict:
        """Create new record."""
        # TODO: Implement
        pass
    
    def get(self, id: str) -> Optional[dict]:
        """Get record by ID."""
        # TODO: Implement
        pass
    
    def update(self, id: str, data: dict) -> dict:
        """Update record."""
        # TODO: Implement
        pass
    
    def delete(self, id: str) -> bool:
        """Delete record."""
        # TODO: Implement
        pass
'''
    
    def _get_basic_dto_template(self, name: str) -> str:
        return f'''"""
{name.title()} DTOs
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class {name.title()}Create(BaseModel):
    """DTO for creating {name}."""
    name: str
    description: Optional[str] = None


class {name.title()}Response(BaseModel):
    """DTO for {name} response."""
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
'''
    
    def _get_basic_test_template(self, name: str) -> str:
        return f'''"""
Tests for {name.title()}Service
"""

import pytest
from src.services.{name}_service import {name.title()}Service


class Test{name.title()}Service:
    """Test suite for {name.title()}Service."""
    
    @pytest.fixture
    def service(self):
        """Create service instance."""
        return {name.title()}Service()
    
    def test_process(self, service):
        """Test process method."""
        # Arrange
        data = {{"test": "data"}}
        
        # Act
        result = service.process(data)
        
        # Assert
        assert result is not None
        assert result["status"] == "success"
'''
    
    def _get_basic_model_template(self, name: str) -> str:
        return f'''"""
{name.title()} Model
"""

from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class {name.title()}(Base):
    """SQLAlchemy model for {name}."""
    
    __tablename__ = "{name.lower()}s"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
'''
    
    def _get_repository_pattern(self) -> str:
        return "Repository pattern template"
    
    def _get_service_pattern(self) -> str:
        return "Service layer pattern template"
    
    def _get_mvc_pattern(self) -> str:
        return "MVC pattern template"
