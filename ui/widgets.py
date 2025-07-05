# ui/widgets.py
"""
Widgets comunes reutilizables para la interfaz WPC
"""
from typing import Optional, Dict, List, Callable, Any
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QSpinBox, QCheckBox, QProgressBar, QFrame,
    QGroupBox, QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox, QDateTimeEdit,
    QTextEdit, QScrollArea, QSplitter, QTabWidget
)
from PyQt6.QtCore import (
    Qt, QTimer, pyqtSignal, QDateTime, QSize, QPropertyAnimation, QEasingCurve,
    QRect, QSequentialAnimationGroup, QParallelAnimationGroup
)
from PyQt6.QtGui import (
    QFont, QColor, QPalette, QPixmap, QIcon, QPainter, QPen, QBrush,
    QLinearGradient, QGradient
)

from core.modules.module_types import ModuleState, BarrierState, SensorState
from utils.logger import log_error

class StatusLED(QLabel):
    """
    LED de estado personalizado
    """
    
    def __init__(self, size: int = 16, parent=None):
        super().__init__(parent)
        
        self.led_size = size
        self.state_color = QColor(128, 128, 128)  # Gris por defecto
        self.is_blinking = False
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.toggle_blink)
        
        self.setFixedSize(size, size)
        self.update_appearance()
    
    def set_state(self, state: str, blinking: bool = False):
        """
        Establecer estado del LED
        
        Args:
            state: Estado ('online', 'offline', 'error', 'warning')
            blinking: Si debe parpadear
        """
        color_map = {
            'online': QColor(0, 255, 0),      # Verde
            'offline': QColor(128, 128, 128), # Gris
            'error': QColor(255, 0, 0),       # Rojo
            'warning': QColor(255, 165, 0),   # Naranja
            'active': QColor(0, 191, 255)     # Azul
        }
        
        self.state_color = color_map.get(state, QColor(128, 128, 128))
        self.is_blinking = blinking
        
        if blinking:
            self.blink_timer.start(500)  # Parpadear cada 500ms
        else:
            self.blink_timer.stop()
        
        self.update_appearance()
    
    def toggle_blink(self):
        """Alternar visibilidad para efecto de parpadeo"""
        self.setVisible(not self.isVisible())
    
    def update_appearance(self):
        """Actualizar apariencia visual del LED"""
        # Crear pixmap del LED
        pixmap = QPixmap(self.led_size, self.led_size)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Crear gradiente para efecto 3D
        gradient = QLinearGradient(0, 0, self.led_size, self.led_size)
        gradient.setColorAt(0, self.state_color.lighter(150))
        gradient.setColorAt(1, self.state_color.darker(150))
        
        # Dibujar círculo del LED
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(0, 0, 0), 1))
        painter.drawEllipse(1, 1, self.led_size - 2, self.led_size - 2)
        
        painter.end()
        
        self.setPixmap(pixmap)

class ConnectionStatusWidget(QFrame):
    """
    Widget de estado de conexión con indicadores múltiples
    """
    
    def __init__(self, title: str = "Estado de Conexión", parent=None):
        super().__init__(parent)
        
        self.title = title
        self.connections = {}  # Dict[str, StatusLED]
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: #f9f9f9;
            }
        """)
        
        layout = QVBoxLayout(self)
        
        # Título
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Contenedor de conexiones
        self.connections_layout = QGridLayout()
        layout.addLayout(self.connections_layout)
    
    def add_connection(self, name: str, label: str, initial_state: str = "offline"):
        """
        Agregar indicador de conexión
        
        Args:
            name: Nombre interno de la conexión
            label: Etiqueta a mostrar
            initial_state: Estado inicial
        """
        led = StatusLED(12)
        led.set_state(initial_state)
        
        label_widget = QLabel(label)
        label_widget.setFont(QFont("Arial", 8))
        
        row = len(self.connections)
        self.connections_layout.addWidget(led, row, 0)
        self.connections_layout.addWidget(label_widget, row, 1)
        
        self.connections[name] = led
    
    def update_connection_status(self, name: str, state: str, blinking: bool = False):
        """Actualizar estado de una conexión"""
        if name in self.connections:
            self.connections[name].set_state(state, blinking)

class ModuleStatusTable(QTableWidget):
    """
    Tabla de estado de módulos con actualización automática
    """
    
    module_selected = pyqtSignal(int)  # module_id
    module_double_clicked = pyqtSignal(int)  # module_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.module_data = {}  # Dict[int, dict] - module_id -> data
        
        self.setup_table()
        self.setup_connections()
    
    def setup_table(self):
        """Configurar estructura de la tabla"""
        headers = ["ID", "Nombre", "Dirección", "Estado", "Barrera", "Sensor", "Último OK", "Errores"]
        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)
        
        # Configurar columnas
        header = self.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nombre
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Estado
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Último OK
        
        # Configurar tabla
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
    
    def setup_connections(self):
        """Configurar conexiones de señales"""
        self.itemSelectionChanged.connect(self.on_selection_changed)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
    
    def add_module(self, module_id: int, module_data: dict):
        """Agregar módulo a la tabla"""
        self.module_data[module_id] = module_data
        self.update_table()
    
    def update_module_status(self, module_id: int, status_data: dict):
        """Actualizar estado de un módulo"""
        if module_id in self.module_data:
            self.module_data[module_id].update(status_data)
            self.update_table()
    
    def update_table(self):
        """Actualizar contenido de la tabla"""
        self.setRowCount(len(self.module_data))
        
        for row, (module_id, data) in enumerate(self.module_data.items()):
            # ID
            self.setItem(row, 0, QTableWidgetItem(str(module_id)))
            
            # Nombre
            name_item = QTableWidgetItem(data.get('name', f'Módulo {module_id}'))
            self.setItem(row, 1, name_item)
            
            # Dirección
            address_item = QTableWidgetItem(str(data.get('address', '--')))
            self.setItem(row, 2, address_item)
            
            # Estado con color
            state = data.get('state', ModuleState.OFFLINE)
            state_item = QTableWidgetItem(state.name if hasattr(state, 'name') else str(state))
            
            if state == ModuleState.ONLINE:
                state_item.setBackground(QColor(200, 255, 200))  # Verde claro
            elif state == ModuleState.ERROR:
                state_item.setBackground(QColor(255, 200, 200))  # Rojo claro
            else:
                state_item.setBackground(QColor(240, 240, 240))  # Gris claro
            
            self.setItem(row, 3, state_item)
            
            # Estado de barrera
            barrier_state = data.get('barrier_state', BarrierState.UNKNOWN)
            barrier_item = QTableWidgetItem(barrier_state.name if hasattr(barrier_state, 'name') else str(barrier_state))
            self.setItem(row, 4, barrier_item)
            
            # Estado de sensor
            sensor_state = data.get('sensor_state', SensorState.UNKNOWN)
            sensor_item = QTableWidgetItem(sensor_state.name if hasattr(sensor_state, 'name') else str(sensor_state))
            self.setItem(row, 5, sensor_item)
            
            # Última comunicación
            last_comm = data.get('last_communication', 'Nunca')
            if isinstance(last_comm, datetime):
                last_comm = last_comm.strftime("%H:%M:%S")
            last_comm_item = QTableWidgetItem(str(last_comm))
            self.setItem(row, 6, last_comm_item)
            
            # Errores consecutivos
            errors = data.get('consecutive_errors', 0)
            errors_item = QTableWidgetItem(str(errors))
            if errors > 0:
                errors_item.setBackground(QColor(255, 220, 220))  # Rojo muy claro
            self.setItem(row, 7, errors_item)
            
            # Guardar module_id en la fila
            self.item(row, 0).setData(Qt.ItemDataRole.UserRole, module_id)
    
    def on_selection_changed(self):
        """Manejar cambio de selección"""
        current_row = self.currentRow()
        if current_row >= 0:
            module_id_item = self.item(current_row, 0)
            if module_id_item:
                module_id = module_id_item.data(Qt.ItemDataRole.UserRole)
                self.module_selected.emit(module_id)
    
    def on_item_double_clicked(self, item):
        """Manejar doble clic en item"""
        row = item.row()
        module_id_item = self.item(row, 0)
        if module_id_item:
            module_id = module_id_item.data(Qt.ItemDataRole.UserRole)
            self.module_double_clicked.emit(module_id)

class EventLogViewer(QFrame):
    """
    Visor de log de eventos con filtros y búsqueda
    """
    
    def __init__(self, max_entries: int = 1000, parent=None):
        super().__init__(parent)
        
        self.max_entries = max_entries
        self.events = []  # Lista de eventos
        self.filtered_events = []  # Eventos filtrados
        
        self.setup_ui()
        self.setup_filters()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Controles superiores
        controls_layout = QHBoxLayout()
        
        # Filtro de nivel
        controls_layout.addWidget(QLabel("Nivel:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["Todos", "INFO", "WARNING", "ERROR", "SUCCESS"])
        controls_layout.addWidget(self.level_filter)
        
        # Filtro de texto
        controls_layout.addWidget(QLabel("Buscar:"))
        self.text_filter = QLineEdit()
        self.text_filter.setPlaceholderText("Filtrar eventos...")
        controls_layout.addWidget(self.text_filter)
        
        # Botón limpiar
        clear_button = QPushButton("Limpiar")
        clear_button.clicked.connect(self.clear_events)
        controls_layout.addWidget(clear_button)
        
        controls_layout.addStretch()
        
        # Contador de eventos
        self.event_counter = QLabel("Eventos: 0")
        controls_layout.addWidget(self.event_counter)
        
        layout.addLayout(controls_layout)
        
        # Lista de eventos
        self.event_list = QListWidget()
        self.event_list.setFont(QFont("Consolas", 9))
        self.event_list.setStyleSheet("""
            QListWidget {
                background-color: #f8f8f8;
                border: 1px solid #cccccc;
                alternate-background-color: #f0f0f0;
            }
            QListWidget::item {
                padding: 2px;
                border-bottom: 1px solid #eeeeee;
            }
        """)
        layout.addWidget(self.event_list)
    
    def setup_filters(self):
        """Configurar filtros automáticos"""
        self.level_filter.currentTextChanged.connect(self.apply_filters)
        self.text_filter.textChanged.connect(self.apply_filters)
    
    def add_event(self, level: str, message: str, timestamp: Optional[datetime] = None):
        """
        Agregar evento al log
        
        Args:
            level: Nivel del evento (INFO, WARNING, ERROR, SUCCESS)
            message: Mensaje del evento
            timestamp: Timestamp (usar actual si no se especifica)
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        event = {
            'level': level,
            'message': message,
            'timestamp': timestamp
        }
        
        self.events.append(event)
        
        # Limitar número de eventos
        if len(self.events) > self.max_entries:
            self.events = self.events[-self.max_entries:]
        
        self.apply_filters()
    
    def apply_filters(self):
        """Aplicar filtros activos"""
        level_filter = self.level_filter.currentText()
        text_filter = self.text_filter.text().lower()
        
        # Filtrar eventos
        self.filtered_events = []
        
        for event in self.events:
            # Filtro de nivel
            if level_filter != "Todos" and event['level'] != level_filter:
                continue
            
            # Filtro de texto
            if text_filter and text_filter not in event['message'].lower():
                continue
            
            self.filtered_events.append(event)
        
        self.update_display()
    
    def update_display(self):
        """Actualizar visualización de eventos"""
        self.event_list.clear()
        
        for event in self.filtered_events:
            timestamp_str = event['timestamp'].strftime("%H:%M:%S")
            level = event['level']
            message = event['message']
            
            # Formatear texto
            item_text = f"[{timestamp_str}] {level}: {message}"
            
            item = QListWidgetItem(item_text)
            
            # Color según nivel
            color_map = {
                'INFO': QColor(0, 0, 0),
                'WARNING': QColor(255, 140, 0),
                'ERROR': QColor(255, 0, 0),
                'SUCCESS': QColor(0, 128, 0)
            }
            
            if level in color_map:
                item.setForeground(color_map[level])
            
            self.event_list.addItem(item)
        
        # Actualizar contador
        self.event_counter.setText(f"Eventos: {len(self.filtered_events)}/{len(self.events)}")
        
        # Scroll al final
        self.event_list.scrollToBottom()
    
    def clear_events(self):
        """Limpiar todos los eventos"""
        self.events.clear()
        self.filtered_events.clear()
        self.update_display()

class ConfigurationDialog(QDialog):
    """
    Diálogo genérico de configuración
    """
    
    def __init__(self, title: str = "Configuración", parent=None):
        super().__init__(parent)
        
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(400, 300)
        
        self.config_items = {}  # Dict[str, QWidget]
        
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Área de configuración scrolleable
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        
        self.config_widget = QWidget()
        self.config_layout = QGridLayout(self.config_widget)
        
        scroll_area.setWidget(self.config_widget)
        layout.addWidget(scroll_area)
        
        # Botones
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def add_string_setting(self, key: str, label: str, default_value: str = ""):
        """Agregar configuración de texto"""
        row = len(self.config_items)
        
        label_widget = QLabel(f"{label}:")
        line_edit = QLineEdit(default_value)
        
        self.config_layout.addWidget(label_widget, row, 0)
        self.config_layout.addWidget(line_edit, row, 1)
        
        self.config_items[key] = line_edit
    
    def add_integer_setting(self, key: str, label: str, default_value: int = 0, 
                           min_value: int = 0, max_value: int = 999999):
        """Agregar configuración numérica"""
        row = len(self.config_items)
        
        label_widget = QLabel(f"{label}:")
        spin_box = QSpinBox()
        spin_box.setRange(min_value, max_value)
        spin_box.setValue(default_value)
        
        self.config_layout.addWidget(label_widget, row, 0)
        self.config_layout.addWidget(spin_box, row, 1)
        
        self.config_items[key] = spin_box
    
    def add_boolean_setting(self, key: str, label: str, default_value: bool = False):
        """Agregar configuración booleana"""
        row = len(self.config_items)
        
        checkbox = QCheckBox(label)
        checkbox.setChecked(default_value)
        
        self.config_layout.addWidget(checkbox, row, 0, 1, 2)
        
        self.config_items[key] = checkbox
    
    def add_choice_setting(self, key: str, label: str, choices: List[str], default_index: int = 0):
        """Agregar configuración de selección"""
        row = len(self.config_items)
        
        label_widget = QLabel(f"{label}:")
        combo_box = QComboBox()
        combo_box.addItems(choices)
        combo_box.setCurrentIndex(default_index)
        
        self.config_layout.addWidget(label_widget, row, 0)
        self.config_layout.addWidget(combo_box, row, 1)
        
        self.config_items[key] = combo_box
    
    def get_values(self) -> Dict[str, Any]:
        """Obtener valores de configuración"""
        values = {}
        
        for key, widget in self.config_items.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text()
            elif isinstance(widget, QSpinBox):
                values[key] = widget.value()
            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                values[key] = widget.currentText()
        
        return values
    
    def set_values(self, values: Dict[str, Any]):
        """Establecer valores de configuración"""
        for key, value in values.items():
            if key in self.config_items:
                widget = self.config_items[key]
                
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QCheckBox):
                    widget.setChecked(bool(value))
                elif isinstance(widget, QComboBox):
                    index = widget.findText(str(value))
                    if index >= 0:
                        widget.setCurrentIndex(index)

class ProgressIndicator(QFrame):
    """
    Indicador de progreso con animación
    """
    
    def __init__(self, text: str = "Procesando...", parent=None):
        super().__init__(parent)
        
        self.animation_group = None
        self.progress_dots = []
        
        self.setup_ui(text)
        self.setup_animation()
    
    def setup_ui(self, text: str):
        """Configurar interfaz"""
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                border: 1px solid #cccccc;
                border-radius: 5px;
                background-color: #f0f0f0;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout(self)
        
        # Texto
        self.text_label = QLabel(text)
        layout.addWidget(self.text_label)
        
        # Puntos animados
        for i in range(3):
            dot = QLabel("●")
            dot.setFont(QFont("Arial", 12))
            dot.setStyleSheet("color: #666666;")
            layout.addWidget(dot)
            self.progress_dots.append(dot)
        
        layout.addStretch()
    
    def setup_animation(self):
        """Configurar animación de puntos"""
        self.animation_group = QSequentialAnimationGroup()
        
        for i, dot in enumerate(self.progress_dots):
            # Animación de fade in/out para cada punto
            animation = QPropertyAnimation(dot, b"styleSheet")
            animation.setDuration(200)
            animation.setStartValue("color: #666666;")
            animation.setEndValue("color: #000000;")
            
            self.animation_group.addAnimation(animation)
        
        self.animation_group.setLoopCount(-1)  # Loop infinito
    
    def start_animation(self):
        """Iniciar animación"""
        if self.animation_group:
            self.animation_group.start()
    
    def stop_animation(self):
        """Detener animación"""
        if self.animation_group:
            self.animation_group.stop()
    
    def set_text(self, text: str):
        """Cambiar texto mostrado"""
        self.text_label.setText(text)

class StatisticsWidget(QGroupBox):
    """
    Widget de estadísticas con actualización automática
    """
    
    def __init__(self, title: str = "Estadísticas", parent=None):
        super().__init__(title, parent)
        
        self.statistics = {}  # Dict[str, Any]
        self.stat_labels = {}  # Dict[str, QLabel]
        
        self.setup_ui()
        
        # Timer para actualización automática
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(5000)  # Actualizar cada 5 segundos
    
    def setup_ui(self):
        """Configurar interfaz"""
        self.layout = QGridLayout(self)
    
    def add_statistic(self, key: str, label: str, initial_value: Any = 0, format_func: Optional[Callable] = None):
        """
        Agregar estadística
        
        Args:
            key: Clave interna
            label: Etiqueta a mostrar
            initial_value: Valor inicial
            format_func: Función para formatear el valor
        """
        row = len(self.stat_labels)
        
        label_widget = QLabel(f"{label}:")
        value_widget = QLabel(str(initial_value))
        value_widget.setStyleSheet("font-weight: bold;")
        
        self.layout.addWidget(label_widget, row, 0)
        self.layout.addWidget(value_widget, row, 1)
        
        self.stat_labels[key] = value_widget
        self.statistics[key] = {
            'value': initial_value,
            'format_func': format_func
        }
    
    def update_statistic(self, key: str, value: Any):
        """Actualizar valor de estadística"""
        if key in self.statistics:
            self.statistics[key]['value'] = value
            self.update_display()
    
    def update_display(self):
        """Actualizar visualización de estadísticas"""
        for key, stat_data in self.statistics.items():
            if key in self.stat_labels:
                value = stat_data['value']
                format_func = stat_data['format_func']
                
                if format_func:
                    formatted_value = format_func(value)
                else:
                    formatted_value = str(value)
                
                self.stat_labels[key].setText(formatted_value)

# Funciones de utilidad para crear widgets comunes
def create_module_status_widget(module_id: int, module_name: str) -> QFrame:
    """Crear widget de estado de módulo"""
    frame = QFrame()
    frame.setFrameStyle(QFrame.Shape.StyledPanel)
    layout = QVBoxLayout(frame)
    
    # Nombre
    name_label = QLabel(module_name)
    name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(name_label)
    
    # LEDs de estado
    leds_layout = QHBoxLayout()
    
    comm_led = StatusLED()
    comm_led.set_state('offline')
    leds_layout.addWidget(comm_led)
    
    barrier_led = StatusLED()
    barrier_led.set_state('offline')
    leds_layout.addWidget(barrier_led)
    
    layout.addLayout(leds_layout)
    
    return frame

def create_connection_status_panel() -> ConnectionStatusWidget:
    """Crear panel de estado de conexiones"""
    panel = ConnectionStatusWidget("Estado del Sistema")
    panel.add_connection('database', 'Base de Datos')
    panel.add_connection('serial', 'Puerto Serie')
    panel.add_connection('cameras', 'Cámaras')
    panel.add_connection('polling', 'Polling')
    return panel

def show_configuration_dialog(parent=None, title: str = "Configuración", 
                            settings: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """
    Mostrar diálogo de configuración genérico
    
    Args:
        parent: Widget padre
        title: Título del diálogo
        settings: Configuraciones existentes
        
    Returns:
        Diccionario con nuevas configuraciones o None si se canceló
    """
    dialog = ConfigurationDialog(title, parent)
    
    # Agregar configuraciones comunes
    dialog.add_string_setting('serial_port', 'Puerto Serie', 'COM1')
    dialog.add_integer_setting('baud_rate', 'Velocidad (baud)', 9600, 1200, 115200)
    dialog.add_integer_setting('polling_interval', 'Intervalo Polling (ms)', 1000, 100, 10000)
    dialog.add_boolean_setting('auto_start', 'Iniciar automáticamente', True)
    
    if settings:
        dialog.set_values(settings)
    
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.get_values()
    
    return None

# Función principal para testing de widgets
def main():
    """Función principal para testing independiente"""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Crear ventana de prueba
    window = QWidget()
    window.setWindowTitle("Test de Widgets WPC")
    window.resize(800, 600)
    
    layout = QVBoxLayout(window)
    
    # Probar diferentes widgets
    
    # Panel de conexiones
    conn_panel = create_connection_status_panel()
    conn_panel.update_connection_status('database', 'online')
    conn_panel.update_connection_status('serial', 'error', True)
    layout.addWidget(conn_panel)
    
    # Tabla de módulos
    module_table = ModuleStatusTable()
    module_table.add_module(1, {
        'name': 'Barrera Principal',
        'address': 1,
        'state': ModuleState.ONLINE,
        'barrier_state': BarrierState.CLOSED,
        'sensor_state': SensorState.FREE,
        'last_communication': datetime.now(),
        'consecutive_errors': 0
    })
    layout.addWidget(module_table)
    
    # Log de eventos
    event_log = EventLogViewer()
    event_log.add_event('INFO', 'Sistema iniciado')
    event_log.add_event('SUCCESS', 'Módulo 1 conectado')
    event_log.add_event('WARNING', 'Módulo 2 sin respuesta')
    event_log.add_event('ERROR', 'Error de comunicación')
    layout.addWidget(event_log)
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()