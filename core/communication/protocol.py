# core/communication/protocol.py
"""
Manejador del protocolo de comunicación RS485
Equivalente a Protocolo.cls en VB6
"""
from typing import Optional, Dict, Any
from datetime import datetime
from core.modules.module_types import ProtocolConstants, CommandType
from utils.logger import log_communication

class ProtocolHandler:
    """
    Maneja el protocolo de comunicación con módulos RS485
    Equivalente a Protocolo.cls en VB6
    """
    
    # Constantes ASCII del protocolo
    ASCII_STX = 0x02  # Start of Text
    ASCII_ETX = 0x03  # End of Text
    ASCII_ACK = 0x06  # Acknowledge
    ASCII_NAK = 0x15  # Negative Acknowledge
    
    def __init__(self):
        """Inicializar manejador de protocolo"""
        pass
    
    def read_status(self, address: int) -> str:
        """
        Generar comando de lectura de estado
        Equivalente a ReadStatus en VB6
        
        Args:
            address: Dirección del módulo (1-255)
            
        Returns:
            str: Comando formateado para envío
        """
        if not (1 <= address <= 255):
            raise ValueError(f"Dirección inválida: {address}")
        
        # Formato: STX + ADDRESS + "S0" + ETX + CHECKSUM
        address_str = f"{address:02d}"
        command_body = f"{chr(self.ASCII_STX)}{address_str}S0{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def set_time(self, address: int, target_datetime: Optional[datetime] = None) -> str:
        """
        Generar comando de sincronización de fecha/hora
        Equivalente a SetTime en VB6
        
        Args:
            address: Dirección del módulo
            target_datetime: Fecha/hora a configurar (default: ahora)
            
        Returns:
            str: Comando formateado
        """
        if target_datetime is None:
            target_datetime = datetime.now()
        
        address_str = f"{address:02d}"
        
        # Formato fecha/hora: AAMMDDHHMMSS
        time_str = target_datetime.strftime("%y%m%d%H%M%S")
        
        command_body = f"{chr(self.ASCII_STX)}{address_str}T0{time_str}{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def continue_sequence(self, address: int, extra_data: str = "") -> str:
        """
        Generar comando de continuación de secuencia (apertura)
        Equivalente a ContSec en VB6
        
        Args:
            address: Dirección del módulo
            extra_data: Datos adicionales del comando
            
        Returns:
            str: Comando formateado
        """
        address_str = f"{address:02d}"
        command_body = f"{chr(self.ASCII_STX)}{address_str}K1{extra_data}{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def stop_sequence(self, address: int) -> str:
        """
        Generar comando de detención de secuencia
        Equivalente a StopSec en VB6
        
        Args:
            address: Dirección del módulo
            
        Returns:
            str: Comando formateado
        """
        address_str = f"{address:02d}"
        command_body = f"{chr(self.ASCII_STX)}{address_str}K0{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def pulse_output(self, address: int, output_number: int, duration_ms: int = 1000) -> str:
        """
        Generar comando de pulso de salida
        
        Args:
            address: Dirección del módulo
            output_number: Número de salida (1-8)
            duration_ms: Duración del pulso en milisegundos
            
        Returns:
            str: Comando formateado
        """
        if not (1 <= output_number <= 8):
            raise ValueError(f"Número de salida inválido: {output_number}")
        
        address_str = f"{address:02d}"
        duration_str = f"{duration_ms:04d}"
        
        command_body = f"{chr(self.ASCII_STX)}{address_str}P{output_number}{duration_str}{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def ok_download_novelty(self, address: int) -> str:
        """
        Generar comando OK para bajar novedad del buffer
        Equivalente a Ok_Bajar_novedad en VB6
        
        Args:
            address: Dirección del módulo
            
        Returns:
            str: Comando formateado
        """
        address_str = f"{address:02d}"
        command_body = f"{chr(self.ASCII_STX)}{address_str}O1{chr(self.ASCII_ETX)}"
        checksum = self.calculate_checksum(command_body)
        
        full_command = command_body + checksum
        
        log_communication("TX", address, full_command)
        return full_command
    
    def calculate_checksum(self, command: str) -> str:
        """
        Calcular checksum de comando
        Equivalente a CalculoCS en VB6
        
        Args:
            command: Comando sin checksum
            
        Returns:
            str: Checksum de 2 caracteres hexadecimales
        """
        if not command:
            return "00"
        
        # Sumar valores ASCII de todos los caracteres
        checksum_value = sum(ord(char) for char in command)
        
        # Obtener los 2 dígitos menos significativos en hexadecimal
        checksum_hex = f"{checksum_value & 0xFF:02X}"
        
        return checksum_hex
    
    def validate_response(self, response: str, expected_address: int) -> Dict[str, Any]:
        """
        Validar respuesta recibida del módulo
        Equivalente a análisis en MPolling.bas
        
        Args:
            response: Respuesta completa recibida
            expected_address: Dirección esperada del módulo
            
        Returns:
            dict: Resultado de validación con campos:
                - valid: bool
                - error: str (si hay error)
                - address: int (dirección extraída)
                - command: str (comando de respuesta)
                - data: str (datos de la respuesta)
        """
        result = {
            'valid': False,
            'error': '',
            'address': 0,
            'command': '',
            'data': ''
        }
        
        try:
            # Verificar longitud mínima
            if len(response) < 7:
                result['error'] = "Respuesta muy corta o vacía"
                return result
            
            # Verificar caracteres STX y ETX
            if response[0] != chr(self.ASCII_STX):
                result['error'] = "STX incorrecto"
                return result
            
            if chr(self.ASCII_ETX) not in response:
                result['error'] = "ETX no encontrado"
                return result
            
            # Encontrar posición de ETX
            etx_pos = response.find(chr(self.ASCII_ETX))
            if etx_pos == -1:
                result['error'] = "ETX no encontrado"
                return result
            
            # Extraer checksum
            if len(response) < etx_pos + 3:
                result['error'] = "Checksum faltante"
                return result
            
            received_checksum = response[etx_pos + 1:etx_pos + 3]
            command_body = response[:etx_pos + 1]
            
            # Calcular checksum esperado
            calculated_checksum = self.calculate_checksum(command_body)
            
            if received_checksum.upper() != calculated_checksum.upper():
                result['error'] = f"Checksum incorrecto: esperado {calculated_checksum}, recibido {received_checksum}"
                return result
            
            # Extraer dirección
            try:
                address = int(response[1:3])
                result['address'] = address
            except ValueError:
                result['error'] = "Dirección inválida en respuesta"
                return result
            
            # Verificar dirección esperada
            if address != expected_address:
                result['error'] = f"Dirección incorrecta: esperada {expected_address}, recibida {address}"
                return result
            
            # Extraer comando de respuesta
            if len(response) >= 5:
                result['command'] = response[3:5]
            
            # Extraer datos (entre comando y ETX)
            if etx_pos > 5:
                result['data'] = response[5:etx_pos]
            
            result['valid'] = True
            log_communication("RX", address, response)
            
        except Exception as e:
            result['error'] = f"Error procesando respuesta: {str(e)}"
        
        return result
    
    def parse_status_response(self, response_data: str) -> Dict[str, Any]:
        """
        Parsear respuesta de estado del módulo
        
        Args:
            response_data: Datos de la respuesta (sin STX, dirección, comando, ETX, checksum)
            
        Returns:
            dict: Estado parseado del módulo
        """
        status = {
            'barrier_state': 0,  # 0: cerrada, 1: abierta
            'sensor_ddmm': 0,    # 0: libre, 1: ocupado
            'inputs': [],        # Estados de entradas digitales
            'outputs': [],       # Estados de salidas digitales
            'has_novelty': False, # Si hay novedad en buffer
            'error_code': 0      # Código de error del módulo
        }
        
        if not response_data:
            return status
        
        try:
            # El formato exacto depende del tipo de módulo
            # Implementación básica para módulos estándar
            
            if len(response_data) >= 2:
                # Primer byte: estado general
                general_state = ord(response_data[0])
                status['barrier_state'] = (general_state >> 0) & 1
                status['sensor_ddmm'] = (general_state >> 1) & 1
                status['has_novelty'] = (general_state >> 7) & 1
                
                # Segundo byte: entradas digitales
                if len(response_data) >= 2:
                    inputs_byte = ord(response_data[1])
                    status['inputs'] = [(inputs_byte >> i) & 1 for i in range(8)]
            
        except Exception as e:
            log_communication("ERROR", 0, f"Error parseando estado: {e}")
        
        return status
    
    def get_command_timeout(self, command_type: str) -> int:
        """
        Obtener timeout apropiado según tipo de comando
        
        Args:
            command_type: Tipo de comando (S0, K1, etc.)
            
        Returns:
            int: Timeout en milisegundos
        """
        timeouts = {
            'S0': 2000,    # Status
            'S6': 2000,    # Status con novedad
            'K1': 1000,    # Continuar secuencia
            'K0': 1000,    # Parar secuencia
            'T0': 3000,    # Sincronizar tiempo
            'O1': 1000,    # OK bajar novedad
            'O5': 5000,    # Alta propietario
            'O6': 5000,    # Baja propietario
            'O8': 5000,    # Consulta propietario
            'O9': 5000,    # Consulta espacio buffer
        }
        
        return timeouts.get(command_type, ProtocolConstants.RESPONSE_TIMEOUT)