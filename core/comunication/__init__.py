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

# ================================================

# core/__init__.py
"""
Núcleo del sistema WPC
Contiene la lógica de negocio principal
"""

__version__ = "2.0.0"
__author__ = "WPC Development Team"

# ================================================

# core/communication/__init__.py
"""
Módulo de comunicación serie RS485
Reemplaza los componentes de comunicación de VB6
"""
from .protocol import ProtocolHandler
from .serial_comm import SerialCommunication

__all__ = [
    'ProtocolHandler',
    'SerialCommunication'
]

# ================================================

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

# ================================================

# core/database/__init__.py
"""
Modelos y gestores de base de datos
"""
from .models import (
    Movement, Ticket, TicketHistory, Person, 
    Identification, Module, Base
)

__all__ = [
    'Movement',
    'Ticket',
    'TicketHistory', 
    'Person',
    'Identification',
    'Module',
    'Base'
]

# ================================================

# ui/__init__.py
"""
Interfaz gráfica de usuario
"""

__all__ = []

# ================================================

# camera_integration/__init__.py
"""
Integración con sistemas de cámaras
"""
from .hikvision_manager import HikvisionManager

__all__ = [
    'HikvisionManager'
]

# ================================================

# utils/__init__.py
"""
Utilidades y funciones auxiliares
"""
from .logger import setup_logging, log_system, log_communication
from .id_generator import IDGenerator

__all__ = [
    'setup_logging',
    'log_system', 
    'log_communication',
    'IDGenerator'
]