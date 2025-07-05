# core/modules/module_types.py
"""
Definición de tipos y estados de módulos
Equivale a las constantes y enums de VB6
"""
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Dict, List, Optional

class ModuleType(IntEnum):
    """
    Tipos de módulos de hardware
    Equivalente a las constantes de VB6
    """
    UNKNOWN = 0
    BARRIER = 1          # Barrera vehicular
    TURNSTILE = 2        # Molinete peatonal
    DOOR = 3             # Puerta de acceso
    CARD_READER = 4      # Lector de tarjetas únicamente
    TICKET_DISPENSER = 5 # Dispensador de tickets
    CASH_PARK = 6        # Módulo Cash Park
    VME100 = 7           # Módulo VME100
    ST1660 = 8           # Módulo ST1660

class ModuleState(IntEnum):
    """
    Estados operativos de módulos
    """
    OFFLINE = 0          # Sin comunicación
    ONLINE = 1           # Comunicación OK
    ERROR = 2            # Error de hardware
    MAINTENANCE = 3      # En mantenimiento
    INITIALIZING = 4     # Inicializando

class BarrierState(IntEnum):
    """
    Estados específicos de barreras
    """
    CLOSED = 0           # Barrera baja
    OPEN = 1             # Barrera alta
    MOVING_UP = 2        # Subiendo
    MOVING_DOWN = 3      # Bajando
    BLOCKED = 4          # Bloqueada por obstáculo

class SensorState(IntEnum):
    """
    Estados de sensores DDMM (Detección de Metales)
    """
    FREE = 0             # Libre
    OCCUPIED = 1         # Ocupado
    UNKNOWN = 2          # Estado desconocido

class Direction(IntEnum):
    """
    Direcciones de movimiento
    """
    ENTRY = 1            # Entrada
    EXIT = 2             # Salida
    BIDIRECTIONAL = 3    # Bidireccional

@dataclass
class ModuleConfiguration:
    """
    Configuración de un módulo
    Equivalente a los elementos del vector Addresses() en VB6
    """
    module_id: int
    address: int                    # Dirección RS485
    module_type: ModuleType
    name: str
    description: str = ""
    group_id: Optional[int] = None
    polling_order: int = 0
    pulse_duration: int = 0         # Duración pulso en ms
    requires_ticket_validation: bool = False
    entry_module_id: Optional[int] = None
    exit_module_id: Optional[int] = None
    
    # Estados operativos
    state: ModuleState = ModuleState.OFFLINE
    barrier_state: Optional[BarrierState] = None
    sensor_ddmm: Optional[SensorState] = None
    
    # Configuración de comunicación
    retry_count: int = 0
    max_retries: int = 3
    last_communication: Optional[float] = None
    
    # Comandos pendientes
    pending_commands: List[str] = None
    
    def __post_init__(self):
        if self.pending_commands is None:
            self.pending_commands = []

class CommandType(Enum):
    """
    Tipos de comandos para módulos
    Equivalente a los comandos del protocolo VB6
    """
    READ_STATUS = "ReadStatus"       # Leer estado
    SET_TIME = "SetTime"             # Sincronizar hora
    OPEN_BARRIER = "ContSec"         # Abrir barrera/continuar secuencia
    CLOSE_BARRIER = "StopSec"        # Cerrar barrera/detener secuencia
    PULSE_OUTPUT = "Pulse"           # Pulso de salida
    RESET_MODULE = "Reset"           # Reiniciar módulo
    GET_VERSION = "Version"          # Obtener versión firmware

# Constantes del protocolo ASCII
class ProtocolConstants:
    """
    Constantes del protocolo de comunicación
    Equivalente a las constantes de Protocolo.cls en VB6
    """
    STX = 0x02                       # Start of Text
    ETX = 0x03                       # End of Text
    ACK = 0x06                       # Acknowledge
    NAK = 0x15                       # Negative Acknowledge
    
    # Timeouts en milisegundos
    RESPONSE_TIMEOUT = 2000
    COMMAND_DELAY = 100
    
    # Códigos de error
    ERROR_TIMEOUT = -1
    ERROR_CHECKSUM = -2
    ERROR_NAK = -3
    ERROR_INVALID_RESPONSE = -4

# Mapeo de tipos de módulo a sus capacidades
MODULE_CAPABILITIES: Dict[ModuleType, Dict[str, bool]] = {
    ModuleType.BARRIER: {
        'has_barrier': True,
        'has_sensors': True,
        'supports_tickets': True,
        'bidirectional': False
    },
    ModuleType.TURNSTILE: {
        'has_barrier': False,
        'has_sensors': True,
        'supports_tickets': False,
        'bidirectional': True
    },
    ModuleType.DOOR: {
        'has_barrier': False,
        'has_sensors': True,
        'supports_tickets': False,
        'bidirectional': True
    },
    ModuleType.CARD_READER: {
        'has_barrier': False,
        'has_sensors': False,
        'supports_tickets': False,
        'bidirectional': False
    },
    ModuleType.TICKET_DISPENSER: {
        'has_barrier': False,
        'has_sensors': False,
        'supports_tickets': True,
        'bidirectional': False
    }
}

def get_module_capabilities(module_type: ModuleType) -> Dict[str, bool]:
    """
    Obtener capacidades de un tipo de módulo
    
    Args:
        module_type: Tipo de módulo
        
    Returns:
        dict: Diccionario con capacidades del módulo
    """
    return MODULE_CAPABILITIES.get(module_type, {
        'has_barrier': False,
        'has_sensors': False,
        'supports_tickets': False,
        'bidirectional': False
    })

def validate_module_configuration(config: ModuleConfiguration) -> List[str]:
    """
    Validar configuración de módulo
    
    Args:
        config: Configuración a validar
        
    Returns:
        list: Lista de errores encontrados (vacía si es válida)
    """
    errors = []
    
    # Validaciones básicas
    if config.module_id <= 0:
        errors.append("module_id debe ser positivo")
    
    if not (1 <= config.address <= 255):
        errors.append("address debe estar entre 1 y 255")
    
    if not config.name.strip():
        errors.append("name no puede estar vacío")
    
    if config.pulse_duration < 0:
        errors.append("pulse_duration no puede ser negativo")
    
    # Validaciones específicas por tipo
    capabilities = get_module_capabilities(config.module_type)
    
    if config.requires_ticket_validation and not capabilities['supports_tickets']:
        errors.append(f"Módulo tipo {config.module_type.name} no soporta validación de tickets")
    
    return errors