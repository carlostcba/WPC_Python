# core/communication/serial_comm.py
"""
Comunicación serie RS485 para módulos WPC
Equivalente a Comm.cls en VB6
"""
import serial
import serial.rs485
import time
import threading
from typing import Optional, Tuple
from dataclasses import dataclass
from config.settings import settings
from utils.logger import log_communication, log_error

@dataclass
class SerialConfig:
    """
    Configuración de comunicación serie
    Equivalente a Comm_INI en VB6
    """
    port: str = "COM1"
    baudrate: int = 9600
    parity: str = "N"  # N=None, E=Even, O=Odd
    data_bits: int = 8
    stop_bits: int = 1
    rts_enable_delay: int = 10    # ms
    rts_disable_delay: int = 10   # ms
    reply_timeout: int = 2000     # ms
    
    @classmethod
    def from_settings(cls) -> 'SerialConfig':
        """Crear configuración desde settings globales"""
        return cls(
            port=settings.SERIAL_PORT,
            baudrate=settings.SERIAL_BAUDRATE,
            reply_timeout=int(settings.SERIAL_TIMEOUT * 1000)
        )

class SerialCommunication:
    """
    Manejador de comunicación serie RS485
    Equivalente a Comm.cls en VB6
    """
    
    def __init__(self, config: Optional[SerialConfig] = None):
        """
        Inicializar comunicación serie
        
        Args:
            config: Configuración de puerto serie
        """
        self.config = config or SerialConfig.from_settings()
        self.serial_port: Optional[serial.Serial] = None
        self.is_initialized = False
        self.lock = threading.Lock()  # Para acceso thread-safe
        
    def initialize(self) -> bool:
        """
        Inicializar puerto serie
        Equivalente a InitComm en VB6
        
        Returns:
            bool: True si inicialización exitosa
        """
        try:
            # Cerrar puerto previo si existe
            self.close()
            
            # Configurar puerto serie
            self.serial_port = serial.Serial()
            self.serial_port.port = self.config.port
            self.serial_port.baudrate = self.config.baudrate
            
            # Configurar parámetros serie
            parity_map = {'N': serial.PARITY_NONE, 'E': serial.PARITY_EVEN, 'O': serial.PARITY_ODD}
            self.serial_port.parity = parity_map.get(self.config.parity, serial.PARITY_NONE)
            self.serial_port.bytesize = self.config.data_bits
            
            stopbits_map = {1: serial.STOPBITS_ONE, 2: serial.STOPBITS_TWO}
            self.serial_port.stopbits = stopbits_map.get(self.config.stop_bits, serial.STOPBITS_ONE)
            
            # Configuración de control de flujo
            self.serial_port.xonxoff = False
            self.serial_port.rtscts = False
            self.serial_port.dsrdtr = False
            
            # Timeouts
            self.serial_port.timeout = self.config.reply_timeout / 1000.0  # Convertir a segundos
            self.serial_port.write_timeout = 1.0
            
            # Configurar RS485 si está disponible
            if hasattr(self.serial_port, 'rs485_mode'):
                rs485_settings = serial.rs485.RS485Settings()
                rs485_settings.rts_level_for_tx = True
                rs485_settings.rts_level_for_rx = False
                # Algunos drivers solo admiten None en delay_before_*.
                rs485_settings.delay_before_tx = None
                rs485_settings.delay_before_rx = None
                self.serial_port.rs485_mode = rs485_settings
            
            # Abrir puerto
            self.serial_port.open()
            
            # Configuración inicial
            self.serial_port.reset_input_buffer()
            self.serial_port.reset_output_buffer()
            
            # Configurar RTS inicial (transmitter disabled)
            if not hasattr(self.serial_port, 'rs485_mode'):
                self.serial_port.rts = False
            
            self.is_initialized = True
            
            log_communication("SYSTEM", 0, f"Puerto serie inicializado: {self.config.port}")
            return True
            
        except Exception as e:
            log_error(e, f"initialize_serial({self.config.port})")
            self.is_initialized = False
            return False
    
    def close(self):
        """
        Cerrar puerto serie
        Equivalente a cerrar_previo en VB6
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
                log_communication("SYSTEM", 0, "Puerto serie cerrado")
        except Exception as e:
            log_error(e, "close_serial")
        finally:
            self.serial_port = None
            self.is_initialized = False
    
    def enable_transmitter(self):
        """
        Habilitar transmisor RS485
        Equivalente a EnableTransmitter en VB6
        """
        if not self.serial_port or not hasattr(self.serial_port, 'rs485_mode'):
            # Control manual de RTS para adaptadores RS485 básicos
            if self.serial_port:
                time.sleep(self.config.rts_disable_delay / 1000.0)
                self.serial_port.rts = True
                time.sleep(self.config.rts_enable_delay / 1000.0)
    
    def disable_transmitter(self):
        """
        Deshabilitar transmisor RS485
        Equivalente a DisableTransmitter en VB6
        """
        if not self.serial_port or not hasattr(self.serial_port, 'rs485_mode'):
            # Control manual de RTS
            if self.serial_port:
                time.sleep(self.config.rts_disable_delay / 1000.0)
                self.serial_port.rts = False
                
                # Limpiar buffer de entrada
                self.serial_port.reset_input_buffer()
                time.sleep(self.config.rts_enable_delay / 1000.0)
    
    def poll_slave(self, command: str, timeout_ms: Optional[int] = None, 
                   no_response: bool = False) -> Tuple[bool, str]:
        """
        Enviar comando y esperar respuesta
        Equivalente a PollSlave en VB6
        
        Args:
            command: Comando a enviar
            timeout_ms: Timeout específico en ms (opcional)
            no_response: Si True, no esperar respuesta
            
        Returns:
            Tuple[bool, str]: (éxito, respuesta)
        """
        if not self.is_initialized or not self.serial_port:
            return False, "Puerto serie no inicializado"
        
        # Configurar timeout específico si se proporciona
        original_timeout = self.serial_port.timeout
        if timeout_ms:
            self.serial_port.timeout = timeout_ms / 1000.0
        
        response = ""
        success = False
        
        try:
            with self.lock:  # Asegurar acceso exclusivo
                # Limpiar buffers
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
                
                # Habilitar transmisor
                self.enable_transmitter()
                
                # Enviar comando
                command_bytes = command.encode('latin-1')
                bytes_written = self.serial_port.write(command_bytes)
                
                # Esperar que se complete la transmisión
                self.serial_port.flush()
                
                # Deshabilitar transmisor
                self.disable_transmitter()
                
                if no_response:
                    success = True
                else:
                    # Leer respuesta
                    success, response = self._read_response()
                
        except Exception as e:
            log_error(e, f"poll_slave({command})")
            response = f"Error: {str(e)}"
        
        finally:
            # Restaurar timeout original
            if timeout_ms and self.serial_port:
                self.serial_port.timeout = original_timeout
        
        return success, response
    
    def _read_response(self) -> Tuple[bool, str]:
        """
        Leer respuesta del puerto serie hasta ETX
        
        Returns:
            Tuple[bool, str]: (éxito, respuesta completa)
        """
        response = ""
        etx_received = False
        start_time = time.time()
        timeout_seconds = self.serial_port.timeout or 2.0
        
        try:
            while not etx_received and (time.time() - start_time) < timeout_seconds:
                # Leer byte por byte
                if self.serial_port.in_waiting > 0:
                    byte_data = self.serial_port.read(1)
                    if byte_data:
                        char = byte_data.decode('latin-1', errors='ignore')
                        response += char
                        
                        # Verificar si recibimos ETX (fin de mensaje)
                        if ord(char) == 0x03:  # ASCII ETX
                            etx_received = True
                else:
                    # Pequeña pausa para no saturar CPU
                    time.sleep(0.001)
            
            return etx_received, response
            
        except Exception as e:
            log_error(e, "_read_response")
            return False, f"Error leyendo respuesta: {str(e)}"
    
    def test_communication(self) -> bool:
        """
        Probar comunicación básica
        
        Returns:
            bool: True si la comunicación funciona
        """
        if not self.is_initialized:
            return False
        
        try:
            # Enviar comando simple de test
            test_command = "\x02""01S0""\x03""4A"  # Status a dirección 1
            success, response = self.poll_slave(test_command, timeout_ms=1000)
            
            # Si hay respuesta (aunque sea error), la comunicación funciona
            return len(response) > 0
            
        except Exception as e:
            log_error(e, "test_communication")
            return False
    
    def get_port_info(self) -> dict:
        """
        Obtener información del puerto serie
        
        Returns:
            dict: Información del puerto
        """
        info = {
            'port': self.config.port,
            'baudrate': self.config.baudrate,
            'is_open': False,
            'is_initialized': self.is_initialized
        }
        
        if self.serial_port:
            info.update({
                'is_open': self.serial_port.is_open,
                'in_waiting': self.serial_port.in_waiting if self.serial_port.is_open else 0,
                'out_waiting': self.serial_port.out_waiting if self.serial_port.is_open else 0
            })
        
        return info
    
    def reopen_port(self) -> bool:
        """
        Cerrar y reabrir puerto (para recuperación de errores)
        Equivalente a Realizar_Cierre_y_Reapertura_del_puerto en VB6
        
        Returns:
            bool: True si reapertura exitosa
        """
        log_communication("SYSTEM", 0, "Reabriendo puerto serie por falta de comunicación")
        
        self.close()
        time.sleep(0.5)  # Pausa antes de reabrir
        
        return self.initialize()
    
    def __enter__(self):
        """Context manager entry"""
        if not self.is_initialized:
            self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

# Funciones de conveniencia
def create_serial_connection(config: Optional[SerialConfig] = None) -> SerialCommunication:
    """
    Crear y configurar conexión serie
    
    Args:
        config: Configuración opcional
        
    Returns:
        SerialCommunication: Instancia configurada
    """
    return SerialCommunication(config)

def test_serial_port(port: str = None) -> bool:
    """
    Probar puerto serie específico
    
    Args:
        port: Puerto a probar (default: desde configuración)
        
    Returns:
        bool: True si el puerto funciona
    """
    config = SerialConfig.from_settings()
    if port:
        config.port = port
    
    with SerialCommunication(config) as comm:
        return comm.test_communication()