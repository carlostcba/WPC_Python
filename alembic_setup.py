# alembic.ini
[alembic]
# Ruta al directorio de migraciones
script_location = migrations

# Plantilla para archivos de migración
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# Nivel de logging
level = INFO

# Configuración de conexión a BD
sqlalchemy.url = driver://user:pass@localhost/dbname

# Configuraciones adicionales
[post_write_hooks]

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S

# ================================================
# migrations/env.py
"""
Configuración del entorno Alembic para WPC
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Importar configuración y modelos de WPC
from config.settings import settings
from core.database.models import Base

# Configuración de Alembic
config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata para autogeneración
target_metadata = Base.metadata

def get_url():
    """
    Obtener URL de conexión desde configuración WPC
    """
    return settings.get_database_url()

def run_migrations_offline() -> None:
    """
    Ejecutar migraciones en modo offline
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """
    Ejecutar migraciones en modo online
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

# ================================================
# migrations/script.py.mako
"""
Plantilla para archivos de migración
"""
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}

# ================================================
# scripts/init_database.py
"""
Script para inicializar la base de datos WPC
"""
import sys
import os
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import init_database, db_manager, Base
from config.settings import settings
from utils.logger import setup_logging, log_system

def create_tables():
    """
    Crear todas las tablas definidas en los modelos
    """
    try:
        log_system("Iniciando creación de tablas...", "INFO")
        
        # Verificar conexión
        if not db_manager.test_connection():
            log_system("Error: No se puede conectar a la base de datos", "ERROR")
            return False
        
        # Crear tablas
        Base.metadata.create_all(bind=db_manager.engine)
        
        log_system("Tablas creadas exitosamente", "INFO")
        return True
        
    except Exception as e:
        log_system(f"Error creando tablas: {e}", "ERROR")
        return False

def verify_tables():
    """
    Verificar que las tablas principales existan
    """
    essential_tables = [
        'mvt', 'mdl', 'idn', 'per', 'tck', 'tckhst', 
        'peridn', 'gru', 'pergru', 'cat', 'catval'
    ]
    
    try:
        from sqlalchemy import inspect
        
        inspector = inspect(db_manager.engine)
        existing_tables = inspector.get_table_names()
        
        missing_tables = [table for table in essential_tables if table not in existing_tables]
        
        if missing_tables:
            log_system(f"Tablas faltantes: {', '.join(missing_tables)}", "WARNING")
            return False
        else:
            log_system("Todas las tablas esenciales están presentes", "INFO")
            return True
            
    except Exception as e:
        log_system(f"Error verificando tablas: {e}", "ERROR")
        return False

def main():
    """
    Función principal del script
    """
    print("=== Inicializador de Base de Datos WPC ===")
    
    # Configurar logging
    setup_logging()
    
    # Validar configuración
    config_errors = settings.validate_configuration()
    if config_errors:
        print("Errores de configuración:")
        for error in config_errors:
            print(f"  - {error}")
        return 1
    
    # Inicializar conexión
    if not init_database():
        print("Error: No se pudo conectar a la base de datos")
        return 1
    
    print(f"Conectado a: {settings.DB_SERVER}\\{settings.DB_DATABASE}")
    
    # Opción de usuario
    response = input("¿Crear/actualizar tablas? (s/N): ").strip().lower()
    
    if response in ['s', 'si', 'y', 'yes']:
        if create_tables():
            print("✓ Tablas creadas/actualizadas exitosamente")
            
            if verify_tables():
                print("✓ Verificación completada")
                return 0
            else:
                print("⚠ Verificación encontró problemas")
                return 1
        else:
            print("✗ Error en la creación de tablas")
            return 1
    else:
        print("Operación cancelada")
        return 0

if __name__ == "__main__":
    exit(main())

# ================================================
# scripts/test_models.py
"""
Script para probar los modelos y gestores
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.database import init_database
from core.database.managers import MovementManager, TicketManager, PersonManager
from core.database.models import Module, Person, Identification
from utils.logger import setup_logging

def test_movement_validation():
    """
    Probar validación de movimientos
    """
    print("\n=== Test: Validación de Movimientos ===")
    
    movement_manager = MovementManager()
    
    # Probar con identificación inexistente
    result = movement_manager.validate_identification("999999", 1)
    print(f"Identificación inexistente: {result.allowed} - {result.reason}")
    
    # TODO: Agregar datos de prueba para testear casos válidos

def test_ticket_operations():
    """
    Probar operaciones de tickets
    """
    print("\n=== Test: Operaciones de Tickets ===")
    
    ticket_manager = TicketManager()
    
    # Crear ticket de prueba
    success, ticket_number = ticket_manager.create_ticket(1)
    if success:
        print(f"✓ Ticket creado: {ticket_number}")
        
        # Validar ticket
        valid, info = ticket_manager.validate_ticket(ticket_number)
        if valid:
            print(f"✓ Ticket válido: {info}")
        else:
            print(f"✗ Error validando: {info}")
    else:
        print("✗ Error creando ticket")

def main():
    """
    Ejecutar todas las pruebas
    """
    print("=== Pruebas de Modelos WPC ===")
    
    # Configurar logging
    setup_logging()
    
    # Inicializar BD
    if not init_database():
        print("Error: No se pudo conectar a la base de datos")
        return 1
    
    print("✓ Conexión a base de datos establecida")
    
    # Ejecutar pruebas
    test_movement_validation()
    test_ticket_operations()
    
    print("\n=== Pruebas Completadas ===")
    return 0

if __name__ == "__main__":
    exit(main())