# ui/image_window.py
"""
Ventana de visualización de imágenes
Equivalente a FrmImg.frm en VB6
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea, QGroupBox, QGridLayout,
    QSpacerItem, QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import (
    Qt, QSize, QTimer, pyqtSignal, QThread, QMutex, QMutexLocker
)
from PyQt6.QtGui import (
    QPixmap, QFont, QPainter, QPen, QColor, QBrush, QResizeEvent
)

from core.database.managers import MovementManager, PersonManager
from camera_integration.hikvision_manager import HikvisionManager
from utils.logger import log_error, log_system

class ImageLoader(QThread):
    """
    Hilo separado para cargar imágenes sin bloquear la UI
    """
    image_loaded = pyqtSignal(QPixmap, dict)  # pixmap, movement_info
    load_failed = pyqtSignal(str)  # error_message
    
    def __init__(self):
        super().__init__()
        self.movement_id = None
        self.image_path = None
        self.movement_info = {}
        self.mutex = QMutex()
    
    def load_image(self, movement_id: int, image_path: str, movement_info: dict):
        """Cargar imagen en hilo separado"""
        with QMutexLocker(self.mutex):
            self.movement_id = movement_id
            self.image_path = image_path
            self.movement_info = movement_info
        
        if not self.isRunning():
            self.start()
    
    def run(self):
        """Ejecutar carga de imagen"""
        try:
            with QMutexLocker(self.mutex):
                image_path = self.image_path
                movement_info = self.movement_info.copy()
            
            if image_path and os.path.exists(image_path):
                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    self.image_loaded.emit(pixmap, movement_info)
                else:
                    self.load_failed.emit(f"Error cargando imagen: {image_path}")
            else:
                self.load_failed.emit(f"Imagen no encontrada: {image_path}")
                
        except Exception as e:
            self.load_failed.emit(f"Error en carga de imagen: {e}")

class ImageDisplayWidget(QLabel):
    """
    Widget personalizado para mostrar imágenes con redimensionamiento automático
    """
    
    def __init__(self, window_type: int = 1):
        super().__init__()
        
        self.window_type = window_type  # Equivalente a TipoVentana en VB6
        self.original_pixmap: Optional[QPixmap] = None
        self.movement_info: Dict[str, Any] = {}
        
        # Configuración inicial
        self.setMinimumSize(320, 240)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #cccccc;
                background-color: #f0f0f0;
                qproperty-alignment: AlignCenter;
            }
        """)
        
        # Texto por defecto
        self.setText("Sin imagen")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def set_image(self, pixmap: QPixmap, movement_info: dict):
        """
        Establecer imagen a mostrar
        
        Args:
            pixmap: Imagen a mostrar
            movement_info: Información del movimiento asociado
        """
        self.original_pixmap = pixmap
        self.movement_info = movement_info
        self.update_displayed_image()
    
    def update_displayed_image(self):
        """Actualizar imagen mostrada con redimensionamiento"""
        if self.original_pixmap is None:
            return
        
        # Redimensionar manteniendo aspecto
        label_size = self.size()
        scaled_pixmap = self.original_pixmap.scaled(
            label_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        # Agregar información superpuesta si es necesario
        if self.movement_info and self.window_type in [2, 3]:
            scaled_pixmap = self.add_overlay_info(scaled_pixmap)
        
        self.setPixmap(scaled_pixmap)
    
    def add_overlay_info(self, pixmap: QPixmap) -> QPixmap:
        """
        Agregar información superpuesta a la imagen
        
        Args:
            pixmap: Imagen base
            
        Returns:
            Imagen con información superpuesta
        """
        # Crear copia para modificar
        overlay_pixmap = QPixmap(pixmap)
        painter = QPainter(overlay_pixmap)
        
        try:
            # Configurar fuente y color
            font = QFont("Arial", 12, QFont.Weight.Bold)
            painter.setFont(font)
            
            # Fondo semitransparente para el texto
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.setBrush(QBrush(QColor(0, 0, 0, 128)))
            
            # Información a mostrar
            info_lines = []
            if 'person_name' in self.movement_info:
                info_lines.append(f"Persona: {self.movement_info['person_name']}")
            if 'movement_time' in self.movement_info:
                info_lines.append(f"Hora: {self.movement_info['movement_time']}")
            if 'module_name' in self.movement_info:
                info_lines.append(f"Módulo: {self.movement_info['module_name']}")
            
            # Dibujar información
            y_offset = 25
            for line in info_lines:
                painter.drawText(10, y_offset, line)
                y_offset += 25
                
        finally:
            painter.end()
        
        return overlay_pixmap
    
    def clear_image(self):
        """Limpiar imagen mostrada"""
        self.original_pixmap = None
        self.movement_info = {}
        self.setText("Sin imagen")
        self.setPixmap(QPixmap())
    
    def resizeEvent(self, event: QResizeEvent):
        """Manejar redimensionamiento del widget"""
        super().resizeEvent(event)
        self.update_displayed_image()
    
    def mousePressEvent(self, event):
        """Manejar clic en la imagen"""
        if event.button() == Qt.MouseButton.LeftButton and self.original_pixmap:
            # Mostrar imagen en tamaño completo
            self.show_fullsize_image()
        super().mousePressEvent(event)
    
    def show_fullsize_image(self):
        """Mostrar imagen en tamaño completo en ventana separada"""
        if not self.original_pixmap:
            return
        
        try:
            # Crear ventana de imagen completa
            fullsize_window = ImageFullsizeWindow(self.original_pixmap, self.movement_info)
            fullsize_window.show()
            
        except Exception as e:
            log_error(e, "show_fullsize_image")

class ImageFullsizeWindow(QWidget):
    """
    Ventana para mostrar imagen en tamaño completo
    """
    
    def __init__(self, pixmap: QPixmap, movement_info: dict, parent=None):
        super().__init__(parent)
        
        self.original_pixmap = pixmap
        self.movement_info = movement_info
        
        self.setup_ui()
        self.setWindowTitle("Imagen - Tamaño Completo")
        
        # Configurar tamaño inicial
        self.resize(min(pixmap.width() + 50, 800), min(pixmap.height() + 100, 600))
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Información del movimiento
        if self.movement_info:
            info_group = QGroupBox("Información del Evento")
            info_layout = QGridLayout(info_group)
            
            row = 0
            for key, value in self.movement_info.items():
                label = QLabel(f"{key.replace('_', ' ').title()}:")
                value_label = QLabel(str(value))
                value_label.setStyleSheet("font-weight: bold;")
                
                info_layout.addWidget(label, row, 0)
                info_layout.addWidget(value_label, row, 1)
                row += 1
            
            layout.addWidget(info_group)
        
        # Scroll area para la imagen
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Widget de imagen
        image_label = QLabel()
        image_label.setPixmap(self.original_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scroll_area.setWidget(image_label)
        layout.addWidget(scroll_area)
        
        # Botones
        buttons_layout = QHBoxLayout()
        
        save_button = QPushButton("Guardar Como...")
        save_button.clicked.connect(self.save_image)
        buttons_layout.addWidget(save_button)
        
        buttons_layout.addStretch()
        
        close_button = QPushButton("Cerrar")
        close_button.clicked.connect(self.close)
        buttons_layout.addWidget(close_button)
        
        layout.addLayout(buttons_layout)
    
    def save_image(self):
        """Guardar imagen a archivo"""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Guardar Imagen", 
                f"imagen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg",
                "Imágenes JPEG (*.jpg);;Imágenes PNG (*.png);;Todos los archivos (*.*)"
            )
            
            if filename:
                success = self.original_pixmap.save(filename)
                if success:
                    QMessageBox.information(self, "Éxito", f"Imagen guardada: {filename}")
                else:
                    QMessageBox.warning(self, "Error", "No se pudo guardar la imagen")
                    
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error guardando imagen: {e}")

class WPCImageWindow(QWidget):
    """
    Ventana de visualización de imágenes del sistema WPC
    Equivalente a FrmImg.frm en VB6
    """
    
    # Señales
    window_closed = pyqtSignal(int)  # window_type
    
    def __init__(self, window_type: int = 1, parent=None):
        super().__init__(parent)
        
        self.window_type = window_type  # 1, 2, 3 como en VB6
        self.movement_manager = MovementManager()
        self.person_manager = PersonManager()
        self.hikvision_manager = None
        
        # Loader de imágenes en hilo separado
        self.image_loader = ImageLoader()
        self.image_loader.image_loaded.connect(self.on_image_loaded)
        self.image_loader.load_failed.connect(self.on_image_load_failed)
        
        # Timer para auto-cerrar ventana (como en VB6)
        self.auto_close_timer = QTimer()
        self.auto_close_timer.setSingleShot(True)
        self.auto_close_timer.timeout.connect(self.auto_close)
        
        self.setup_ui()
        self.setup_connections()
        
        # Configurar comportamiento por tipo de ventana
        self.configure_window_behavior()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        self.setWindowTitle(f"WPC - Visualización de Imagen {self.window_type}")
        self.setMinimumSize(400, 300)
        self.resize(600, 500)
        
        # Layout principal
        main_layout = QVBoxLayout(self)
        
        # Información del evento
        self.info_group = QGroupBox("Información del Evento")
        info_layout = QGridLayout(self.info_group)
        
        # Labels de información
        self.person_label = QLabel("Persona: --")
        self.time_label = QLabel("Hora: --") 
        self.module_label = QLabel("Módulo: --")
        self.direction_label = QLabel("Dirección: --")
        self.identification_label = QLabel("Identificación: --")
        
        info_layout.addWidget(self.person_label, 0, 0)
        info_layout.addWidget(self.time_label, 0, 1)
        info_layout.addWidget(self.module_label, 1, 0)
        info_layout.addWidget(self.direction_label, 1, 1)
        info_layout.addWidget(self.identification_label, 2, 0, 1, 2)
        
        main_layout.addWidget(self.info_group)
        
        # Widget de imagen principal
        self.image_widget = ImageDisplayWidget(self.window_type)
        main_layout.addWidget(self.image_widget)
        
        # Estado de carga
        self.status_label = QLabel("Listo")
        self.status_label.setStyleSheet("color: #666666; font-style: italic;")
        main_layout.addWidget(self.status_label)
        
        # Botones de control
        buttons_layout = QHBoxLayout()
        
        self.capture_button = QPushButton("Capturar Imagen")
        self.capture_button.clicked.connect(self.capture_current_image)
        buttons_layout.addWidget(self.capture_button)
        
        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.clicked.connect(self.refresh_image)
        buttons_layout.addWidget(self.refresh_button)
        
        buttons_layout.addStretch()
        
        self.close_button = QPushButton("Cerrar")
        self.close_button.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_button)
        
        main_layout.addLayout(buttons_layout)
    
    def setup_connections(self):
        """Configurar conexiones del sistema"""
        try:
            # Inicializar gestor de cámaras Hikvision si está disponible
            self.hikvision_manager = HikvisionManager()
            if self.hikvision_manager.is_available():
                log_system("Sistema de cámaras Hikvision disponible")
            else:
                log_system("Sistema de cámaras no disponible")
                self.capture_button.setEnabled(False)
                
        except Exception as e:
            log_error(e, "setup_connections")
            self.capture_button.setEnabled(False)
    
    def configure_window_behavior(self):
        """
        Configurar comportamiento específico por tipo de ventana
        Equivalente a la lógica de TipoVentana en VB6
        """
        if self.window_type == 1:
            # Ventana principal - sin auto-close
            self.setWindowTitle("WPC - Imagen Principal")
            
        elif self.window_type == 2:
            # Ventana secundaria - auto-close en 10 segundos
            self.setWindowTitle("WPC - Imagen Evento")
            self.auto_close_timer.start(10000)  # 10 segundos
            
        elif self.window_type == 3:
            # Ventana de alerta - auto-close en 5 segundos  
            self.setWindowTitle("WPC - Imagen Alerta")
            self.auto_close_timer.start(5000)  # 5 segundos
            self.setStyleSheet("""
                QGroupBox {
                    border: 2px solid red;
                    font-weight: bold;
                }
            """)
    
    def show_movement_image(self, movement_id: int):
        """
        Mostrar imagen asociada a un movimiento
        Función principal para mostrar imágenes de eventos
        
        Args:
            movement_id: ID del movimiento a mostrar
        """
        try:
            self.status_label.setText("Cargando información del evento...")
            
            # Obtener información del movimiento
            movement_info = self.movement_manager.get_movement_details(movement_id)
            
            if not movement_info:
                self.status_label.setText("Movimiento no encontrado")
                return
            
            # Actualizar información mostrada
            self.update_movement_info(movement_info)
            
            # Buscar imagen asociada
            image_path = self.get_movement_image_path(movement_id, movement_info)
            
            if image_path:
                self.status_label.setText("Cargando imagen...")
                # Cargar imagen en hilo separado
                self.image_loader.load_image(movement_id, image_path, movement_info)
            else:
                self.status_label.setText("Sin imagen disponible")
                self.image_widget.clear_image()
                
        except Exception as e:
            log_error(e, "show_movement_image")
            self.status_label.setText(f"Error: {e}")
    
    def update_movement_info(self, movement_info: dict):
        """Actualizar información del movimiento en la UI"""
        try:
            # Información de la persona
            person_name = movement_info.get('person_name', 'Desconocido')
            self.person_label.setText(f"Persona: {person_name}")
            
            # Hora del evento
            movement_time = movement_info.get('movement_time', '')
            if isinstance(movement_time, datetime):
                time_str = movement_time.strftime("%d/%m/%Y %H:%M:%S")
            else:
                time_str = str(movement_time)
            self.time_label.setText(f"Hora: {time_str}")
            
            # Módulo
            module_name = movement_info.get('module_name', '--')
            self.module_label.setText(f"Módulo: {module_name}")
            
            # Dirección
            direction = movement_info.get('direction', '--')
            self.direction_label.setText(f"Dirección: {direction}")
            
            # Identificación
            identification = movement_info.get('identification', '--')
            self.identification_label.setText(f"Identificación: {identification}")
            
        except Exception as e:
            log_error(e, "update_movement_info")
    
    def get_movement_image_path(self, movement_id: int, movement_info: dict) -> Optional[str]:
        """
        Obtener ruta de imagen para un movimiento
        
        Args:
            movement_id: ID del movimiento
            movement_info: Información del movimiento
            
        Returns:
            Ruta de la imagen o None si no existe
        """
        try:
            # Construir ruta basada en fecha y movimiento
            movement_time = movement_info.get('movement_time')
            if not movement_time:
                return None
            
            if isinstance(movement_time, datetime):
                date_str = movement_time.strftime("%Y%m%d")
                time_str = movement_time.strftime("%H%M%S")
            else:
                return None
            
            # Rutas posibles para buscar imagen
            possible_paths = [
                f"temp/camera_images/{date_str}/{movement_id}_{time_str}.jpg",
                f"temp/camera_images/{date_str}/mvt_{movement_id}.jpg",
                f"images/{date_str}/{movement_id}.jpg",
                f"images/movements/mvt_{movement_id}.jpg"
            ]
            
            # Buscar en las rutas posibles
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            
            return None
            
        except Exception as e:
            log_error(e, "get_movement_image_path")
            return None
    
    def capture_current_image(self):
        """Capturar imagen actual de cámara"""
        try:
            if not self.hikvision_manager or not self.hikvision_manager.is_available():
                QMessageBox.warning(self, "Aviso", "Sistema de cámaras no disponible")
                return
            
            self.status_label.setText("Capturando imagen...")
            self.capture_button.setEnabled(False)
            
            # Determinar cámara a usar (basado en configuración del módulo)
            camera_id = 1  # Por defecto
            
            # Capturar imagen
            success, image_path = self.hikvision_manager.capture_snapshot(camera_id)
            
            if success and image_path:
                # Cargar imagen capturada
                movement_info = {
                    'person_name': 'Captura Manual',
                    'movement_time': datetime.now(),
                    'module_name': 'Manual',
                    'direction': 'Captura',
                    'identification': '--'
                }
                
                self.image_loader.load_image(0, image_path, movement_info)
                self.update_movement_info(movement_info)
                
            else:
                QMessageBox.warning(self, "Error", "No se pudo capturar la imagen")
                self.status_label.setText("Error en captura")
                
        except Exception as e:
            log_error(e, "capture_current_image")
            QMessageBox.critical(self, "Error", f"Error capturando imagen: {e}")
            
        finally:
            self.capture_button.setEnabled(True)
    
    def refresh_image(self):
        """Actualizar imagen actual"""
        # Recargar la última imagen mostrada
        if hasattr(self, 'current_movement_id'):
            self.show_movement_image(self.current_movement_id)
        else:
            self.status_label.setText("No hay imagen para actualizar")
    
    def on_image_loaded(self, pixmap: QPixmap, movement_info: dict):
        """Manejar imagen cargada exitosamente"""
        self.image_widget.set_image(pixmap, movement_info)
        self.status_label.setText("Imagen cargada")
    
    def on_image_load_failed(self, error_message: str):
        """Manejar error en carga de imagen"""
        self.image_widget.clear_image()
        self.status_label.setText(error_message)
        log_error(Exception(error_message), "image_load_failed")
    
    def auto_close(self):
        """Auto-cerrar ventana (para tipos 2 y 3)"""
        self.close()
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        try:
            # Detener timer de auto-close
            self.auto_close_timer.stop()
            
            # Detener loader de imágenes
            if self.image_loader.isRunning():
                self.image_loader.terminate()
                self.image_loader.wait(3000)  # Esperar 3 segundos máximo
            
            # Emitir señal de cierre
            self.window_closed.emit(self.window_type)
            
            log_system(f"Ventana de imagen {self.window_type} cerrada")
            
        except Exception as e:
            log_error(e, "closeEvent")
        
        event.accept()

# Función de conveniencia para crear ventanas de imagen
def create_image_window(window_type: int = 1, movement_id: Optional[int] = None) -> WPCImageWindow:
    """
    Crear ventana de imagen
    
    Args:
        window_type: Tipo de ventana (1=principal, 2=evento, 3=alerta)
        movement_id: ID del movimiento a mostrar (opcional)
        
    Returns:
        Instancia de WPCImageWindow
    """
    window = WPCImageWindow(window_type)
    
    if movement_id is not None:
        window.show_movement_image(movement_id)
    
    return window

# Función principal para testing independiente
def main():
    """Función principal para testing independiente"""
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # Crear ventana de imagen de prueba
    window = WPCImageWindow(window_type=1)
    window.show()
    
    # Simular información de movimiento para testing
    test_movement_info = {
        'person_name': 'Juan Pérez',
        'movement_time': datetime.now(),
        'module_name': 'Barrera Principal',
        'direction': 'Entrada',
        'identification': '123456'
    }
    
    window.update_movement_info(test_movement_info)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()