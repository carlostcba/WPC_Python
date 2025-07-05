# utils/logger.py
"""
Sistema de logging para WPC
Reemplaza mdlmensajes.bas de VB6
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional
from config.settings import settings

class WPCLogger:
    """
    Gestor de logging del sistema WPC
    Equivalente a las funciones de mdlmensajes.bas
    """
    
    _instance: Optional['WPCLogger'] = None
    _logger: Optional[logging.Logger] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def setup(self) -> logging.Logger:
        """
        Configurar sistema de logging
        Equivalente a la inicialización en VB6
        """
        if self._logger is not None:
            return self._logger
        
        # Crear logger principal
        self._logger = logging.getLogger('wpc')
        self._logger.setLevel(getattr(logging, settings.LOG_LEVEL))
        
        # Evitar duplicación de handlers
        if self._logger.handlers:
            return self._logger
        
        # Formatter para logs
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
        
        # Handler para archivo con rotación
        if settings.LOG_FILE:
            try:
                # Asegurar que el directorio existe
                settings.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
                
                file_handler = logging.handlers.RotatingFileHandler(
                    filename=settings.LOG_FILE,
                    maxBytes=10*1024*1024,  # 10 MB
                    backupCount=5,
                    encoding='utf-8'
                )
                file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
                file_handler.setFormatter(formatter)
                self._logger.addHandler(file_handler)
                
            except Exception as e:
                self._logger.warning(f"No se pudo configurar logging a archivo: {e}")
        
        return self._logger
    
    def log_system_message(self, message: str, level: str = "INFO", 
                          to_file: bool = True, show_dialog: bool = False):
        """
        Registrar mensaje del sistema
        Equivalente a Mensajes_Sistema en VB6
        
        Args:
            message: Mensaje a registrar
            level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            to_file: Si escribir a archivo (equivale al parámetro VB6)
            show_dialog: Si mostrar diálogo (equivale al parámetro VB6)
        """
        if not self._logger:
            self.setup()
        
        # Registrar en log
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._logger.log(log_level, message)
        
        # Mostrar diálogo si se requiere (para errores críticos)
        if show_dialog and level.upper() in ['ERROR', 'CRITICAL']:
            try:
                # Solo si hay interfaz gráfica disponible
                from PyQt6.QtWidgets import QMessageBox, QApplication
                if QApplication.instance():
                    if level.upper() == 'CRITICAL':
                        QMessageBox.critical(None, "Error Crítico", message)
                    else:
                        QMessageBox.warning(None, "Advertencia", message)
            except ImportError:
                # No hay GUI disponible, solo log
                pass
    
    def log_communication(self, direction: str, module_id: int, 
                         command: str, response: str = ""):
        """
        Registrar comunicación con módulos
        Equivalente al logging de comunicación serie en VB6
        
        Args:
            direction: 'TX' o 'RX'
            module_id: ID del módulo
            command: Comando enviado
            response: Respuesta recibida (si aplica)
        """
        if not self._logger:
            self.setup()
        
        comm_logger = logging.getLogger('wpc.communication')
        
        if direction == 'TX':
            comm_logger.debug(f"TX -> Módulo {module_id}: {command}")
        elif direction == 'RX':
            comm_logger.debug(f"RX <- Módulo {module_id}: {response}")
        else:
            comm_logger.debug(f"{direction} | Módulo {module_id}: {command} -> {response}")
    
    def log_movement(self, movement_id: int, module_id: int, 
                    identification: str, result: str):
        """
        Registrar evento de movimiento
        """
        if not self._logger:
            self.setup()
        
        movement_logger = logging.getLogger('wpc.movements')
        movement_logger.info(
            f"Movimiento {movement_id}: Módulo {module_id}, "
            f"ID {identification}, Resultado: {result}"
        )
    
    def log_error(self, error: Exception, context: str = ""):
        """
        Registrar error con contexto
        """
        if not self._logger:
            self.setup()
        
        error_msg = f"Error en {context}: {str(error)}" if context else str(error)
        self._logger.error(error_msg, exc_info=True)

# Instancia global del logger
wpc_logger = WPCLogger()

def setup_logging() -> logging.Logger:
    """
    Función de conveniencia para configurar logging
    """
    return wpc_logger.setup()

def log_system(message: str, level: str = "INFO", to_file: bool = True, 
               show_dialog: bool = False):
    """
    Función de conveniencia para logging de sistema
    """
    wpc_logger.log_system_message(message, level, to_file, show_dialog)

def log_communication(direction: str, module_id: int, command: str, response: str = ""):
    """
    Función de conveniencia para logging de comunicación
    """
    wpc_logger.log_communication(direction, module_id, command, response)

def log_movement(movement_id: int, module_id: int, identification: str, result: str):
    """
    Función de conveniencia para logging de movimientos
    """
    wpc_logger.log_movement(movement_id, module_id, identification, result)

def log_error(error: Exception, context: str = ""):
    """
    Función de conveniencia para logging de errores
    """
    wpc_logger.log_error(error, context)