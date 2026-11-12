"""
TOON Parser - Token-Oriented Object Notation

Parser para el protocolo TOON, optimizado para comunicación con LLMs.
Reduce 30-60% de tokens comparado con JSON.
"""

from typing import Any, Dict, List, Union
import re


class TOONParser:
    """Parser para formato TOON."""
    
    @staticmethod
    def serialize(data: Any, indent: int = 0) -> str:
        """
        Convierte un diccionario Python a formato TOON.
        
        Args:
            data: Datos a serializar (dict, list, o primitivo)
            indent: Nivel de indentación actual
            
        Returns:
            String en formato TOON
        """
        if data is None:
            return "null"
        
        if isinstance(data, bool):
            return "true" if data else "false"
        
        if isinstance(data, (int, float)):
            return str(data)
        
        if isinstance(data, str):
            # Escapar comillas
            escaped = data.replace('"', '\\"')
            return f'"{escaped}"'
        
        if isinstance(data, list):
            return TOONParser._serialize_array(data, indent)
        
        if isinstance(data, dict):
            return TOONParser._serialize_object(data, indent)
        
        raise ValueError(f"Tipo no soportado: {type(data)}")
    
    @staticmethod
    def _serialize_object(obj: Dict, indent: int) -> str:
        """Serializa un objeto (diccionario)."""
        lines = []
        indent_str = "  " * indent
        
        for key, value in obj.items():
            if isinstance(value, dict):
                # Objeto anidado
                lines.append(f"{indent_str}{key}")
                lines.append(TOONParser._serialize_object(value, indent + 1))
            elif isinstance(value, list):
                # Array
                lines.append(f"{indent_str}{key}[{len(value)}]")
                for item in value:
                    if isinstance(item, (dict, list)):
                        lines.append(TOONParser.serialize(item, indent + 1))
                    else:
                        item_str = TOONParser.serialize(item, 0)
                        lines.append(f"{'  ' * (indent + 1)}{item_str}")
            else:
                # Valor primitivo
                value_str = TOONParser.serialize(value, 0)
                lines.append(f"{indent_str}{key} {value_str}")
        
        return "\n".join(lines)
    
    @staticmethod
    def _serialize_array(arr: List, indent: int) -> str:
        """Serializa un array."""
        lines = []
        indent_str = "  " * indent
        
        for item in arr:
            if isinstance(item, (dict, list)):
                lines.append(TOONParser.serialize(item, indent))
            else:
                item_str = TOONParser.serialize(item, 0)
                lines.append(f"{indent_str}{item_str}")
        
        return "\n".join(lines)
    
    @staticmethod
    def deserialize(toon_string: str) -> Dict[str, Any]:
        """
        Convierte una string TOON a diccionario Python.
        
        Args:
            toon_string: String en formato TOON
            
        Returns:
            Diccionario Python
        """
        lines = toon_string.strip().split('\n')
        result = {}
        stack = [result]
        current_key = None
        current_array = None
        array_size = 0
        
        for line in lines:
            if not line.strip():
                continue
            
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            
            # Ajustar stack al nivel actual
            while len(stack) > level + 1:
                stack.pop()
                if current_array is not None and len(current_array) >= array_size:
                    current_array = None
            
            line_content = line.strip()
            
            # Detectar array
            array_match = re.match(r'(\w+)\[(\d+)\]', line_content)
            if array_match:
                key = array_match.group(1)
                size = int(array_match.group(2))
                arr = []
                stack[-1][key] = arr
                stack.append(arr)
                current_array = arr
                array_size = size
                current_key = key
                continue
            
            # Detectar key-value
            if ' ' in line_content and not line_content.startswith('"'):
                parts = line_content.split(' ', 1)
                key = parts[0]
                value_str = parts[1] if len(parts) > 1 else ""
                value = TOONParser._parse_value(value_str)
                stack[-1][key] = value
                current_key = key
                continue
            
            # Detectar objeto anidado (solo key)
            if ' ' not in line_content and not line_content.startswith('"'):
                key = line_content
                obj = {}
                if isinstance(stack[-1], dict):
                    stack[-1][key] = obj
                    stack.append(obj)
                current_key = key
                continue
            
            # Valor de array
            if current_array is not None:
                value = TOONParser._parse_value(line_content)
                current_array.append(value)
        
        return result
    
    @staticmethod
    def _parse_value(value_str: str) -> Any:
        """Parsea un valor primitivo."""
        value_str = value_str.strip()
        
        if value_str == "null":
            return None
        
        if value_str == "true":
            return True
        
        if value_str == "false":
            return False
        
        # String
        if value_str.startswith('"') and value_str.endswith('"'):
            # Remover comillas y desescapar
            return value_str[1:-1].replace('\\"', '"')
        
        # Número
        try:
            if '.' in value_str:
                return float(value_str)
            return int(value_str)
        except ValueError:
            # Si no es número, retornar como string
            return value_str


# Funciones de conveniencia
def to_toon(data: Any) -> str:
    """Convierte datos Python a TOON."""
    return TOONParser.serialize(data)


def from_toon(toon_string: str) -> Dict[str, Any]:
    """Convierte TOON a datos Python."""
    return TOONParser.deserialize(toon_string)
