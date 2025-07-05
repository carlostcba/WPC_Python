# ui/__init__.py
"""
Módulo de interfaz gráfica WPC Python
Equivalente a los formularios VB6 del sistema original
"""

# Importaciones principales
from .main_window import WPCMainWindow, ModuleWidget, SystemStatusWidget, EventLogWidget
from .debug_window import CommunicationDebugWindow, CommandTester, CommunicationMonitor
from .image_window import WPCImageWindow, ImageDisplayWidget, create_image_window
from .widgets import (
    StatusLED, ConnectionStatusWidget, ModuleStatusTable, EventLogViewer,
    ConfigurationDialog, ProgressIndicator, StatisticsWidget,
    create_module_status_widget, create_connection_status_panel,
    show_configuration_dialog
)

# Información del módulo
__version__ = "2.0.0"
__author__ = "WPC Development Team"
__description__ = "Interfaz gráfica para Windows Park Control - Migración VB6 a Python"

# Mapa de equivalencias VB6 → Python
VB6_EQUIVALENTS = {
    "CACommMain.frm": "WPCMainWindow",
    "ViewComm.frm": "CommunicationDebugWindow", 
    "FrmImg.frm": "WPCImageWindow"
}

# Configuración por defecto para las ventanas
DEFAULT_WINDOW_CONFIG = {
    "main_window": {
        "title": "WPC - Windows Park Control v2.0",
        "min_size": (1000, 700),
        "default_size": (1200, 800)
    },
    "debug_window": {
        "title": "Debug de Comunicación WPC",
        "min_size": (800, 600),
        "default_size": (1000, 700)
    },
    "image_window": {
        "title": "WPC - Visualización de Imagen",
        "min_size": (400, 300),
        "default_size": (600, 500)
    }
}

# Estilos CSS globales para la aplicación
GLOBAL_STYLES = """
/* Estilo base para la aplicación WPC */
QMainWindow {
    background-color: #f0f0f0;
}

QGroupBox {
    font-weight: bold;
    border: 2px solid #cccccc;
    border-radius: 5px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

QPushButton {
    background-color: #e1e1e1;
    border: 1px solid #999999;
    border-radius: 3px;
    padding: 5px 15px;
    min-width: 80px;
}

QPushButton:hover {
    background-color: #e8e8e8;
    border-color: #0078d4;
}

QPushButton:pressed {
    background-color: #d0d0d0;
}

QPushButton:disabled {
    background-color: #f0f0f0;
    color: #999999;
    border-color: #cccccc;
}

QStatusBar {
    background-color: #e0e0e0;
    border-top: 1px solid #cccccc;
}

QTextEdit {
    border: 1px solid #cccccc;
    border-radius: 3px;
    background-color: white;
}

QLineEdit {
    border: 1px solid #cccccc;
    border-radius: 3px;
    padding: 3px;
    background-color: white;
}

QLineEdit:focus {
    border-color: #0078d4;
}

QComboBox {
    border: 1px solid #cccccc;
    border-radius: 3px;
    padding: 3px;
    background-color: white;
}

QTableWidget {
    gridline-color: #e0e0e0;
    background-color: white;
    alternate-background-color: #f8f8f8;
}

QTableWidget::item:selected {
    background-color: #0078d4;
    color: white;
}

QListWidget {
    border: 1px solid #cccccc;
    background-color: white;
    alternate-background-color: #f8f8f8;
}

QListWidget::item:selected {
    background-color: #0078d4;
    color: white;
}
"""

def apply_global_styles(app):
    """
    Aplicar estilos globales a la aplicación
    
    Args:
        app: Instancia de QApplication
    """
    app.setStyleSheet(GLOBAL_STYLES)

def create_main_application():
    """
    Crear aplicación principal con todas las ventanas
    
    Returns:
        Tupla (app, main_window)
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    
    # Crear aplicación
    app = QApplication(sys.argv)
    app.setApplicationName("WPC Python")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("WPC Development")
    
    # Aplicar estilos globales
    apply_global_styles(app)
    
    # Configurar atributos de alta resolución
    app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    
    # Crear ventana principal
    main_window = WPCMainWindow()
    
    # Configurar icono si existe
    try:
        icon = QIcon("resources/wpc_icon.ico")
        app.setWindowIcon(icon)
        main_window.setWindowIcon(icon)
    except:
        pass  # Icono no disponible
    
    return app, main_window

def show_debug_window_standalone():
    """
    Mostrar ventana de debug de forma independiente
    Útil para testing y desarrollo
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    apply_global_styles(app)
    
    debug_window = CommunicationDebugWindow()
    debug_window.show()
    
    return app.exec()

def show_image_window_standalone(window_type: int = 1):
    """
    Mostrar ventana de imagen de forma independiente
    
    Args:
        window_type: Tipo de ventana (1=principal, 2=evento, 3=alerta)
    """
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    apply_global_styles(app)
    
    image_window = WPCImageWindow(window_type)
    image_window.show()
    
    return app.exec()

def get_available_windows():
    """
    Obtener lista de ventanas disponibles
    
    Returns:
        Dict con información de ventanas disponibles
    """
    return {
        "main": {
            "class": WPCMainWindow,
            "description": "Ventana principal del sistema",
            "vb6_equivalent": "CACommMain.frm"
        },
        "debug": {
            "class": CommunicationDebugWindow,
            "description": "Debug de comunicación serie",
            "vb6_equivalent": "ViewComm.frm"
        },
        "image": {
            "class": WPCImageWindow,
            "description": "Visualización de imágenes",
            "vb6_equivalent": "FrmImg.frm"
        }
    }

def validate_ui_dependencies():
    """
    Validar que todas las dependencias de UI estén disponibles
    
    Returns:
        Tupla (success, missing_dependencies)
    """
    missing = []
    
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QIcon
    except ImportError as e:
        missing.append(f"PyQt6: {e}")
    
    try:
        from core.communication.polling import PollingManager
        from core.modules.module_manager import ModuleManager
    except ImportError as e:
        missing.append(f"Core modules: {e}")
    
    try:
        from camera_integration.hikvision_manager import HikvisionManager
    except ImportError as e:
        missing.append(f"Camera integration: {e}")
    
    return len(missing) == 0, missing

# Información de compatibilidad con VB6
COMPATIBILITY_INFO = {
    "converted_forms": 3,
    "total_vb6_forms": 3,
    "conversion_percentage": 100,
    "maintained_functionality": [
        "Visualización de estado de módulos",
        "Debug de comunicación serie", 
        "Monitoreo en tiempo real",
        "Control manual de dispositivos",
        "Visualización de imágenes",
        "Log de eventos",
        "Configuración del sistema"
    ],
    "improvements": [
        "Interfaz moderna con PyQt6",
        "Threading para operaciones no bloqueantes",
        "Mejor manejo de errores",
        "Widgets reutilizables",
        "Estilos CSS personalizables",
        "Mejor escalabilidad"
    ]
}

# Funciones de conveniencia para testing
def test_all_windows():
    """
    Función para probar todas las ventanas de forma independiente
    Útil durante desarrollo
    """
    import sys
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
    
    app = QApplication(sys.argv)
    apply_global_styles(app)
    
    # Ventana de testing
    test_window = QWidget()
    test_window.setWindowTitle("WPC UI Tests")
    test_window.resize(300, 200)
    
    layout = QVBoxLayout(test_window)
    
    # Botones para cada ventana
    main_btn = QPushButton("Ventana Principal")
    main_btn.clicked.connect(lambda: WPCMainWindow().show())
    layout.addWidget(main_btn)
    
    debug_btn = QPushButton("Debug Comunicación")
    debug_btn.clicked.connect(lambda: CommunicationDebugWindow().show())
    layout.addWidget(debug_btn)
    
    image_btn = QPushButton("Ventana de Imagen")
    image_btn.clicked.connect(lambda: WPCImageWindow().show())
    layout.addWidget(image_btn)
    
    widgets_btn = QPushButton("Test de Widgets")
    widgets_btn.clicked.connect(test_widgets)
    layout.addWidget(widgets_btn)
    
    test_window.show()
    return app.exec()

def test_widgets():
    """Probar widgets individuales"""
    from PyQt6.QtWidgets import QWidget, QVBoxLayout
    from datetime import datetime
    
    # Crear ventana de prueba de widgets
    widget_test = QWidget()
    widget_test.setWindowTitle("Test de Widgets WPC")
    widget_test.resize(600, 400)
    
    layout = QVBoxLayout(widget_test)
    
    # Probar panel de conexiones
    conn_panel = create_connection_status_panel()
    conn_panel.update_connection_status('database', 'online')
    conn_panel.update_connection_status('serial', 'error', True)
    layout.addWidget(conn_panel)
    
    # Probar log de eventos
    event_log = EventLogViewer(max_entries=100)
    event_log.add_event('INFO', 'Prueba de evento INFO')
    event_log.add_event('SUCCESS', 'Prueba de evento SUCCESS')
    event_log.add_event('WARNING', 'Prueba de evento WARNING')
    event_log.add_event('ERROR', 'Prueba de evento ERROR')
    layout.addWidget(event_log)
    
    widget_test.show()

# Exportar símbolos principales
__all__ = [
    # Ventanas principales
    'WPCMainWindow',
    'CommunicationDebugWindow', 
    'WPCImageWindow',
    
    # Widgets reutilizables
    'StatusLED',
    'ConnectionStatusWidget',
    'ModuleStatusTable',
    'EventLogViewer',
    'ConfigurationDialog',
    'ProgressIndicator',
    'StatisticsWidget',
    
    # Funciones de utilidad
    'create_main_application',
    'apply_global_styles',
    'create_module_status_widget',
    'create_connection_status_panel',
    'show_configuration_dialog',
    'create_image_window',
    
    # Funciones de testing
    'show_debug_window_standalone',
    'show_image_window_standalone', 
    'test_all_windows',
    'test_widgets',
    
    # Información del módulo
    'VB6_EQUIVALENTS',
    'DEFAULT_WINDOW_CONFIG',
    'COMPATIBILITY_INFO',
    
    # Validación
    'validate_ui_dependencies',
    'get_available_windows'
]

# Log de inicialización del módulo
try:
    from utils.logger import log_system
    log_system("Módulo UI inicializado correctamente")
    
    # Validar dependencias
    success, missing = validate_ui_dependencies()
    if success:
        log_system("Todas las dependencias de UI están disponibles")
    else:
        log_system(f"Dependencias faltantes: {missing}")
        
except ImportError:
    print("Módulo UI inicializado (logger no disponible)")

# Mensaje de estado
print(f"""
🎮 MÓDULO UI WPC PYTHON v{__version__}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Ventanas implementadas: {COMPATIBILITY_INFO['converted_forms']}/{COMPATIBILITY_INFO['total_vb6_forms']}
✅ Compatibilidad VB6: {COMPATIBILITY_INFO['conversion_percentage']}%

📋 Equivalencias:
   CACommMain.frm  → WPCMainWindow
   ViewComm.frm    → CommunicationDebugWindow  
   FrmImg.frm      → WPCImageWindow

🚀 Para probar: python -m ui.test_all_windows
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")