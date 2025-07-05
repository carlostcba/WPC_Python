# config/database.py
"""
Configuración y gestión de conexiones a SQL Server
Equivalente a Entorno.cls y Conexiones.cls en VB6
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Optional, Generator
import logging
from .settings import settings

logger = logging.getLogger(__name__)

# Base para modelos SQLAlchemy
Base = declarative_base()

class DatabaseManager:
    """
    Gestor de conexiones a la base de datos SQL Server
    Reemplaza las funciones de Entorno.cls en VB6
    """
    
    def __init__(self):
        self.engine: Optional[object] = None
        self.SessionLocal: Optional[sessionmaker] = None
        self._is_initialized = False
    
    def initialize(self) -> bool:
        """
        Inicializar conexión a base de datos
        Equivalente a InitBD() en VB6
        """
        try:
            # Configurar engine con pool de conexiones
            self.engine = create_engine(
                settings.get_database_url(),
                echo=settings.DEBUG_MODE,  # Log SQL queries en debug
                pool_pre_ping=True,       # Verificar conexiones antes de usar
                pool_recycle=3600,        # Renovar conexiones cada hora
                poolclass=QueuePool,
                pool_size=5,              # Número de conexiones en el pool
                max_overflow=10,          # Conexiones adicionales si es necesario
                pool_timeout=30,          # Timeout para obtener conexión
                isolation_level="READ_COMMITTED"
            )
            
            # Configurar sessionmaker
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            # Probar conexión
            if self.test_connection():
                self._is_initialized = True
                logger.info("Conexión a base de datos inicializada correctamente")
                return True
            else:
                logger.error("Error al probar conexión inicial")
                return False
                
        except Exception as e:
            logger.error(f"Error inicializando base de datos: {e}")
            return False
    
    def test_connection(self) -> bool:
        """
        Probar conexión a base de datos
        Equivalente a las validaciones en VB6
        """
        if not self.engine:
            return False
            
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Error probando conexión: {e}")
            return False
    
    def refresh_connection(self) -> bool:
        """
        Refrescar conexión (equivalente a Refresco_Conexion_MySql en VB6)
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1+1"))
                return result.fetchone()[0] == 2
        except Exception as e:
            logger.warning(f"Conexión perdida, reintentando: {e}")
            return self.initialize()
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager para obtener sesión de base de datos
        Manejo automático de commit/rollback
        """
        if not self._is_initialized:
            raise RuntimeError("DatabaseManager no inicializado")
            
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error en sesión de base de datos: {e}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """
        Obtener sesión síncrona (para uso directo)
        """
        if not self._is_initialized:
            raise RuntimeError("DatabaseManager no inicializado")
        return self.SessionLocal()
    
    def close(self):
        """
        Cerrar conexiones (equivalente a CloseBD en VB6)
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Conexiones de base de datos cerradas")

# Instancia global del gestor de base de datos
db_manager = DatabaseManager()

# Funciones de conveniencia
def get_db_session() -> Generator[Session, None, None]:
    """Función de conveniencia para obtener sesión"""
    with db_manager.get_session() as session:
        yield session

def init_database() -> bool:
    """Inicializar base de datos desde el módulo principal"""
    return db_manager.initialize()

def close_database():
    """Cerrar conexiones desde el módulo principal"""
    db_manager.close()