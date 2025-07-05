# config/settings.py
"""
Configuración principal del sistema WPC
Equivalente a la lectura de archivos INI en VB6
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class WPCSettings:
    """
    Configuración centralizada del sistema WPC
    Reemplaza la lectura de Init.ini del sistema VB6
    """
    
    # Rutas del proyecto
    BASE_DIR = Path(__file__).parent.parent
    CONFIG_DIR = BASE_DIR / "config"
    LOGS_DIR = BASE_DIR / "logs"
    TEMP_DIR = BASE_DIR / "temp"
    
    # Base de datos SQL Server
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_SERVER = os.getenv("DB_SERVER", "localhost\\SQLEXPRESS") 
    DB_DATABASE = os.getenv("DB_DATABASE", "videoman")
    DB_TRUSTED_CONNECTION = os.getenv("DB_TRUSTED_CONNECTION", "yes").lower() == "yes"
    DB_USERNAME = os.getenv("DB_USERNAME", "")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    
    # Comunicación serie RS485
    SERIAL_PORT = os.getenv("SERIAL_PORT", "COM1")
    SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "9600"))
    SERIAL_TIMEOUT = float(os.getenv("SERIAL_TIMEOUT", "2.0"))
    SERIAL_RTS_CONTROL = True  # Para RS485
    
    # Polling de módulos
    POLLING_INTERVAL = int(os.getenv("POLLING_INTERVAL", "1000"))  # milisegundos
    MAX_RETRIES = 3
    RETRY_DELAY = 500  # milisegundos
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOGS_DIR / "wpc.log"
    LOG_MAX_SIZE = "10 MB"
    LOG_RETENTION = "30 days"
    
    # Cámaras
    CAMERA_DEFAULT_USER = os.getenv("CAMERA_DEFAULT_USER", "admin")
    CAMERA_DEFAULT_PASSWORD = os.getenv("CAMERA_DEFAULT_PASSWORD", "")
    CAMERA_TIMEOUT = int(os.getenv("CAMERA_TIMEOUT", "10"))
    CAMERA_TEMP_DIR = TEMP_DIR / "camera_images"
    
    # Interfaz gráfica
    UI_THEME = os.getenv("UI_THEME", "dark")
    UI_LANGUAGE = os.getenv("UI_LANGUAGE", "es")
    
    # Desarrollo y debug
    DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"
    
    @classmethod
    def ensure_directories(cls):
        """Crear directorios necesarios si no existen"""
        for directory in [cls.LOGS_DIR, cls.TEMP_DIR, cls.CAMERA_TEMP_DIR]:
            directory.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_database_url(cls) -> str:
        """
        Construir URL de conexión a SQL Server
        Equivalente a la función en Entorno.cls de VB6
        """
        if cls.DB_TRUSTED_CONNECTION:
            connection_string = (
                f"Driver={{{cls.DB_DRIVER}}};"
                f"Server={cls.DB_SERVER};"
                f"Database={cls.DB_DATABASE};"
                f"Trusted_Connection=yes;"
            )
        else:
            connection_string = (
                f"Driver={{{cls.DB_DRIVER}}};"
                f"Server={cls.DB_SERVER};"
                f"Database={cls.DB_DATABASE};"
                f"UID={cls.DB_USERNAME};"
                f"PWD={cls.DB_PASSWORD};"
            )
        
        return f"mssql+pyodbc:///?odbc_connect={connection_string}"
    
    @classmethod
    def validate_configuration(cls) -> list[str]:
        """
        Validar configuración y retornar lista de errores
        """
        errors = []
        
        # Validar base de datos
        if not cls.DB_SERVER:
            errors.append("DB_SERVER no configurado")
        if not cls.DB_DATABASE:
            errors.append("DB_DATABASE no configurado")
            
        # Validar comunicación serie
        if not cls.SERIAL_PORT:
            errors.append("SERIAL_PORT no configurado")
            
        # Validar directorios
        try:
            cls.ensure_directories()
        except Exception as e:
            errors.append(f"Error creando directorios: {e}")
            
        return errors

# Instancia global de configuración
settings = WPCSettings()