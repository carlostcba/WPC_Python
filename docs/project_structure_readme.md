# 🏗️ Estructura del Proyecto WPC Python

## 📁 Organización de Directorios

```
wpc_python/
├── 📋 main.py                    # Punto de entrada principal
├── 📋 requirements.txt           # Dependencias Python
├── 📋 .env.template             # Plantilla configuración
├── 📋 .gitignore               # Control de versiones
│
├── 📁 config/                   # Configuración del sistema
│   ├── __init__.py
│   ├── settings.py             # Configuración principal
│   └── database.py             # Gestión base de datos
│
├── 📁 core/                     # Núcleo del sistema
│   ├── __init__.py
│   │
│   ├── 📁 communication/        # Comunicación RS485
│   │   ├── __init__.py
│   │   ├── protocol.py         # Protocolo de comunicación
│   │   ├── serial_comm.py      # Comunicación serie
│   │   └── polling.py          # Sistema de polling
│   │
│   ├── 📁 modules/             # Gestión de módulos
│   │   ├── __init__.py
│   │   ├── module_manager.py   # Gestor de módulos
│   │   └── module_types.py     # Tipos y estados
│   │
│   └── 📁 database/            # Modelos de datos
│       ├── __init__.py
│       ├── models.py           # Modelos SQLAlchemy
│       └── managers.py         # Gestores de negocio
│
├── 📁 ui/                      # Interfaz gráfica
│   ├── __init__.py
│   ├── main_window.py          # Ventana principal
│   ├── debug_window.py         # Debug comunicación
│   └── image_window.py         # Visualización imágenes
│
├── 📁 camera_integration/      # Sistema de cámaras
│   ├── __init__.py
│   ├── hikvision_manager.py    # Gestor Hikvision
│   ├── camera_config.py        # Configuración cámaras
│   └── image_processor.py      # Procesamiento imágenes
│
├── 📁 utils/                   # Utilidades
│   ├── __init__.py
│   ├── logger.py               # Sistema de logging
│   ├── id_generator.py         # Generador IDs únicos
│   └── helpers.py              # Funciones auxiliares
│
├── 📁 tests/                   # Pruebas unitarias
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_database.py
│   ├── test_communication.py
│   └── test_modules.py
│
├── 📁 logs/                    # Archivos de log
│   └── wpc.log
│
└── 📁 temp/                    # Archivos temporales
    └── camera_images/
```

## 🔄 Mapeo VB6 → Python

### Formularios (UI Layer)
| VB6 Original | Python Equivalente | Descripción |
|--------------|-------------------|-------------|
| `CACommMain.frm` | `ui/main_window.py` | Ventana principal del sistema |
| `ViewComm.frm` | `ui/debug_window.py` | Debug de comunicación serie |
| `FrmImg.frm` | `ui/image_window.py` | Visualización de imágenes |

### Módulos (Business Logic)
| VB6 Original | Python Equivalente | Descripción |
|--------------|-------------------|-------------|
| `MdlConnMain.bas` | `main.py` | Punto de entrada y control principal |
| `MPolling.bas` | `core/communication/polling.py` | Motor de encuestas a módulos |
| `mdlmensajes.bas` | `utils/logger.py` | Sistema de logging |

### Clases (Data Layer)
| VB6 Original | Python Equivalente | Descripción |
|--------------|-------------------|-------------|
| `Protocolo.cls` | `core/communication/protocol.py` | Protocolos de comunicación |
| `Comm.cls` | `core/communication/serial_comm.py` | Comunicación serie RS485 |
| `ClsMvt.cls` | `core/database/managers.py` | Gestión de movimientos |
| `TckSVR.cls` | `core/database/managers.py` | Gestión de tickets |
| `Entorno.cls` | `config/database.py` | Configuración entorno |

### Configuración
| VB6 Original | Python Equivalente | Descripción |
|--------------|-------------------|-------------|
| `Init.ini` | `.env` + `config/settings.py` | Configuración del sistema |
| Variables globales | `config/settings.py` | Configuración centralizada |

## 🎯 Componentes Clave Creados

### ✅ 1. Sistema de Configuración
- **`config/settings.py`**: Configuración centralizada usando variables de entorno
- **`config/database.py`**: Gestión de conexiones SQL Server con SQLAlchemy
- **`.env.template`**: Plantilla para configuración local

### ✅ 2. Punto de Entrada
- **`main.py`**: Aplicación principal con soporte GUI y consola
- Inicialización ordenada de componentes
- Manejo de errores y cierre limpio

### ✅ 3. Sistema de Logging
- **`utils/logger.py`**: Logging estructurado con rotación de archivos
- Compatibilidad con funciones VB6 (`Mensajes_Sistema`)
- Soporte para diferentes niveles y contextos

### ✅ 4. Generación de IDs
- **`utils/id_generator.py`**: Compatible con algoritmo VB6
- Mantiene formato original para compatibilidad
- Funciones de validación y parsing

### ✅ 5. Tipos de Módulos
- **`core/modules/module_types.py`**: Enums y clases para módulos
- Estados, tipos y configuraciones
- Validaciones de configuración

## 🔧 Tecnologías Utilizadas

### Base de Datos
- **SQLAlchemy 2.0+**: ORM moderno para SQL Server
- **pyodbc**: Driver nativo para SQL Server
- **Alembic**: Migraciones de base de datos

### Comunicación
- **pyserial**: Comunicación serie RS485
- **asyncio**: Operaciones asíncronas

### Interfaz Gráfica
- **PyQt6**: Framework GUI moderno (alternativa: PySide6)
- **OpenCV**: Procesamiento de imágenes de cámaras

### Utilidades
- **python-dotenv**: Gestión de variables de entorno
- **pydantic**: Validación de datos
- **loguru**: Logging avanzado

## 📋 Próximos Pasos

### 🎯 Paso 3: Modelos de Base de Datos
- [ ] Crear modelos SQLAlchemy principales (`mvt`, `mdl`, `idn`, `per`, `tck`)
- [ ] Implementar relaciones entre entidades
- [ ] Configurar migraciones con Alembic

### 🎯 Paso 4: Comunicación Serie
- [ ] Implementar protocolo de comunicación
- [ ] Crear gestor de polling a módulos
- [ ] Sistema de comandos y respuestas

### 🎯 Paso 5: Lógica de Negocio
- [ ] Gestores de movimientos y tickets
- [ ] Validaciones de acceso
- [ ] Integración con cámaras Hikvision

## 🚀 Instalación y Configuración

### 1. Clonar estructura
```bash
mkdir wpc_python
cd wpc_python
# Crear estructura de directorios
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Configurar entorno
```bash
cp .env.template .env
# Editar .env con configuración específica
```

### 4. Ejecutar aplicación
```bash
# Modo GUI (por defecto)
python main.py

# Modo consola
python main.py --console
```

## 📝 Notas de Migración

### Compatibilidad
- Los IDs generados son **100% compatibles** con el sistema VB6 existente
- La base de datos puede usarse **simultáneamente** con ambos sistemas
- El protocolo de comunicación **mantiene la misma estructura**

### Mejoras Implementadas
- **Logging estructurado** con rotación automática
- **Configuración centralizada** con validación
- **Manejo de errores robusto** con recuperación automática
- **Arquitectura modular** para facilitar mantenimiento
- **Soporte asíncrono** para mejor rendimiento