# ========================================
# ESTRUCTURA DEL PROYECTO WPC PYTHON
# ========================================

"""
wpc_python/
├── config/
│   ├── __init__.py
│   ├── settings.py          # Configuración general (equivalente a INI)
│   └── database.py          # Configuración SQL Server
├── core/
│   ├── __init__.py
│   ├── communication/
│   │   ├── __init__.py
│   │   ├── protocol.py      # Protocolo.cls (VB6)
│   │   ├── serial_comm.py   # Comm.cls (VB6)
│   │   └── polling.py       # MPolling.bas (VB6)
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── module_manager.py
│   │   └── module_types.py  # Constantes de tipos de módulos
│   └── database/
│       ├── __init__.py
│       ├── models.py        # Modelos SQLAlchemy
│       └── managers.py      # ClsMvt, TckSVR (VB6)
├── ui/
│   ├── __init__.py
│   ├── main_window.py       # CACommMain.frm (VB6)
│   ├── debug_window.py      # ViewComm.frm (VB6)
│   └── image_window.py      # FrmImg.frm (VB6)
├── camera_integration/
│   ├── __init__.py
│   ├── hikvision_manager.py # Reemplaza GeoSVR.cls
│   ├── camera_config.py     # Configuración cámaras
│   └── image_processor.py   # Procesamiento imágenes
├── utils/
│   ├── __init__.py
│   ├── logger.py           # mdlmensajes.bas (VB6)
│   ├── id_generator.py     # Generación de IDs únicos
│   └── helpers.py          # Funciones auxiliares
├── requirements.txt         # Dependencias Python
├── main.py                 # Punto de entrada (equivale a MdlConnMain.bas)
└── README.md               # Documentación del proyecto
"""

# ========================================
# DEPENDENCIAS PRINCIPALES
# ========================================

REQUIREMENTS = """
# Base de datos SQL Server
pyodbc>=4.0.39
sqlalchemy>=2.0.23
alembic>=1.12.1

# Comunicación serie RS485
pyserial>=3.5

# Interface gráfica
PyQt6>=6.6.0
# O alternativamente: PySide6>=6.6.0

# Integración cámaras Hikvision
requests>=2.31.0
opencv-python>=4.8.1.78

# Utilidades
python-dotenv>=1.0.0
asyncio-mqtt>=0.16.1
loguru>=0.7.2

# Testing y desarrollo
pytest>=7.4.3
pytest-asyncio>=0.21.1
black>=23.11.0
"""

# ========================================
# ARCHIVOS DE CONFIGURACIÓN
# ========================================

GITIGNORE = """
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Configuración local
.env
config/local_settings.py

# Logs
logs/
*.log

# Base de datos
*.db
*.sqlite3

# Cámaras - archivos temporales
temp_images/
camera_cache/
"""

ENV_TEMPLATE = """
# ========================================
# CONFIGURACIÓN DE ENTORNO - .env
# ========================================

# Base de datos SQL Server
DB_DRIVER=ODBC Driver 17 for SQL Server
DB_SERVER=localhost\\SQLEXPRESS
DB_DATABASE=videoman
DB_TRUSTED_CONNECTION=yes
DB_USERNAME=
DB_PASSWORD=

# Comunicación serie
SERIAL_PORT=COM1
SERIAL_BAUDRATE=9600
SERIAL_TIMEOUT=2.0

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/wpc.log

# Cámaras Hikvision
CAMERA_DEFAULT_USER=admin
CAMERA_DEFAULT_PASSWORD=
CAMERA_TIMEOUT=10

# Interfaz gráfica
UI_THEME=dark
UI_LANGUAGE=es

# Desarrollo
DEBUG_MODE=false
POLLING_INTERVAL=1000
"""