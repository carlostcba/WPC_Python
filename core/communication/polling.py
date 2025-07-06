# core/communication/polling.py
"""
Motor de encuestas a módulos RS485
Equivalente a MPolling.bas en VB6
"""
import asyncio
import time
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .protocol import ProtocolHandler
from .serial_comm import SerialCommunication, SerialConfig
from core.modules.module_types import ModuleState, BarrierState, SensorState
from core.database.managers import MovementManager, TicketManager
from core.database.models import Module
from config.settings import settings
from utils.logger import log_communication, log_error, log_system

@dataclass
class ModuleStatus:
    """
    Estado actual de un módulo
    Equivalente a elementos del vector Addresses() en VB6
    """
    module_id: int
    address: int
    name: str = ""
    module_type: int = 0
    
    # Estado operativo
    state: ModuleState = ModuleState.OFFLINE
    barrier_state: BarrierState = BarrierState.CLOSED
    sensor_ddmm: SensorState = SensorState.FREE
    
    # Control de comunicación
    retry_count: int = 0
    max_retries: int = 3
    consecutive_errors: int = 0
    last_communication: Optional[datetime] = None
    last_command: str = ""
    
    # Cola de comandos pendientes
    pending_commands: List[str] = field(default_factory=list)
    
    # Configuración específica
    requires_response: bool = True
    poll_enabled: bool = True
    entry_module_id: Optional[int] = None
    exit_module_id: Optional[int] = None
    
    def add_pending_command(self, command: str):
        """Agregar comando a la cola de pendientes"""
        if command not in self.pending_commands:
            self.pending_commands.append(command)
    
    def get_next_command(self) -> Optional[str]:
        """Obtener próximo comando pendiente"""
        if self.pending_commands:
            return self.pending_commands.pop(0)
        return None
    
    def clear_pending_commands(self):
        """Limpiar todos los comandos pendientes"""
        self.pending_commands.clear()

class PollingManager:
    """
    Gestor del polling cíclico a módulos
    Equivalente a MPolling.bas en VB6
    """
    
    def __init__(self, module_manager=None):
        """
        Inicializar gestor de polling
        
        Args:
            module_manager: Gestor de módulos (opcional)
        """
        self.protocol = ProtocolHandler()
        self.serial_comm: Optional[SerialCommunication] = None
        self.movement_manager = MovementManager()
        self.ticket_manager = TicketManager()
        
        # Estado del polling
        self.is_running = False
        self.modules: Dict[int, ModuleStatus] = {}  # key: address
        self.current_module_index = 0
        self.polling_interval = settings.POLLING_INTERVAL / 1000.0  # Convertir a segundos
        
        # Control de errores
        self.consecutive_errors = 0
        self.max_consecutive_errors = 10
        self.port_reopen_count = 0
        
        # Callbacks para eventos
        self.event_callbacks: Dict[str, List[Callable]] = {
            'movement_detected': [],
            'module_state_changed': [],
            'communication_error': [],
            'novelty_received': []
        }
        
        # Task para polling asíncrono
        self.polling_task: Optional[asyncio.Task] = None
    
    def initialize(self) -> bool:
        """
        Inicializar sistema de polling
        
        Returns:
            bool: True si inicialización exitosa
        """
        try:
            # Inicializar comunicación serie
            serial_config = SerialConfig.from_settings()
            self.serial_comm = SerialCommunication(serial_config)
            
            if not self.serial_comm.initialize():
                log_error(Exception("Error inicializando puerto serie"), "PollingManager.initialize")
                return False
            
            # Cargar configuración de módulos
            self._load_modules_configuration()
            
            log_system("Sistema de polling inicializado correctamente", "INFO")
            return True
            
        except Exception as e:
            log_error(e, "PollingManager.initialize")
            return False
    
    def _load_modules_configuration(self):
        """
        Cargar configuración de módulos desde base de datos
        Equivalente a cargar vector Addresses() en VB6
        """
        try:
            from core.database.managers import ModuleManager
            module_manager = ModuleManager()
            
            modules = module_manager.get_modules_for_polling()
            
            for module in modules:
                module_status = ModuleStatus(
                    module_id=module.ModuloID,
                    address=module.Address,
                    name=module.Nombre or f"Module_{module.ModuloID}",
                    entry_module_id=module.ModuloEntradaID,
                    exit_module_id=module.ModuloSalidaID
                )
                
                self.modules[module.Address] = module_status
                log_system(f"Módulo cargado: {module_status.name} (Address: {module_status.address})", "DEBUG")
            
            log_system(f"Cargados {len(self.modules)} módulos para polling", "INFO")
            
        except Exception as e:
            log_error(e, "_load_modules_configuration")
    
    def start(self):
        """
        Iniciar polling asíncrono
        """
        if self.is_running:
            log_system("Polling ya está ejecutándose", "WARNING")
            return
        
        if not self.serial_comm or not self.serial_comm.is_initialized:
            log_error(Exception("Comunicación serie no inicializada"), "PollingManager.start")
            return
        
        self.is_running = True
        
        # Iniciar task asíncrona
        loop = asyncio.get_event_loop()
        self.polling_task = loop.create_task(self._polling_loop())
        
        log_system("Polling iniciado", "INFO")
    
    def stop(self):
        """
        Detener polling
        """
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.polling_task:
            self.polling_task.cancel()
            self.polling_task = None
        
        if self.serial_comm:
            self.serial_comm.close()
        
        log_system("Polling detenido", "INFO")
    
    async def _polling_loop(self):
        """
        Loop principal de polling
        Equivalente al timer principal en VB6
        """
        try:
            module_addresses = list(self.modules.keys())
            
            while self.is_running:
                if not module_addresses:
                    await asyncio.sleep(1.0)
                    continue
                
                # Obtener siguiente módulo
                current_address = module_addresses[self.current_module_index]
                module_status = self.modules[current_address]
                
                # Procesar módulo actual
                await self._poll_module(module_status)
                
                # Avanzar al siguiente módulo
                self.current_module_index = (self.current_module_index + 1) % len(module_addresses)
                
                # Pausa entre módulos
                await asyncio.sleep(self.polling_interval)
                
        except asyncio.CancelledError:
            log_system("Polling loop cancelado", "INFO")
        except Exception as e:
            log_error(e, "_polling_loop")
            self.is_running = False
    
    async def _poll_module(self, module_status: ModuleStatus):
        """
        Encuestar un módulo específico
        Equivalente a la encuesta individual en VB6
        
        Args:
            module_status: Estado del módulo a encuestar
        """
        try:
            # Determinar comando a enviar
            command = module_status.get_next_command()
            if not command:
                # No hay comandos pendientes, enviar status
                command = self.protocol.read_status(module_status.address)
            
            module_status.last_command = command
            
            # Obtener timeout específico según comando
            command_type = self._extract_command_type(command)
            timeout_ms = self.protocol.get_command_timeout(command_type)
            
            # Enviar comando y esperar respuesta
            success, response = self.serial_comm.poll_slave(command, timeout_ms)
            
            if success and response:
                # Analizar respuesta
                await self._analyze_response(response, module_status)
            else:
                # Procesar error de comunicación
                await self._process_communication_error(module_status, command, response)
                
        except Exception as e:
            log_error(e, f"_poll_module(address={module_status.address})")
            await self._process_communication_error(module_status, "", str(e))
    
    async def _analyze_response(self, response: str, module_status: ModuleStatus):
        """
        Analizar respuesta del módulo
        Equivalente a Analyze en VB6
        
        Args:
            response: Respuesta recibida
            module_status: Estado del módulo
        """
        try:
            # Validar respuesta
            validation = self.protocol.validate_response(response, module_status.address)
            
            if not validation['valid']:
                log_communication("ERROR", module_status.address, 
                                f"Respuesta inválida: {validation['error']}")
                await self._process_communication_error(module_status, module_status.last_command, 
                                                      validation['error'])
                return
            
            # Respuesta válida, resetear contadores de error
            self.consecutive_errors = 0
            module_status.retry_count = 0
            module_status.consecutive_errors = 0
            module_status.last_communication = datetime.now()
            module_status.state = ModuleState.ONLINE
            
            # Procesar respuesta según tipo
            await self._process_valid_response(validation, module_status)
            
            # Notificar cambio de estado si es necesario
            await self._notify_module_state_change(module_status)
            
        except Exception as e:
            log_error(e, f"_analyze_response(module={module_status.address})")
    
    async def _process_valid_response(self, validation: Dict[str, Any], module_status: ModuleStatus):
        """
        Procesar respuesta válida del módulo
        Equivalente a Procesar_Respuesta en VB6
        
        Args:
            validation: Resultado de validación
            module_status: Estado del módulo
        """
        command_type = validation['command']
        response_data = validation['data']
        
        try:
            if command_type in ['S0', 'S6']:
                # Respuesta de estado
                await self._process_status_response(response_data, module_status)
                
                # Si es S6, hay novedad en buffer
                if command_type == 'S6':
                    await self._process_novelty(response_data, module_status)
            
            elif command_type in ['K1', 'K0']:
                # Respuesta a comando de control
                log_communication("INFO", module_status.address, 
                                f"Comando {command_type} ejecutado correctamente")
            
            elif command_type == 'O1':
                # Confirmación de descarga de novedad
                log_communication("INFO", module_status.address, "Novedad descargada")
            
        except Exception as e:
            log_error(e, f"_process_valid_response(module={module_status.address})")
    
    async def _process_status_response(self, response_data: str, module_status: ModuleStatus):
        """
        Procesar respuesta de estado del módulo
        
        Args:
            response_data: Datos de la respuesta
            module_status: Estado del módulo
        """
        try:
            status = self.protocol.parse_status_response(response_data)
            
            # Actualizar estado del módulo
            old_barrier = module_status.barrier_state
            old_sensor = module_status.sensor_ddmm
            
            module_status.barrier_state = BarrierState(status['barrier_state'])
            module_status.sensor_ddmm = SensorState(status['sensor_ddmm'])
            
            # Detectar cambios significativos
            if old_barrier != module_status.barrier_state or old_sensor != module_status.sensor_ddmm:
                log_communication("STATUS", module_status.address,
                                f"Barrera: {module_status.barrier_state.name}, "
                                f"Sensor: {module_status.sensor_ddmm.name}")
                
                await self._notify_module_state_change(module_status)
            
        except Exception as e:
            log_error(e, f"_process_status_response(module={module_status.address})")
    
    async def _process_novelty(self, response_data: str, module_status: ModuleStatus):
        """
        Procesar novedad detectada en módulo
        Equivalente a Hubo_Novedad en VB6
        
        Args:
            response_data: Datos de la novedad
            module_status: Estado del módulo
        """
        try:
            # Extraer información de la novedad
            if len(response_data) >= 8:
                # Formato típico: NNNNNNNNDDHHMMSS (identificación + timestamp)
                identification = response_data[:8]
                timestamp_str = response_data[8:14] if len(response_data) >= 14 else ""
                
                log_communication("NOVELTY", module_status.address,
                                f"ID: {identification}, Time: {timestamp_str}")
                
                # Procesar identificación reconocida
                await self._process_identification(identification, module_status)
                
                # Enviar comando para confirmar descarga de novedad
                ack_command = self.protocol.ok_download_novelty(module_status.address)
                module_status.add_pending_command(ack_command)
            
        except Exception as e:
            log_error(e, f"_process_novelty(module={module_status.address})")
    
    async def _process_identification(self, identification: str, module_status: ModuleStatus):
        """
        Procesar identificación reconocida
        Equivalente a Procesar_id_Reconocido en VB6
        
        Args:
            identification: Número de identificación
            module_status: Estado del módulo
        """
        try:
            # Validar acceso
            access_result = self.movement_manager.validate_identification(
                identification, module_status.module_id
            )
            
            if access_result.allowed:
                # Crear movimiento en base de datos
                success, movement_id = self.movement_manager.create_movement(
                    identification, module_status.module_id
                )
                
                if success:
                    log_system(f"Movimiento creado: {movement_id} - {identification}", "INFO")
                    
                    # Si el módulo responde, enviar comando de apertura
                    if module_status.requires_response:
                        open_command = self.protocol.continue_sequence(module_status.address)
                        module_status.add_pending_command(open_command)
                    
                    # Notificar evento
                    await self._notify_movement_detected(identification, module_status, access_result.person)
                else:
                    log_error(Exception("Error creando movimiento"), 
                            f"identification={identification}")
            else:
                log_system(f"Acceso denegado: {identification} - {access_result.reason}", "WARNING")
                # Opcional: comando de rechazo o mensaje
            
        except Exception as e:
            log_error(e, f"_process_identification({identification})")
    
    async def _process_communication_error(self, module_status: ModuleStatus, 
                                         command: str, error_msg: str):
        """
        Procesar error de comunicación
        Equivalente a Procesar_Respuesta_Erronea en VB6
        
        Args:
            module_status: Estado del módulo
            command: Comando que falló
            error_msg: Mensaje de error
        """
        try:
            # Incrementar contadores de error
            module_status.retry_count += 1
            self.consecutive_errors += 1
            module_status.consecutive_errors += 1
            
            log_communication("ERROR", module_status.address,
                            f"Error comunicación (intento {module_status.retry_count}): {error_msg}")
            
            # Si se exceden los reintentos para este módulo
            if module_status.retry_count >= module_status.max_retries:
                module_status.state = ModuleState.ERROR
                module_status.retry_count = 0
                module_status.clear_pending_commands()
                
                error_type = "status" if not command or "S0" in command else "command"
                log_system(f"Módulo {module_status.address} sin respuesta ({error_type})", "ERROR")
                
                await self._notify_module_state_change(module_status)
            
            # Si hay demasiados errores consecutivos, reabrir puerto
            if self.consecutive_errors >= self.max_consecutive_errors:
                await self._reopen_serial_port()
            
        except Exception as e:
            log_error(e, f"_process_communication_error(module={module_status.address})")
    
    async def _reopen_serial_port(self):
        """
        Reabrir puerto serie por errores de comunicación
        Equivalente a Realizar_Cierre_y_Reapertura_del_puerto en VB6
        """
        try:
            log_system("Reabriendo puerto serie por errores de comunicación", "WARNING")
            
            if self.serial_comm:
                success = self.serial_comm.reopen_port()
                if success:
                    self.consecutive_errors = 0
                    self.port_reopen_count += 1
                    log_system("Puerto serie reabierto exitosamente", "INFO")
                else:
                    log_error(Exception("Error reabriendo puerto"), "_reopen_serial_port")
            
        except Exception as e:
            log_error(e, "_reopen_serial_port")
    
    def send_command(self, address: int, command: str, immediate: bool = False) -> bool:
        """
        Enviar comando a módulo específico
        
        Args:
            address: Dirección del módulo
            command: Comando a enviar
            immediate: Si True, enviar inmediatamente
            
        Returns:
            bool: True si comando enviado/encolado exitosamente
        """
        try:
            if address not in self.modules:
                log_error(Exception(f"Módulo no encontrado: {address}"), "send_command")
                return False
            
            module_status = self.modules[address]
            
            if immediate and self.serial_comm:
                # Enviar inmediatamente
                success, response = self.serial_comm.poll_slave(command)
                log_communication("IMMEDIATE", address, f"Cmd: {command}, Success: {success}")
                return success
            else:
                # Agregar a cola de pendientes
                module_status.add_pending_command(command)
                log_communication("QUEUED", address, f"Comando encolado: {command}")
                return True
                
        except Exception as e:
            log_error(e, f"send_command({address}, {command})")
            return False
    
    def _extract_command_type(self, command: str) -> str:
        """
        Extraer tipo de comando de la cadena completa
        
        Args:
            command: Comando completo
            
        Returns:
            str: Tipo de comando (S0, K1, etc.)
        """
        try:
            if len(command) >= 5:
                return command[3:5]
        except:
            pass
        return "S0"  # Default
    
    # Métodos para callbacks de eventos
    def subscribe_to_event(self, event_type: str, callback: Callable):
        """
        Suscribirse a eventos del polling
        
        Args:
            event_type: Tipo de evento
            callback: Función de callback
        """
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)
    
    async def _notify_movement_detected(self, identification: str, module_status: ModuleStatus, person=None):
        """Notificar movimiento detectado"""
        for callback in self.event_callbacks['movement_detected']:
            try:
                await callback(identification, module_status, person)
            except Exception as e:
                log_error(e, "movement_detected_callback")
    
    async def _notify_module_state_change(self, module_status: ModuleStatus):
        """Notificar cambio de estado de módulo"""
        for callback in self.event_callbacks['module_state_changed']:
            try:
                await callback(module_status)
            except Exception as e:
                log_error(e, "module_state_change_callback")
    
    def get_module_status(self, address: int) -> Optional[ModuleStatus]:
        """
        Obtener estado actual de un módulo
        
        Args:
            address: Dirección del módulo
            
        Returns:
            ModuleStatus: Estado del módulo o None
        """
        return self.modules.get(address)
    
    def get_all_modules_status(self) -> Dict[int, ModuleStatus]:
        """
        Obtener estado de todos los módulos
        
        Returns:
            dict: Diccionario con estados de módulos
        """
        return self.modules.copy()
    
    def get_polling_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del polling
        
        Returns:
            dict: Estadísticas del sistema
        """
        online_modules = sum(1 for m in self.modules.values() if m.state == ModuleState.ONLINE)
        offline_modules = sum(1 for m in self.modules.values() if m.state == ModuleState.OFFLINE)
        error_modules = sum(1 for m in self.modules.values() if m.state == ModuleState.ERROR)
        
        return {
            'is_running': self.is_running,
            'total_modules': len(self.modules),
            'online_modules': online_modules,
            'offline_modules': offline_modules,
            'error_modules': error_modules,
            'consecutive_errors': self.consecutive_errors,
            'port_reopen_count': self.port_reopen_count,
            'serial_port_info': self.serial_comm.get_port_info() if self.serial_comm else {}
        }