# core/modules/module_manager.py
"""
Gestor de módulos de hardware
Coordina la configuración y estado de los módulos del sistema
"""
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from .module_types import (
    ModuleType, ModuleState, BarrierState, SensorState, 
    ModuleConfiguration, get_module_capabilities, validate_module_configuration
)
from core.database.models import Module, ModuleCamera
from core.database.managers import ModuleManager as DBModuleManager
from utils.logger import log_system, log_error

@dataclass
class ModuleRuntimeInfo:
    """
    Información de tiempo de ejecución de un módulo
    """
    module_id: int
    is_online: bool = False
    last_seen: Optional[datetime] = None
    error_count: int = 0
    total_commands_sent: int = 0
    total_responses_received: int = 0
    average_response_time: float = 0.0
    current_barrier_state: BarrierState = BarrierState.CLOSED
    current_sensor_state: SensorState = SensorState.FREE
    pending_commands_count: int = 0

class ModuleManager:
    """
    Gestor principal de módulos de hardware
    Maneja configuración, estado y operaciones de módulos
    """
    
    def __init__(self):
        """Inicializar gestor de módulos"""
        self.db_manager = DBModuleManager()
        self.modules_config: Dict[int, ModuleConfiguration] = {}
        self.runtime_info: Dict[int, ModuleRuntimeInfo] = {}
        self.initialized = False
    
    def initialize(self) -> bool:
        """
        Inicializar gestor de módulos
        
        Returns:
            bool: True si inicialización exitosa
        """
        try:
            log_system("Inicializando gestor de módulos...", "INFO")
            
            # Cargar configuración desde base de datos
            if not self._load_modules_from_database():
                return False
            
            # Validar configuración
            validation_errors = self._validate_all_modules()
            if validation_errors:
                log_system(f"Errores de validación encontrados: {len(validation_errors)}", "WARNING")
                for error in validation_errors:
                    log_system(f"  - {error}", "WARNING")
            
            # Inicializar información de runtime
            self._initialize_runtime_info()
            
            self.initialized = True
            log_system(f"Gestor de módulos inicializado con {len(self.modules_config)} módulos", "INFO")
            return True
            
        except Exception as e:
            log_error(e, "ModuleManager.initialize")
            return False
    
    def _load_modules_from_database(self) -> bool:
        """
        Cargar configuración de módulos desde base de datos
        
        Returns:
            bool: True si carga exitosa
        """
        try:
            modules = self.db_manager.get_all_modules()
            
            for module in modules:
                config = ModuleConfiguration(
                    module_id=module.ModuloID,
                    address=module.Address or 0,
                    module_type=self._determine_module_type(module),
                    name=module.Nombre or f"Module_{module.ModuloID}",
                    description=module.Descripcion or "",
                    group_id=module.GrupoModulos,
                    polling_order=module.OrdenEncuesta or 0,
                    pulse_duration=int(module.duracion_pulso or 0),
                    requires_ticket_validation=bool(module.ValidacionTicket),
                    entry_module_id=module.ModuloEntradaID,
                    exit_module_id=module.ModuloSalidaID
                )
                
                self.modules_config[module.ModuloID] = config
            
            log_system(f"Cargados {len(self.modules_config)} módulos desde base de datos", "DEBUG")
            return True
            
        except Exception as e:
            log_error(e, "_load_modules_from_database")
            return False
    
    def _determine_module_type(self, module: Module) -> ModuleType:
        """
        Determinar tipo de módulo basado en configuración
        
        Args:
            module: Modelo de módulo de BD
            
        Returns:
            ModuleType: Tipo determinado
        """
        # TODO: Implementar lógica para determinar tipo basado en categorías
        # Por ahora retornar tipo genérico
        if module.ValidacionTicket:
            return ModuleType.TICKET_DISPENSER
        else:
            return ModuleType.BARRIER  # Default
    
    def _validate_all_modules(self) -> List[str]:
        """
        Validar configuración de todos los módulos
        
        Returns:
            List[str]: Lista de errores encontrados
        """
        all_errors = []
        
        for module_id, config in self.modules_config.items():
            errors = validate_module_configuration(config)
            for error in errors:
                all_errors.append(f"Módulo {module_id}: {error}")
        
        # Validar direcciones únicas
        addresses = [config.address for config in self.modules_config.values() if config.address > 0]
        if len(addresses) != len(set(addresses)):
            all_errors.append("Direcciones RS485 duplicadas encontradas")
        
        return all_errors
    
    def _initialize_runtime_info(self):
        """
        Inicializar información de runtime para todos los módulos
        """
        for module_id in self.modules_config.keys():
            self.runtime_info[module_id] = ModuleRuntimeInfo(module_id=module_id)
    
    def get_module_config(self, module_id: int) -> Optional[ModuleConfiguration]:
        """
        Obtener configuración de un módulo
        
        Args:
            module_id: ID del módulo
            
        Returns:
            ModuleConfiguration: Configuración del módulo o None
        """
        return self.modules_config.get(module_id)
    
    def get_module_by_address(self, address: int) -> Optional[ModuleConfiguration]:
        """
        Obtener módulo por dirección RS485
        
        Args:
            address: Dirección RS485
            
        Returns:
            ModuleConfiguration: Configuración del módulo o None
        """
        for config in self.modules_config.values():
            if config.address == address:
                return config
        return None
    
    def get_modules_for_polling(self) -> List[ModuleConfiguration]:
        """
        Obtener módulos configurados para polling
        
        Returns:
            List[ModuleConfiguration]: Lista de módulos para polling
        """
        valid_modules = []
        
        for config in self.modules_config.values():
            if config.address > 0:  # Solo módulos con dirección válida
                valid_modules.append(config)
        
        # Ordenar por orden de encuesta
        valid_modules.sort(key=lambda m: (m.polling_order, m.module_id))
        
        return valid_modules
    
    def get_modules_by_type(self, module_type: ModuleType) -> List[ModuleConfiguration]:
        """
        Obtener módulos por tipo
        
        Args:
            module_type: Tipo de módulo
            
        Returns:
            List[ModuleConfiguration]: Lista de módulos del tipo especificado
        """
        return [config for config in self.modules_config.values() 
                if config.module_type == module_type]
    
    def get_modules_by_group(self, group_id: int) -> List[ModuleConfiguration]:
        """
        Obtener módulos por grupo
        
        Args:
            group_id: ID del grupo
            
        Returns:
            List[ModuleConfiguration]: Lista de módulos del grupo
        """
        return [config for config in self.modules_config.values() 
                if config.group_id == group_id]
    
    def update_module_runtime_status(self, module_id: int, **kwargs):
        """
        Actualizar estado de runtime de un módulo
        
        Args:
            module_id: ID del módulo
            **kwargs: Campos a actualizar
        """
        if module_id in self.runtime_info:
            runtime_info = self.runtime_info[module_id]
            
            for key, value in kwargs.items():
                if hasattr(runtime_info, key):
                    setattr(runtime_info, key, value)
    
    def get_module_runtime_info(self, module_id: int) -> Optional[ModuleRuntimeInfo]:
        """
        Obtener información de runtime de un módulo
        
        Args:
            module_id: ID del módulo
            
        Returns:
            ModuleRuntimeInfo: Información de runtime o None
        """
        return self.runtime_info.get(module_id)
    
    def is_module_online(self, module_id: int) -> bool:
        """
        Verificar si un módulo está online
        
        Args:
            module_id: ID del módulo
            
        Returns:
            bool: True si está online
        """
        runtime_info = self.runtime_info.get(module_id)
        if not runtime_info:
            return False
        
        # Considerar online si se vio en los últimos 30 segundos
        if runtime_info.last_seen:
            time_since_last_seen = datetime.now() - runtime_info.last_seen
            return time_since_last_seen.total_seconds() < 30
        
        return False
    
    def get_online_modules(self) -> List[int]:
        """
        Obtener lista de IDs de módulos online
        
        Returns:
            List[int]: Lista de IDs de módulos online
        """
        return [module_id for module_id in self.modules_config.keys() 
                if self.is_module_online(module_id)]
    
    def get_offline_modules(self) -> List[int]:
        """
        Obtener lista de IDs de módulos offline
        
        Returns:
            List[int]: Lista de IDs de módulos offline
        """
        return [module_id for module_id in self.modules_config.keys() 
                if not self.is_module_online(module_id)]
    
    def get_module_capabilities(self, module_id: int) -> Dict[str, bool]:
        """
        Obtener capacidades de un módulo
        
        Args:
            module_id: ID del módulo
            
        Returns:
            Dict[str, bool]: Capacidades del módulo
        """
        config = self.get_module_config(module_id)
        if config:
            return get_module_capabilities(config.module_type)
        return {}
    
    def can_module_validate_tickets(self, module_id: int) -> bool:
        """
        Verificar si un módulo puede validar tickets
        
        Args:
            module_id: ID del módulo
            
        Returns:
            bool: True si puede validar tickets
        """
        config = self.get_module_config(module_id)
        return config.requires_ticket_validation if config else False
    
    def get_related_modules(self, module_id: int) -> Dict[str, Optional[int]]:
        """
        Obtener módulos relacionados (entrada/salida)
        
        Args:
            module_id: ID del módulo
            
        Returns:
            Dict[str, Optional[int]]: Módulos de entrada y salida relacionados
        """
        config = self.get_module_config(module_id)
        if config:
            return {
                'entry_module': config.entry_module_id,
                'exit_module': config.exit_module_id
            }
        return {'entry_module': None, 'exit_module': None}
    
    def should_module_respond(self, module_id: int) -> bool:
        """
        Verificar si un módulo debe responder a identificaciones
        
        Args:
            module_id: ID del módulo
            
        Returns:
            bool: True si debe responder
        """
        # TODO: Implementar lógica basada en categorías de BD
        # Por ahora, asumir que todos los módulos responden
        return True
    
    def get_module_pulse_duration(self, module_id: int) -> int:
        """
        Obtener duración del pulso para un módulo
        
        Args:
            module_id: ID del módulo
            
        Returns:
            int: Duración en milisegundos
        """
        config = self.get_module_config(module_id)
        return config.pulse_duration if config else 1000
    
    def add_module_command_stat(self, module_id: int, response_time_ms: float = 0, success: bool = True):
        """
        Agregar estadística de comando para un módulo
        
        Args:
            module_id: ID del módulo
            response_time_ms: Tiempo de respuesta en ms
            success: Si el comando fue exitoso
        """
        runtime_info = self.runtime_info.get(module_id)
        if runtime_info:
            runtime_info.total_commands_sent += 1
            
            if success:
                runtime_info.total_responses_received += 1
                runtime_info.last_seen = datetime.now()
                runtime_info.is_online = True
                runtime_info.error_count = 0
                
                # Calcular promedio de tiempo de respuesta
                if response_time_ms > 0:
                    total_time = runtime_info.average_response_time * (runtime_info.total_responses_received - 1)
                    runtime_info.average_response_time = (total_time + response_time_ms) / runtime_info.total_responses_received
            else:
                runtime_info.error_count += 1
                runtime_info.is_online = False
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del sistema de módulos
        
        Returns:
            Dict[str, Any]: Estadísticas completas
        """
        total_modules = len(self.modules_config)
        online_modules = len(self.get_online_modules())
        offline_modules = len(self.get_offline_modules())
        
        # Estadísticas por tipo
        type_stats = {}
        for module_type in ModuleType:
            count = len(self.get_modules_by_type(module_type))
            if count > 0:
                type_stats[module_type.name] = count
        
        # Estadísticas de comunicación
        total_commands = sum(info.total_commands_sent for info in self.runtime_info.values())
        total_responses = sum(info.total_responses_received for info in self.runtime_info.values())
        success_rate = (total_responses / total_commands * 100) if total_commands > 0 else 0
        
        avg_response_time = 0
        if self.runtime_info:
            valid_times = [info.average_response_time for info in self.runtime_info.values() 
                          if info.average_response_time > 0]
            if valid_times:
                avg_response_time = sum(valid_times) / len(valid_times)
        
        return {
            'total_modules': total_modules,
            'online_modules': online_modules,
            'offline_modules': offline_modules,
            'online_percentage': (online_modules / total_modules * 100) if total_modules > 0 else 0,
            'modules_by_type': type_stats,
            'communication_stats': {
                'total_commands_sent': total_commands,
                'total_responses_received': total_responses,
                'success_rate_percentage': success_rate,
                'average_response_time_ms': avg_response_time
            }
        }
    
    def get_module_detailed_info(self, module_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener información detallada de un módulo
        
        Args:
            module_id: ID del módulo
            
        Returns:
            Dict[str, Any]: Información completa del módulo
        """
        config = self.get_module_config(module_id)
        runtime_info = self.get_module_runtime_info(module_id)
        
        if not config:
            return None
        
        capabilities = self.get_module_capabilities(module_id)
        related_modules = self.get_related_modules(module_id)
        
        result = {
            'configuration': {
                'module_id': config.module_id,
                'name': config.name,
                'description': config.description,
                'address': config.address,
                'module_type': config.module_type.name,
                'group_id': config.group_id,
                'polling_order': config.polling_order,
                'pulse_duration_ms': config.pulse_duration,
                'requires_ticket_validation': config.requires_ticket_validation,
                'entry_module_id': config.entry_module_id,
                'exit_module_id': config.exit_module_id
            },
            'capabilities': capabilities,
            'related_modules': related_modules,
            'runtime_status': {}
        }
        
        if runtime_info:
            result['runtime_status'] = {
                'is_online': runtime_info.is_online,
                'last_seen': runtime_info.last_seen.isoformat() if runtime_info.last_seen else None,
                'error_count': runtime_info.error_count,
                'total_commands_sent': runtime_info.total_commands_sent,
                'total_responses_received': runtime_info.total_responses_received,
                'success_rate': (runtime_info.total_responses_received / runtime_info.total_commands_sent * 100) 
                               if runtime_info.total_commands_sent > 0 else 0,
                'average_response_time_ms': runtime_info.average_response_time,
                'current_barrier_state': runtime_info.current_barrier_state.name,
                'current_sensor_state': runtime_info.current_sensor_state.name,
                'pending_commands_count': runtime_info.pending_commands_count
            }
        
        return result
    
    def validate_module_operation(self, module_id: int, operation: str) -> Tuple[bool, str]:
        """
        Validar si un módulo puede realizar una operación específica
        
        Args:
            module_id: ID del módulo
            operation: Operación a validar (open_barrier, validate_ticket, etc.)
            
        Returns:
            Tuple[bool, str]: (válido, mensaje de error si aplica)
        """
        config = self.get_module_config(module_id)
        if not config:
            return False, f"Módulo {module_id} no encontrado"
        
        if not self.is_module_online(module_id):
            return False, f"Módulo {module_id} no está online"
        
        capabilities = self.get_module_capabilities(module_id)
        
        operation_requirements = {
            'open_barrier': 'has_barrier',
            'validate_ticket': 'supports_tickets',
            'read_sensors': 'has_sensors'
        }
        
        required_capability = operation_requirements.get(operation)
        if required_capability and not capabilities.get(required_capability, False):
            return False, f"Módulo {module_id} no soporta operación: {operation}"
        
        return True, ""
    
    def reload_configuration(self) -> bool:
        """
        Recargar configuración desde base de datos
        
        Returns:
            bool: True si recarga exitosa
        """
        try:
            log_system("Recargando configuración de módulos...", "INFO")
            
            # Limpiar configuración actual
            self.modules_config.clear()
            
            # Recargar desde BD
            success = self._load_modules_from_database()
            
            if success:
                # Actualizar runtime info para nuevos módulos
                for module_id in self.modules_config.keys():
                    if module_id not in self.runtime_info:
                        self.runtime_info[module_id] = ModuleRuntimeInfo(module_id=module_id)
                
                # Remover runtime info de módulos que ya no existen
                existing_ids = set(self.modules_config.keys())
                to_remove = [mid for mid in self.runtime_info.keys() if mid not in existing_ids]
                for module_id in to_remove:
                    del self.runtime_info[module_id]
                
                log_system(f"Configuración recargada: {len(self.modules_config)} módulos", "INFO")
            
            return success
            
        except Exception as e:
            log_error(e, "reload_configuration")
            return False
    
    def export_configuration(self) -> Dict[str, Any]:
        """
        Exportar configuración completa para backup/debug
        
        Returns:
            Dict[str, Any]: Configuración exportada
        """
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'total_modules': len(self.modules_config),
            'modules': []
        }
        
        for config in self.modules_config.values():
            module_data = {
                'module_id': config.module_id,
                'name': config.name,
                'address': config.address,
                'module_type': config.module_type.name,
                'configuration': config.__dict__
            }
            
            runtime_info = self.runtime_info.get(config.module_id)
            if runtime_info:
                module_data['runtime_info'] = runtime_info.__dict__.copy()
                # Convertir datetime a string para serialización
                if module_data['runtime_info']['last_seen']:
                    module_data['runtime_info']['last_seen'] = runtime_info.last_seen.isoformat()
            
            export_data['modules'].append(module_data)
        
        return export_data

# Funciones de conveniencia
def get_module_manager() -> ModuleManager:
    """
    Obtener instancia del gestor de módulos (singleton)
    
    Returns:
        ModuleManager: Instancia del gestor
    """
    if not hasattr(get_module_manager, '_instance'):
        get_module_manager._instance = ModuleManager()
    return get_module_manager._instance