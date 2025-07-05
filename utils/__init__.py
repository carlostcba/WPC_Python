# utils/__init__.py - EXPORTACIONES ACTUALIZADAS
# ========================================
"""
Módulo de utilidades actualizado
"""
from .logger import setup_logging, log_system, log_error, log_movement, log_communication, log_camera
from .id_generator import IDGenerator
from .helpers import format_identification, validate_datetime_range, get_system_info

__all__ = [
    'setup_logging',
    'log_system', 
    'log_error',
    'log_movement',
    'log_communication',
    'log_camera',  # ← NUEVA FUNCIÓN
    'IDGenerator',
    'format_identification',
    'validate_datetime_range', 
    'get_system_info'
]