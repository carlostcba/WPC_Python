# config/__init__.py
"""
Módulo de configuración del sistema WPC
"""
from .settings import settings, WPCSettings
from .database import db_manager, init_database, close_database

__all__ = [
    'settings',
    'WPCSettings', 
    'db_manager',
    'init_database',
    'close_database'
]
