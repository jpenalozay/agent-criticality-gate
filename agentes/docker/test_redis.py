#!/usr/bin/env python3
"""Script de verificación de Redis"""
from agentes.core.redis_communication import RedisConnectionManager

manager = RedisConnectionManager.get_instance()
print(f'✅ Redis disponible: {manager.is_available()}')

if manager.is_available():
    client = manager.get_client()
    print(f'✅ Host conectado: {client.connection_pool.connection_kwargs.get("host")}')
    print(f'✅ Puerto: {client.connection_pool.connection_kwargs.get("port")}')
    print(f'✅ DB: {client.connection_pool.connection_kwargs.get("db")}')
    print(f'✅ Conexión verificada: {client.ping()}')
    print(f'✅ Info del servidor: Redis {client.info("server")["redis_version"]}')
else:
    print('⚠️ Redis no está disponible')

