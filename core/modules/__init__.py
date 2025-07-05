# core/modules/__init__.py
"""
Gestión de módulos de hardware
"""
from .module_manager import ModuleManager
from .module_types import ModuleType, ModuleState

__all__ = [
    'ModuleManager',
    'ModuleType', 
    'ModuleState'
]
