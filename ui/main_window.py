# ui/main_window.py
"""
Ventana principal del sistema WPC
Equivalente a CACommMain.frm en VB6
"""
import sys
import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QScrollArea, QTextEdit, QStatusBar,
    QMenuBar, QMenu, QMessageBox, QSplitter, QGroupBox, QApplication
)
from PyQt6.QtCore import (
    QTimer, QThread, pyqtSignal, Qt, QSize
)
from PyQt6.QtGui import (
    QPixmap, QIcon, QFont, QColor, QPalette, QAction
)

from core.communication.polling import PollingManager, ModuleStatus
from core.modules.module_manager import ModuleManager
from core.modules.module_types import ModuleState, BarrierState, SensorState
from core.database.managers import MovementManager, TicketManager
from config.settings import settings
from utils.logger import log_system, log_error
from camera_integration.hikvision_manager import HikvisionManager
from ui.widgets import StatusLED

class ModuleWidget(QFrame):
    """
    Widget que representa un módulo individual
    Equivalente a los controles de módulo en CACommMain.frm
    """
    
    # Señales para eventos
    module_clicked = pyqtSignal(int)  # module_id
    barrier_toggle_requested = pyqtSignal(int)  # module_id
    
    def __init__(self, module_id: int, module_name: str, address: int):
        super().__init__()
        
        self.module_id = module_id
        self.module_name = module_name
        self.address = address
        self.current_state = ModuleState.OFFLINE
        
        self.setup_ui()
        self.update_appearance()
    
    def setup_ui(self):
        """Configurar interfaz del widget"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setMinimumSize(120, 100)
        self.setMaximumSize(120, 100)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #555555;
                border-radius: 8px;
                background-color: #f0f0f0;
            }
            QFrame:hover {
                border-color: #0078d4;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(2)
        
        # Nombre del módulo
        self.name_label = QLabel(self.module_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        layout.addWidget(self.name_label)
        
        # Dirección
        self.address_label = QLabel(f"Addr: {self.address}")
        self.address_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.address_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.address_label)
        
        # Indicadores de estado
        indicators_layout = QHBoxLayout()
        
        # LED de comunicación
        self.comm_led = QLabel("●")
        self.comm_led.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.comm_led.setFont(QFont("Arial", 12))
        self.comm_led.setToolTip("Estado de comunicación")
        indicators_layout.addWidget(self.comm_led)
        
        # LED de barrera
        self.barrier_led = QLabel("■")
        self.barrier_led.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.barrier_led.setFont(QFont("Arial", 12))
        self.barrier_led.setToolTip("Estado de barrera")
        indicators_layout.addWidget(self.barrier_led)
        
        # LED de sensor
        self.sensor_led = QLabel("▲")
        self.sensor_led.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sensor_led.setFont(QFont("Arial", 12))
        self.sensor_led.setToolTip("Sensor DDMM")
        indicators_layout.addWidget(self.sensor_led)
        
        layout.addLayout(indicators_layout)
        
        # Estado textual
        self.status_label = QLabel("OFFLINE")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 8))
        layout.addWidget(self.status_label)
    
    def update_state(self, module_status: ModuleStatus):
        """
        Actualizar estado visual del módulo
        
        Args:
            module_status: Estado actual del módulo
        """
        self.current_state = module_status.state
        
        # Actualizar LEDs según estado
        if module_status.state == ModuleState.ONLINE:
            self.comm_led.setStyleSheet("color: #00ff00;")  # Verde
            self.status_label.setText("ONLINE")
            self.status_label.setStyleSheet("color: #008000;")
        elif module_status.state == ModuleState.ERROR:
            self.comm_led.setStyleSheet("color: #ff0000;")  # Rojo
            self.status_label.setText("ERROR")
            self.status_label.setStyleSheet("color: #ff0000;")
        else:
            self.comm_led.setStyleSheet("color: #808080;")  # Gris
            self.status_label.setText("OFFLINE")
            self.status_label.setStyleSheet("color: #808080;")
        
        # Estado de barrera
        if module_status.barrier_state == BarrierState.OPEN:
            self.barrier_led.setStyleSheet("color: #00ff00;")  # Verde - abierta
        elif module_status.barrier_state == BarrierState.CLOSED:
            self.barrier_led.setStyleSheet("color: #ff0000;")  # Rojo - cerrada
        else:
            self.barrier_led.setStyleSheet("color: #ffff00;")  # Amarillo - moviendo
        
        # Estado de sensor
        if module_status.sensor_ddmm == SensorState.OCCUPIED:
            self.sensor_led.setStyleSheet("color: #ff0000;")  # Rojo - ocupado
        else:
            self.sensor_led.setStyleSheet("color: #00ff00;")  # Verde - libre
        
        self.update_appearance()
    
    def update_appearance(self):
        """Actualizar apariencia general"""
        if self.current_state == ModuleState.ONLINE:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #00aa00;
                    border-radius: 8px;
                    background-color: #f0fff0;
                }
                QFrame:hover {
                    border-color: #0078d4;
                }
            """)
        elif self.current_state == ModuleState.ERROR:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #ff0000;
                    border-radius: 8px;
                    background-color: #fff0f0;
                }
                QFrame:hover {
                    border-color: #0078d4;
                }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    border: 2px solid #808080;
                    border-radius: 8px;
                    background-color: #f5f5f5;
                }
                QFrame:hover {
                    border-color: #0078d4;
                }
            """)
    
    def mousePressEvent(self, event):
        """Manejar clic en el módulo"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.module_clicked.emit(self.module_id)
        elif event.button() == Qt.MouseButton.RightButton:
            # Menú contextual para control manual
            self.barrier_toggle_requested.emit(self.module_id)
        super().mousePressEvent(event)

class SystemStatusWidget(QGroupBox):
    """
    Widget de estado del sistema
    Muestra estadísticas generales
    """
    
    def __init__(self):
        super().__init__("Estado del Sistema")
        self.setup_ui()
        
        # Timer para actualizar estadísticas
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_statistics)
        self.update_timer.start(2000)  # Cada 2 segundos
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QGridLayout(self)
        
        # Etiquetas de estadísticas
        self.total_modules_label = QLabel("Módulos totales: 0")
        self.online_modules_label = QLabel("Online: 0")
        self.offline_modules_label = QLabel("Offline: 0")
        self.comm_success_label = QLabel("Éxito com.: 0%")
        self.last_movement_label = QLabel("Último movimiento: --")
        self.active_tickets_label = QLabel("Tickets activos: 0")
        
        layout.addWidget(self.total_modules_label, 0, 0)
        layout.addWidget(self.online_modules_label, 0, 1)
        layout.addWidget(self.offline_modules_label, 1, 0)
        layout.addWidget(self.comm_success_label, 1, 1)
        layout.addWidget(self.last_movement_label, 2, 0, 1, 2)
        layout.addWidget(self.active_tickets_label, 3, 0, 1, 2)
    
    def update_statistics(self):
        """Actualizar estadísticas mostradas"""
        try:
            # Obtener estadísticas del sistema
            # TODO: Conectar con managers reales
            pass
        except Exception as e:
            log_error(e, "SystemStatusWidget.update_statistics")

class EventLogWidget(QGroupBox):
    """
    Widget de log de eventos en tiempo real
    Equivalente al área de mensajes en VB6
    """
    
    def __init__(self):
        super().__init__("Log de Eventos")
        self.setup_ui()
        self.max_lines = 100
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(200)
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        
        # Estilo del log
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
            }
        """)
        
        layout.addWidget(self.log_text)
        
        # Botones de control
        buttons_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("Limpiar")
        self.clear_button.clicked.connect(self.clear_log)
        
        self.pause_button = QPushButton("Pausar")
        self.pause_button.setCheckable(True)
        
        buttons_layout.addWidget(self.clear_button)
        buttons_layout.addWidget(self.pause_button)
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
    
    def add_log_entry(self, message: str, level: str = "INFO"):
        """
        Agregar entrada al log
        
        Args:
            message: Mensaje a mostrar
            level: Nivel del mensaje (INFO, WARNING, ERROR)
        """
        if self.pause_button.isChecked():
            return
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Color según nivel
        color_map = {
            "INFO": "#ffffff",
            "WARNING": "#ffaa00", 
            "ERROR": "#ff4444",
            "SUCCESS": "#44ff44"
        }
        color = color_map.get(level, "#ffffff")
        
        # Formatear mensaje
        formatted_message = f'<span style="color: {color}">[{timestamp}] {level}: {message}</span>'
        
        # Agregar al log
        self.log_text.append(formatted_message)
        
        # Limitar número de líneas
        lines = self.log_text.toPlainText().split('\n')
        if len(lines) > self.max_lines:
            # Remover líneas más antiguas
            self.log_text.clear()
            for line in lines[-self.max_lines:]:
                self.log_text.append(line)
        
        # Scroll al final
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def clear_log(self):
        """Limpiar el log"""
        self.log_text.clear()

class WPCMainWindow(QMainWindow):
    """
    Ventana principal del sistema WPC
    Equivalente a CACommMain.frm en VB6
    """
    
    def __init__(self, polling_manager: Optional[PollingManager] = None,
                 module_manager: Optional[ModuleManager] = None,
                 camera_manager: Optional['HikvisionManager'] = None):
        super().__init__()
        
        self.polling_manager = polling_manager
        self.module_manager = module_manager        
        self.camera_manager = camera_manager
        self.movement_manager = MovementManager()
        self.ticket_manager = TicketManager()
        
        # Widgets de módulos
        self.module_widgets: Dict[int, ModuleWidget] = {}
        
        # Configurar interfaz
        self.setup_ui()
        self.setup_menus()
        self.setup_status_bar()
        
        # Configurar conexiones con el sistema
        self.setup_connections()

        # Panel de estado de cámaras si el manager está disponible
        if self.camera_manager:
            self.setup_camera_status_panel()
        
        # Timer principal (equivalente al timer de VB6)
        self.main_timer = QTimer()
        self.main_timer.timeout.connect(self.update_ui)
        self.main_timer.start(1000)  # Cada segundo
        
        # Cargar módulos
        self.load_modules()
    
    def setup_ui(self):
        """Configurar interfaz principal"""
        self.setWindowTitle("WPC - Windows Park Control v2.0")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QVBoxLayout(central_widget)
        self.main_layout = main_layout
        
        # Splitter horizontal
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(h_splitter)
        
        # Panel izquierdo - Módulos
        modules_panel = self.create_modules_panel()
        h_splitter.addWidget(modules_panel)
        
        # Panel derecho - Información
        info_panel = self.create_info_panel()
        h_splitter.addWidget(info_panel)
        
        # Configurar proporciones del splitter
        h_splitter.setSizes([700, 300])
    
    def create_modules_panel(self) -> QWidget:
        """Crear panel de módulos"""
        panel = QGroupBox("Módulos del Sistema")
        layout = QVBoxLayout(panel)
        # Guardar para añadir widgets opcionales (p.ej. cámaras)
        self.info_layout = layout
        
        # Área scrolleable para módulos
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contenedor de módulos con grid layout
        self.modules_container = QWidget()
        self.modules_layout = QGridLayout(self.modules_container)
        self.modules_layout.setSpacing(10)
        
        scroll_area.setWidget(self.modules_container)
        layout.addWidget(scroll_area)
        
        return panel
    
    def create_info_panel(self) -> QWidget:
        """Crear panel de información"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Estado del sistema
        self.status_widget = SystemStatusWidget()
        layout.addWidget(self.status_widget)
        
        # Log de eventos
        self.log_widget = EventLogWidget()
        layout.addWidget(self.log_widget)
        
        return panel
    
    def setup_menus(self):
        """Configurar menús"""
        menubar = self.menuBar()
        
        # Menú Sistema
        system_menu = menubar.addMenu("&Sistema")
        
        start_action = QAction("&Iniciar Polling", self)
        start_action.triggered.connect(self.start_polling)
        system_menu.addAction(start_action)
        
        stop_action = QAction("&Detener Polling", self)
        stop_action.triggered.connect(self.stop_polling)
        system_menu.addAction(stop_action)
        
        system_menu.addSeparator()
        
        exit_action = QAction("&Salir", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        system_menu.addAction(exit_action)
        
        # Menú Herramientas
        tools_menu = menubar.addMenu("&Herramientas")
        
        debug_action = QAction("&Debug Comunicación", self)
        debug_action.triggered.connect(self.show_debug_window)
        tools_menu.addAction(debug_action)
        
        config_action = QAction("&Configuración", self)
        config_action.triggered.connect(self.show_config_dialog)
        tools_menu.addAction(config_action)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("&Ayuda")
        
        about_action = QAction("&Acerca de...", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def setup_status_bar(self):
        """Configurar barra de estado"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Indicadores en la barra de estado
        self.comm_status_label = QLabel("Puerto: Desconectado")
        self.polling_status_label = QLabel("Polling: Detenido")
        self.db_status_label = QLabel("BD: Desconectada")
        
        self.status_bar.addWidget(self.comm_status_label)
        self.status_bar.addPermanentWidget(self.polling_status_label)
        self.status_bar.addPermanentWidget(self.db_status_label)
    
    def setup_connections(self):
        """Configurar conexiones con el sistema de polling"""
        if self.polling_manager:
            # Suscribirse a eventos del polling
            self.polling_manager.subscribe_to_event('movement_detected', self.on_movement_detected)
            self.polling_manager.subscribe_to_event('module_state_changed', self.on_module_state_changed)
    
    def load_modules(self):
        """Cargar módulos desde la configuración"""
        if not self.module_manager:
            self.log_widget.add_log_entry("ModuleManager no disponible", "WARNING")
            return
        
        try:
            # Limpiar módulos existentes
            self.clear_modules()
            
            # Obtener configuración de módulos
            modules_config = self.module_manager.get_modules_for_polling()
            
            # Crear widgets para cada módulo
            row, col = 0, 0
            max_cols = 6  # Máximo 6 columnas
            
            for config in modules_config:
                module_widget = ModuleWidget(
                    config.module_id,
                    config.name,
                    config.address
                )
                
                # Conectar señales
                module_widget.module_clicked.connect(self.on_module_clicked)
                module_widget.barrier_toggle_requested.connect(self.on_barrier_toggle_requested)
                
                # Agregar al layout
                self.modules_layout.addWidget(module_widget, row, col)
                self.module_widgets[config.module_id] = module_widget
                
                # Avanzar posición
                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1
            
            self.log_widget.add_log_entry(f"Cargados {len(modules_config)} módulos", "SUCCESS")
            
        except Exception as e:
            log_error(e, "load_modules")
            self.log_widget.add_log_entry(f"Error cargando módulos: {e}", "ERROR")
    
    def clear_modules(self):
        """Limpiar widgets de módulos"""
        for widget in self.module_widgets.values():
            widget.deleteLater()
        self.module_widgets.clear()
    
    def update_ui(self):
        """Actualización periódica de la interfaz"""
        try:
            # Actualizar barra de estado
            self.update_status_bar()
            
            # Actualizar estado de módulos
            self.update_modules_status()

            # Actualizar estado de cámaras
            self.update_camera_status()
            
        except Exception as e:
            log_error(e, "update_ui")
    
    def update_status_bar(self):
        """Actualizar barra de estado"""
        # Estado de comunicación
        if self.polling_manager and self.polling_manager.serial_comm:
            if self.polling_manager.serial_comm.is_initialized:
                self.comm_status_label.setText(f"Puerto: {self.polling_manager.serial_comm.config.port} - Conectado")
            else:
                self.comm_status_label.setText("Puerto: Desconectado")
        
        # Estado de polling
        if self.polling_manager and self.polling_manager.is_running:
            self.polling_status_label.setText("Polling: Activo")
        else:
            self.polling_status_label.setText("Polling: Detenido")
        
        # Estado de BD
        self.db_status_label.setText("BD: Conectada")  # TODO: Verificar conexión real
    
    def update_modules_status(self):
        """Actualizar estado visual de todos los módulos"""
        if not self.polling_manager:
            return
        
        try:
            modules_status = self.polling_manager.get_all_modules_status()
            
            for address, module_status in modules_status.items():
                module_widget = None
                
                # Buscar widget por module_id
                for widget in self.module_widgets.values():
                    if widget.address == address:
                        module_widget = widget
                        break
                
                if module_widget:
                    module_widget.update_state(module_status)
                    
        except Exception as e:
            log_error(e, "update_modules_status")

    def setup_camera_status_panel(self):
        """Configurar panel de estado de cámaras"""
        try:
            camera_group = QGroupBox("Estado de Cámaras")
            camera_layout = QVBoxLayout()

            # Estadísticas generales
            self.camera_stats_label = QLabel("Inicializando...")
            camera_layout.addWidget(self.camera_stats_label)

            self.camera_leds = {}
            for module_id in self.camera_manager.module_cameras.keys():
                led_layout = QHBoxLayout()
                led = StatusLED()
                led.set_state('offline')
                self.camera_leds[module_id] = led

                label = QLabel(f"Módulo {module_id}")

                led_layout.addWidget(led)
                led_layout.addWidget(label)
                led_layout.addStretch()

                camera_layout.addLayout(led_layout)

            camera_group.setLayout(camera_layout)

            if hasattr(self, 'info_layout'):
                self.info_layout.addWidget(camera_group)
            elif hasattr(self, 'main_layout'):
                self.main_layout.addWidget(camera_group)

        except Exception as e:
            log_error(e, "setup_camera_status_panel")

    def update_camera_status(self):
        """Actualizar estado visual de cámaras"""
        try:
            if not self.camera_manager:
                return

            stats = self.camera_manager.get_system_statistics()
            stats_text = (
                f"Dispositivos: {stats.get('online_devices', 0)}/"
                f"{stats.get('total_devices', 0)} | "
                f"Cámaras: {stats.get('configured_cameras', 0)}"
            )
            self.camera_stats_label.setText(stats_text)

            for module_id, led in self.camera_leds.items():
                camera_config = self.camera_manager.module_cameras.get(module_id)
                if camera_config:
                    device_status = self.camera_manager.get_device_status(
                        camera_config.device_id
                    )
                    if device_status.get("status") == "online":
                        led.set_state('online')
                    else:
                        led.set_state('error', blinking=True)
                else:
                    led.set_state('offline')

        except Exception as e:
            log_error(e, "update_camera_status")

    def on_movement_detected_ui(self, movement_data: dict):
        """Manejador UI para eventos de movimiento con imágenes"""
        try:
            if movement_data.get('image_path'):
                self.show_movement_image(
                    movement_data.get('movement_id'),
                    movement_data['image_path']
                )
        except Exception as e:
            log_error(e, "on_movement_detected_ui")

    def show_movement_image(self, movement_id: int, image_path: str):
        """Mostrar imagen de movimiento en ventana flotante"""
        try:
            from ui.image_window import create_image_window

            image_window = create_image_window(
                window_type=2,
                movement_id=movement_id
            )

            if hasattr(image_window, 'image_loader'):
                movement_info = {
                    'movement_time': datetime.now(),
                    'module_name': f'Módulo {movement_id}',
                }
                image_window.image_loader.load_image(movement_id, image_path, movement_info)

            image_window.show()

            QTimer.singleShot(10000, image_window.close)

        except Exception as e:
            log_error(e, f"show_movement_image(movement_id={movement_id})")
    
    # Slots para eventos
    async def on_movement_detected(self, identification: str, module_status: ModuleStatus, person=None):
        """Manejar detección de movimiento"""
        person_name = person.full_name if person else "Desconocido"
        message = f"Movimiento detectado: {identification} ({person_name}) en {module_status.name}"
        self.log_widget.add_log_entry(message, "SUCCESS")
    
    async def on_module_state_changed(self, module_status: ModuleStatus):
        """Manejar cambio de estado de módulo"""
        message = f"Módulo {module_status.name}: {module_status.state.name}"
        level = "SUCCESS" if module_status.state == ModuleState.ONLINE else "WARNING"
        self.log_widget.add_log_entry(message, level)
    
    def on_module_clicked(self, module_id: int):
        """Manejar clic en módulo"""
        self.log_widget.add_log_entry(f"Módulo seleccionado: {module_id}", "INFO")
        # TODO: Mostrar detalles del módulo
    
    def on_barrier_toggle_requested(self, module_id: int):
        """Manejar solicitud de toggle de barrera"""
        if self.polling_manager:
            # Enviar comando de toggle
            module_widget = self.module_widgets.get(module_id)
            if module_widget:
                address = module_widget.address
                # TODO: Determinar si abrir o cerrar según estado actual
                from core.communication.protocol import ProtocolHandler
                protocol = ProtocolHandler()
                command = protocol.continue_sequence(address)
                
                success = self.polling_manager.send_command(address, command, immediate=True)
                if success:
                    self.log_widget.add_log_entry(f"Comando enviado a módulo {module_id}", "SUCCESS")
                else:
                    self.log_widget.add_log_entry(f"Error enviando comando a módulo {module_id}", "ERROR")
    
    # Acciones de menú
    def start_polling(self):
        """Iniciar polling"""
        if self.polling_manager:
            if not self.polling_manager.is_running:
                self.polling_manager.start()
                self.log_widget.add_log_entry("Polling iniciado", "SUCCESS")
            else:
                self.log_widget.add_log_entry("Polling ya está activo", "WARNING")
    
    def stop_polling(self):
        """Detener polling"""
        if self.polling_manager:
            if self.polling_manager.is_running:
                self.polling_manager.stop()
                self.log_widget.add_log_entry("Polling detenido", "WARNING")
            else:
                self.log_widget.add_log_entry("Polling ya está detenido", "INFO")
    
    def show_debug_window(self):
        """Mostrar ventana de debug"""
        try:
            from .debug_window import CommunicationDebugWindow
            self.debug_window = CommunicationDebugWindow(self.polling_manager)
            self.debug_window.show()
        except ImportError:
            self.log_widget.add_log_entry("Ventana de debug no disponible", "WARNING")
    
    def show_config_dialog(self):
        """Mostrar diálogo de configuración"""
        QMessageBox.information(self, "Configuración", "Diálogo de configuración no implementado aún")
    
    def show_about_dialog(self):
        """Mostrar diálogo acerca de"""
        QMessageBox.about(self, "Acerca de WPC",
                         "Windows Park Control v2.0\n"
                         "Sistema de control de acceso vehicular y peatonal\n"
                         "Migrado de VB6 a Python\n\n"
                         "© 2025 - Versión Python")
    
    def closeEvent(self, event):
        """Manejar cierre de la aplicación"""
        reply = QMessageBox.question(self, "Confirmar Salida",
                                    "¿Está seguro que desea salir del sistema?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            # Detener polling antes de cerrar
            if self.polling_manager and self.polling_manager.is_running:
                self.polling_manager.stop()
            
            self.log_widget.add_log_entry("Sistema cerrando...", "INFO")
            event.accept()
        else:
            event.ignore()