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
