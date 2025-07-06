# ui/debug_window.py
"""
Ventana de debug de comunicación
Equivalente a ViewComm.frm en VB6
"""
from typing import Optional
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, 
    QCheckBox, QLabel, QGroupBox, QSpinBox, QComboBox, QLineEdit,
    QSplitter, QFrame, QGridLayout, QTabWidget, QWidget, QScrollArea
)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPalette

from core.communication.polling import PollingManager
from core.communication.protocol import ProtocolHandler
from utils.logger import log_error

class CommunicationMonitor(QThread):
    """
    Hilo separado para monitorear comunicación sin bloquear UI
    """
    message_received = pyqtSignal(str, str, str)  # timestamp, direction, data
    
    def __init__(self, polling_manager: PollingManager):
        super().__init__()
        self.polling_manager = polling_manager
        self.is_monitoring = True
        self.message_buffer = []
        
    def run(self):
        """Loop principal de monitoreo"""
        while self.is_monitoring:
            # Aquí interceptaríamos los mensajes de comunicación
            # En la implementación real se conectaría con eventos del polling
            self.msleep(100)
    
    def stop_monitoring(self):
        """Detener monitoreo"""
        self.is_monitoring = False
        self.wait()

class CommandTester(QGroupBox):
    """
    Widget para probar comandos manualmente
    """
    command_sent = pyqtSignal(str, str)  # address, command
    
    def __init__(self):
        super().__init__("Prueba de Comandos")
        self.protocol = ProtocolHandler()
        self.setup_ui()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QGridLayout(self)
        
        # Dirección del módulo
        layout.addWidget(QLabel("Dirección:"), 0, 0)
        self.address_spin = QSpinBox()
        self.address_spin.setRange(1, 99)
        self.address_spin.setValue(1)
        layout.addWidget(self.address_spin, 0, 1)
        
        # Tipo de comando
        layout.addWidget(QLabel("Comando:"), 1, 0)
        self.command_combo = QComboBox()
        self.command_combo.addItems([
            "S0 - Leer Estado",
            "K1 - Continuar Secuencia", 
            "K0 - Parar Secuencia",
            "T0 - Sincronizar Hora",
            "O1 - OK Download Novedad",
            "Personalizado"
        ])
        layout.addWidget(self.command_combo, 1, 1)
        
        # Comando personalizado
        layout.addWidget(QLabel("Comando personalizado:"), 2, 0)
        self.custom_command = QLineEdit()
        self.custom_command.setEnabled(False)
        layout.addWidget(self.custom_command, 2, 1)
        
        # Conectar evento de cambio
        self.command_combo.currentTextChanged.connect(self.on_command_changed)
        
        # Botón enviar
        self.send_button = QPushButton("Enviar Comando")
        self.send_button.clicked.connect(self.send_command)
        layout.addWidget(self.send_button, 3, 0, 1, 2)
        
        # Información del comando generado
        layout.addWidget(QLabel("Comando generado:"), 4, 0)
        self.generated_command = QLineEdit()
        self.generated_command.setReadOnly(True)
        self.generated_command.setFont(QFont("Consolas", 9))
        layout.addWidget(self.generated_command, 4, 1)
        
        # Actualizar comando inicial
        self.update_generated_command()
        
        # Conectar eventos para actualización automática
        self.address_spin.valueChanged.connect(self.update_generated_command)
        self.command_combo.currentIndexChanged.connect(self.update_generated_command)
        self.custom_command.textChanged.connect(self.update_generated_command)
    
    def on_command_changed(self, text: str):
        """Manejar cambio de tipo de comando"""
        is_custom = "Personalizado" in text
        self.custom_command.setEnabled(is_custom)
        self.update_generated_command()
    
    def update_generated_command(self):
        """Actualizar comando generado"""
        try:
            address = self.address_spin.value()
            command_text = self.command_combo.currentText()
            
            if "Personalizado" in command_text:
                custom = self.custom_command.text().upper()
                if custom:
                    command = self.protocol._build_command(address, custom)
                else:
                    command = ""
            elif "S0 - Leer Estado" in command_text:
                command = self.protocol.read_status(address)
            elif "K1 - Continuar" in command_text:
                command = self.protocol.continue_sequence(address)
            elif "K0 - Parar" in command_text:
                command = self.protocol.stop_sequence(address)
            elif "T0 - Sincronizar" in command_text:
                command = self.protocol.set_time(address)
            elif "O1 - OK Download" in command_text:
                command = self.protocol.ok_download_novelty(address)
            else:
                command = ""
            
            # Mostrar comando en formato legible
            if command:
                hex_command = " ".join(f"{ord(c):02X}" for c in command)
                self.generated_command.setText(hex_command)
            else:
                self.generated_command.setText("")
                
        except Exception as e:
            self.generated_command.setText(f"Error: {e}")
    
    def send_command(self):
        """Enviar comando"""
        try:
            address = self.address_spin.value()
            command = self.generated_command.text()
            
            if command and not command.startswith("Error"):
                self.command_sent.emit(str(address), command)
                
        except Exception as e:
            log_error(e, "CommandTester.send_command")

class CommunicationDebugWindow(QDialog):
    """
    Ventana de debug de comunicación serie
    Equivalente a ViewComm.frm en VB6
    """
    
    def __init__(self, polling_manager: Optional[PollingManager] = None, parent=None):
        super().__init__(parent)
        
        self.polling_manager = polling_manager
        self.protocol = ProtocolHandler()
        self.max_lines = 500
        self.auto_scroll = True
        self.is_monitoring = True
        self.line_count = 0
        
        # Monitor de comunicación en hilo separado
        self.comm_monitor = None
        if polling_manager:
            self.comm_monitor = CommunicationMonitor(polling_manager)
            self.comm_monitor.message_received.connect(self.add_communication_log)
        
        self.setup_ui()
        self.setup_monitoring()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        self.setWindowTitle("Debug de Comunicación WPC")
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Controles superiores
        controls_layout = self.create_controls_section()
        main_layout.addLayout(controls_layout)
        
        # Splitter principal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Panel izquierdo - Log de comunicación
        log_panel = self.create_log_panel()
        splitter.addWidget(log_panel)
        
        # Panel derecho - Herramientas
        tools_panel = self.create_tools_panel()
        splitter.addWidget(tools_panel)
        
        # Configurar proporciones
        splitter.setSizes([600, 400])
        
        # Botones inferiores
        buttons_layout = self.create_buttons_section()
        main_layout.addLayout(buttons_layout)
    
    def create_controls_section(self) -> QHBoxLayout:
        """Crear sección de controles"""
        layout = QHBoxLayout()
        
        # Checkbox para activar/desactivar monitoreo
        self.monitor_checkbox = QCheckBox("Ver Comunicación")
        self.monitor_checkbox.setChecked(True)
        self.monitor_checkbox.toggled.connect(self.toggle_monitoring)
        layout.addWidget(self.monitor_checkbox)
        
        # Checkbox para auto-scroll
        self.autoscroll_checkbox = QCheckBox("Auto-scroll")
        self.autoscroll_checkbox.setChecked(True)
        self.autoscroll_checkbox.toggled.connect(self.toggle_autoscroll)
        layout.addWidget(self.autoscroll_checkbox)
        
        # Límite de líneas
        layout.addWidget(QLabel("Máx. líneas:"))
        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(50, 2000)
        self.max_lines_spin.setValue(500)
        self.max_lines_spin.valueChanged.connect(self.set_max_lines)
        layout.addWidget(self.max_lines_spin)
        
        # Información de estado
        layout.addStretch()
        self.status_label = QLabel("Estado: Monitoreando")
        layout.addWidget(self.status_label)
        
        return layout
    
    def create_log_panel(self) -> QGroupBox:
        """Crear panel de log de comunicación"""
        panel = QGroupBox("Log de Comunicación")
        layout = QVBoxLayout(panel)
        
        # Área de texto para el log
        self.comm_log = QTextEdit()
        self.comm_log.setReadOnly(True)
        self.comm_log.setFont(QFont("Consolas", 9))
        
        # Estilo oscuro para el log
        self.comm_log.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #555555;
                selection-background-color: #264f78;
            }
        """)
        
        layout.addWidget(self.comm_log)
        
        # Controles del log
        log_controls = QHBoxLayout()
        
        clear_button = QPushButton("Limpiar")
        clear_button.clicked.connect(self.clear_log)
        log_controls.addWidget(clear_button)
        
        save_button = QPushButton("Guardar Log")
        save_button.clicked.connect(self.save_log)
        log_controls.addWidget(save_button)
        
        log_controls.addStretch()
        
        # Contador de líneas
        self.line_counter = QLabel("Líneas: 0")
        log_controls.addWidget(self.line_counter)
        
        layout.addLayout(log_controls)
        
        return panel
    
    def create_tools_panel(self) -> QTabWidget:
        """Crear panel de herramientas"""
        tabs = QTabWidget()
        
        # Tab 1: Prueba de comandos
        command_tester = CommandTester()
        command_tester.command_sent.connect(self.send_manual_command)
        tabs.addTab(command_tester, "Comandos")
        
        # Tab 2: Estadísticas
        stats_widget = self.create_statistics_widget()
        tabs.addTab(stats_widget, "Estadísticas")
        
        # Tab 3: Filtros
        filters_widget = self.create_filters_widget()
        tabs.addTab(filters_widget, "Filtros")
        
        return tabs
    
    def create_statistics_widget(self) -> QWidget:
        """Crear widget de estadísticas"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Estadísticas de comunicación
        stats_group = QGroupBox("Estadísticas de Comunicación")
        stats_layout = QGridLayout(stats_group)
        
        self.tx_count_label = QLabel("Comandos TX: 0")
        self.rx_count_label = QLabel("Respuestas RX: 0")
        self.errors_count_label = QLabel("Errores: 0")
        self.success_rate_label = QLabel("Tasa éxito: 100%")
        
        stats_layout.addWidget(self.tx_count_label, 0, 0)
        stats_layout.addWidget(self.rx_count_label, 0, 1)
        stats_layout.addWidget(self.errors_count_label, 1, 0)
        stats_layout.addWidget(self.success_rate_label, 1, 1)
        
        layout.addWidget(stats_group)
        
        # Estadísticas por módulo
        module_stats_group = QGroupBox("Estado por Módulo")
        module_layout = QVBoxLayout(module_stats_group)
        
        self.module_stats_text = QTextEdit()
        self.module_stats_text.setReadOnly(True)
        self.module_stats_text.setMaximumHeight(200)
        self.module_stats_text.setFont(QFont("Consolas", 9))
        module_layout.addWidget(self.module_stats_text)
        
        refresh_stats_button = QPushButton("Actualizar Estadísticas")
        refresh_stats_button.clicked.connect(self.update_statistics)
        module_layout.addWidget(refresh_stats_button)
        
        layout.addWidget(module_stats_group)
        layout.addStretch()
        
        return widget
    
    def create_filters_widget(self) -> QWidget:
        """Crear widget de filtros"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        filters_group = QGroupBox("Filtros de Visualización")
        filters_layout = QGridLayout(filters_group)
        
        # Checkboxes para tipos de mensaje
        self.show_tx_checkbox = QCheckBox("Mostrar TX (Comandos)")
        self.show_tx_checkbox.setChecked(True)
        filters_layout.addWidget(self.show_tx_checkbox, 0, 0)
        
        self.show_rx_checkbox = QCheckBox("Mostrar RX (Respuestas)")
        self.show_rx_checkbox.setChecked(True)
        filters_layout.addWidget(self.show_rx_checkbox, 0, 1)
        
        self.show_errors_checkbox = QCheckBox("Mostrar Errores")
        self.show_errors_checkbox.setChecked(True)
        filters_layout.addWidget(self.show_errors_checkbox, 1, 0)
        
        self.show_info_checkbox = QCheckBox("Mostrar Info")
        self.show_info_checkbox.setChecked(True)
        filters_layout.addWidget(self.show_info_checkbox, 1, 1)
        
        # Filtro por dirección
        filters_layout.addWidget(QLabel("Filtrar por dirección:"), 2, 0)
        self.address_filter = QComboBox()
        self.address_filter.addItem("Todas")
        for i in range(1, 100):
            self.address_filter.addItem(f"Dirección {i}")
        filters_layout.addWidget(self.address_filter, 2, 1)
        
        layout.addWidget(filters_group)
        layout.addStretch()
        
        return widget
    
    def create_buttons_section(self) -> QHBoxLayout:
        """Crear sección de botones inferiores"""
        layout = QHBoxLayout()
        
        # Botón de prueba de comunicación
        test_comm_button = QPushButton("Probar Comunicación")
        test_comm_button.clicked.connect(self.test_communication)
        layout.addWidget(test_comm_button)
        
        # Botón para abrir puerto
        self.port_button = QPushButton("Abrir Puerto")
        self.port_button.clicked.connect(self.toggle_port)
        layout.addWidget(self.port_button)
        
        layout.addStretch()
        
        # Botón cerrar
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        
        return layout
    
    def setup_monitoring(self):
        """Configurar monitoreo de comunicación"""
        # Timer para actualizar estadísticas periódicamente
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_statistics)
        self.stats_timer.start(5000)  # Cada 5 segundos
        
        # Inicializar contadores
        self.tx_count = 0
        self.rx_count = 0
        self.error_count = 0
        
        # Inicializar logs de ejemplo para testing
        self.add_communication_log("12:00:00", "INFO", "Sistema iniciado")
        self.add_communication_log("12:00:01", "INFO", "Puerto serie configurado")
        
        # Iniciar monitor si está disponible
        if self.comm_monitor:
            self.comm_monitor.start()
    
    def add_communication_log(self, timestamp: str, direction: str, data: str):
        """
        Agregar entrada al log de comunicación
        Equivalente a UpdateView en VB6
        """
        if not self.is_monitoring:
            return
        
        # Verificar filtros
        if not self.should_show_message(direction):
            return
        
        # Verificar límite de líneas (equivalente a nLines = 30 en VB6)
        if self.line_count >= self.max_lines:
            self.clear_log()
        
        # Formatear mensaje según el tipo
        color = self.get_message_color(direction)
        formatted_message = self.format_message(timestamp, direction, data, color)
        
        # Agregar al log
        self.comm_log.append(formatted_message)
        self.line_count += 1
        
        # Auto-scroll si está habilitado
        if self.auto_scroll:
            scrollbar = self.comm_log.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        # Actualizar contador
        self.line_counter.setText(f"Líneas: {self.line_count}")
        
        # Actualizar contadores por tipo
        if direction == "TX":
            self.tx_count += 1
        elif direction == "RX":
            self.rx_count += 1
        elif direction == "ERROR":
            self.error_count += 1
    
    def should_show_message(self, direction: str) -> bool:
        """Verificar si se debe mostrar el mensaje según filtros"""
        if direction == "TX" and not self.show_tx_checkbox.isChecked():
            return False
        if direction == "RX" and not self.show_rx_checkbox.isChecked():
            return False
        if direction == "ERROR" and not self.show_errors_checkbox.isChecked():
            return False
        if direction == "INFO" and not self.show_info_checkbox.isChecked():
            return False
        return True
    
    def get_message_color(self, direction: str) -> str:
        """Obtener color para el tipo de mensaje"""
        color_map = {
            "TX": "#00ff00",      # Verde para comandos enviados
            "RX": "#00aaff",      # Azul para respuestas recibidas
            "ERROR": "#ff4444",   # Rojo para errores
            "INFO": "#ffffff",    # Blanco para información
            "WARNING": "#ffaa00"  # Naranja para advertencias
        }
        return color_map.get(direction, "#ffffff")
    
    def format_message(self, timestamp: str, direction: str, data: str, color: str) -> str:
        """Formatear mensaje para el log"""
        # Convertir datos hexadecimales a formato legible si es necesario
        if direction in ["TX", "RX"] and " " in data:
            # Es comando hex, agregar interpretación
            interpretation = self.interpret_command(data, direction)
            if interpretation:
                data = f"{data} [{interpretation}]"
        
        return f'<span style="color: {color};">[{timestamp}] {direction}: {data}</span>'
    
    def interpret_command(self, hex_data: str, direction: str) -> str:
        """Interpretar comando hexadecimal"""
        try:
            # Convertir hex string a bytes
            hex_parts = hex_data.split()
            if len(hex_parts) < 4:
                return ""
            
            # Parsear componentes básicos
            if hex_parts[0] == "02":  # STX
                address = int(hex_parts[1] + hex_parts[2])
                command = hex_parts[3] + hex_parts[4]
                
                command_map = {
                    "5330": "Leer Estado",
                    "4B31": "Continuar Secuencia", 
                    "4B30": "Parar Secuencia",
                    "5430": "Sincronizar Hora",
                    "4F31": "OK Download Novedad"
                }
                
                cmd_name = command_map.get(command, f"Comando {command}")
                return f"Dir:{address} {cmd_name}"
                
        except:
            pass
        
        return ""
    
    def clear_log(self):
        """
        Limpiar el log
        Equivalente a ClearView_Click en VB6
        """
        self.comm_log.clear()
        self.line_count = 0
        self.line_counter.setText("Líneas: 0")
        self.add_communication_log(datetime.now().strftime("%H:%M:%S"), "INFO", "Log limpiado")
    
    def save_log(self):
        """Guardar log a archivo"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            
            filename, _ = QFileDialog.getSaveFileName(
                self, "Guardar Log", f"comm_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                "Archivos de texto (*.txt);;Todos los archivos (*.*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.comm_log.toPlainText())
                
                self.add_communication_log(
                    datetime.now().strftime("%H:%M:%S"), 
                    "INFO", 
                    f"Log guardado: {filename}"
                )
                
        except Exception as e:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"),
                "ERROR", 
                f"Error guardando log: {e}"
            )
    
    def toggle_monitoring(self, enabled: bool):
        """Activar/desactivar monitoreo"""
        self.is_monitoring = enabled
        self.status_label.setText("Estado: Monitoreando" if enabled else "Estado: Pausado")
        
        # Equivalent to Check1 in VB6
        if enabled:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"), 
                "INFO", 
                "Monitoreo activado"
            )
        else:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"), 
                "WARNING", 
                "Monitoreo pausado"
            )
    
    def toggle_autoscroll(self, enabled: bool):
        """Activar/desactivar auto-scroll"""
        self.auto_scroll = enabled
    
    def set_max_lines(self, value: int):
        """Establecer límite máximo de líneas"""
        self.max_lines = value
    
    def send_manual_command(self, address: str, command: str):
        """Enviar comando manual"""
        try:
            if self.polling_manager:
                # Convertir hex string a comando real
                hex_parts = command.split()
                cmd_bytes = bytes([int(h, 16) for h in hex_parts])
                cmd_string = cmd_bytes.decode('latin-1')
                
                # Enviar comando
                success = self.polling_manager.send_command(
                    int(address), cmd_string, immediate=True
                )
                
                # Log del comando enviado
                timestamp = datetime.now().strftime("%H:%M:%S")
                if success:
                    self.add_communication_log(timestamp, "TX", command)
                    self.add_communication_log(timestamp, "INFO", f"Comando enviado a dirección {address}")
                else:
                    self.add_communication_log(timestamp, "ERROR", f"Error enviando comando a dirección {address}")
            else:
                self.add_communication_log(
                    datetime.now().strftime("%H:%M:%S"),
                    "WARNING", 
                    "PollingManager no disponible"
                )
                
        except Exception as e:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"),
                "ERROR", 
                f"Error en comando manual: {e}"
            )
    
    def test_communication(self):
        """Probar comunicación básica"""
        self.add_communication_log(
            datetime.now().strftime("%H:%M:%S"),
            "INFO", 
            "Iniciando prueba de comunicación..."
        )
        
        # Simular prueba de comunicación
        if self.polling_manager:
            # Obtener estadísticas del polling
            stats = self.polling_manager.get_polling_statistics()
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"),
                "INFO", 
                f"Módulos online: {stats.get('online_modules', 0)}/{stats.get('total_modules', 0)}"
            )
        else:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"),
                "WARNING", 
                "Sistema de polling no disponible"
            )
    
    def toggle_port(self):
        """Abrir/cerrar puerto serie"""
        if self.polling_manager and self.polling_manager.serial_comm:
            if self.polling_manager.serial_comm.is_initialized:
                # Puerto abierto, cerrar
                self.port_button.setText("Abrir Puerto")
                self.add_communication_log(
                    datetime.now().strftime("%H:%M:%S"),
                    "WARNING", 
                    "Puerto serie cerrado"
                )
            else:
                # Puerto cerrado, abrir
                self.port_button.setText("Cerrar Puerto")
                self.add_communication_log(
                    datetime.now().strftime("%H:%M:%S"),
                    "SUCCESS", 
                    "Puerto serie abierto"
                )
        else:
            self.add_communication_log(
                datetime.now().strftime("%H:%M:%S"),
                "ERROR", 
                "Comunicación serie no disponible"
            )
    
    def update_statistics(self):
        """Actualizar estadísticas mostradas"""
        try:
            # Actualizar contadores básicos
            self.tx_count_label.setText(f"Comandos TX: {self.tx_count}")
            self.rx_count_label.setText(f"Respuestas RX: {self.rx_count}")
            self.errors_count_label.setText(f"Errores: {self.error_count}")
            
            # Calcular tasa de éxito
            total = self.tx_count + self.rx_count
            if total > 0:
                success_rate = ((total - self.error_count) / total) * 100
                self.success_rate_label.setText(f"Tasa éxito: {success_rate:.1f}%")
            
            # Actualizar estadísticas por módulo
            if self.polling_manager:
                stats_text = "Dirección | Estado | Última Com. | Errores\n"
                stats_text += "-" * 45 + "\n"
                
                modules_status = self.polling_manager.get_all_modules_status()
                for address, status in modules_status.items():
                    last_comm = status.last_communication or "Nunca"
                    if isinstance(last_comm, datetime):
                        last_comm = last_comm.strftime("%H:%M:%S")
                    
                    stats_text += f"{address:^9} | {status.state.name:^6} | {last_comm:^10} | {status.consecutive_errors:^6}\n"
                
                self.module_stats_text.setText(stats_text)
                
        except Exception as e:
            log_error(e, "update_statistics")
    
    def closeEvent(self, event):
        """Manejar cierre de la ventana"""
        # Detener monitor de comunicación
        if self.comm_monitor:
            self.comm_monitor.stop_monitoring()
        
        # Detener timers
        if hasattr(self, 'stats_timer'):
            self.stats_timer.stop()
        
        # Equivalent to setting MPolling.IsViewing = False in VB6
        self.add_communication_log(
            datetime.now().strftime("%H:%M:%S"),
            "INFO", 
            "Ventana de debug cerrada"
        )
        
        event.accept()

# Función de conveniencia para testing independiente
def main():
    """Función principal para testing independiente"""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Crear ventana de debug sin polling manager (modo demo)
    debug_window = CommunicationDebugWindow()
    debug_window.show()
    
    # Agregar algunos logs de ejemplo
    import time
    debug_window.add_communication_log("12:00:05", "TX", "02 01 53 30 03 4A")
    debug_window.add_communication_log("12:00:05", "RX", "02 01 53 30 30 30 30 30 03 56")
    debug_window.add_communication_log("12:00:06", "TX", "02 02 4B 31 03 4C") 
    debug_window.add_communication_log("12:00:06", "RX", "02 02 4B 31 03 4C")
    debug_window.add_communication_log("12:00:07", "ERROR", "Timeout esperando respuesta del módulo 3")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
    