# main.py

"""
Punto de entrada principal del sistema WPC
Equivalente a MdlConnMain.bas en VB6
"""
import sys
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from config.database import init_database, close_database
from utils.logger import setup_logging, log_error
from core.communication.polling import PollingManager
from core.modules.module_manager import ModuleManager

# Importaciones para sistema de cámaras
try:
    from camera_integration.hikvision_manager import HikvisionManager
    from camera_integration.camera_config import CameraConfigurationManager
    from camera_integration.image_processor import ImageProcessor
    CAMERA_SUPPORT = True
except ImportError as e:
    CAMERA_SUPPORT = False
    print(f"Sistema de cámaras no disponible: {e}")


class WPCApplication:
    """
    Clase principal de la aplicación WPC
    Reemplaza las funciones de MdlConnMain.bas
    """
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.polling_manager: Optional[PollingManager] = None
        self.module_manager: Optional[ModuleManager] = None
        self.camera_manager: Optional['HikvisionManager'] = None
        self.image_processor: Optional['ImageProcessor'] = None
        self.camera_config: Optional['CameraConfigurationManager'] = None
        self._is_running = False
    
    def initialize(self) -> bool:
        """
        Inicializar todos los componentes del sistema
        Equivalente a la función Main() en VB6
        """
        try:
            # 1. Configurar logging
            self.logger = setup_logging()
            self.logger.info("=== Iniciando Sistema WPC ===")
            
            # 2. Validar configuración
            config_errors = settings.validate_configuration()
            if config_errors:
                self.logger.error("Errores de configuración:")
                for error in config_errors:
                    self.logger.error(f"  - {error}")
                return False
            
            # 3. Crear directorios necesarios
            settings.ensure_directories()
            
            # 4. Inicializar base de datos
            self.logger.info("Conectando a base de datos...")
            if not init_database():
                self.logger.error("Error al conectar con la base de datos")
                return False
            
            # 5. Inicializar gestor de módulos
            self.logger.info("Inicializando gestor de módulos...")
            self.module_manager = ModuleManager()
            if not self.module_manager.initialize():
                self.logger.error("Error inicializando gestor de módulos")
                return False
            
            # 6. Inicializar sistema de polling
            self.logger.info("Inicializando sistema de comunicación...")
            self.polling_manager = PollingManager(self.module_manager)
            if not self.polling_manager.initialize():
                self.logger.error("Error inicializando sistema de polling")
                return False
            
            # 7. Inicializar sistema de cámaras (opcional)
            if CAMERA_SUPPORT:
                self.logger.info("Inicializando sistema de cámaras Hikvision...")
                try:
                    self.camera_manager = HikvisionManager()
                    self.image_processor = ImageProcessor()
                    self.camera_config = CameraConfigurationManager()
                    
                    camera_success = self.camera_manager.initialize()
                    if camera_success:
                        self.logger.info("Sistema de cámaras inicializado correctamente")
                        
                        # Crear estructura de directorios
                        self.camera_config.create_directory_structure()
                        
                        # Probar cámaras configuradas
                        test_results = self.camera_manager.test_all_cameras()
                        working_cameras = sum(1 for result in test_results.values() if result)
                        self.logger.info(f"Cámaras funcionando: {working_cameras}/{len(test_results)}")
                        
                        # Suscribir eventos de movimiento para captura automática
                        self.polling_manager.subscribe_to_event('movement_detected', self._on_movement_detected)
                        
                    else:
                        self.logger.warning("Sistema de cámaras no disponible")
                        
                except Exception as e:
                    self.logger.warning(f"Error inicializando cámaras: {e}")
                    self.camera_manager = None
            else:
                self.logger.info("Sistema de cámaras no incluido en esta instalación")
            
            self.logger.info("Sistema WPC inicializado correctamente")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error crítico durante inicialización: {e}")
            else:
                print(f"Error crítico durante inicialización: {e}")
            return False
    
    async def _on_movement_detected(self, movement_data: dict):
        """
        Manejador de eventos de movimiento con captura automática
        """
        try:
            if not self.camera_manager or not self.camera_manager.initialized:
                return
            
            movement_id = movement_data.get('movement_id')
            module_id = movement_data.get('module_id')
            identification = movement_data.get('identification', '')
            
            if not all([movement_id, module_id]):
                return
            
            # Capturar foto automática
            success, image_path = self.camera_manager.capture_movement_photo(
                module_id, movement_id, identification
            )
            
            if success and image_path and self.image_processor:
                # Procesar imagen
                image_path_obj = Path(image_path)
                
                # Agregar marca de agua con información
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                watermark_text = f"WPC - {identification} - {timestamp}"
                self.image_processor.add_watermark(image_path_obj, watermark_text)
                
                # Crear thumbnail
                self.image_processor.create_thumbnail(image_path_obj)
                
                self.logger.info(f"Imagen capturada para movimiento {movement_id}: {image_path}")
                
                # Actualizar datos del evento para la UI
                movement_data['image_path'] = str(image_path)
                
        except Exception as e:
            log_error(e, f"_on_movement_detected(movement_id={movement_data.get('movement_id')})")
    
    def start_gui_mode(self):
        """
        Iniciar modo interfaz gráfica
        """
        try:
            from ui.main_window import WPCMainWindow
            from PyQt6.QtWidgets import QApplication
            
            self.logger.info("Iniciando interfaz gráfica...")
            
            app = QApplication(sys.argv)
            app.setApplicationName("WPC - Windows Park Control")
            app.setApplicationVersion("2.0.0")
            
            # Crear ventana principal
            main_window = WPCMainWindow(
                polling_manager=self.polling_manager,
                module_manager=self.module_manager,
                camera_manager=self.camera_manager  # Pasar manager de cámaras
            )
            
            main_window.show()
            
            # Iniciar polling
            self.polling_manager.start()
            self._is_running = True
            
            # Ejecutar loop de la aplicación
            exit_code = app.exec()
            
            self.shutdown()
            return exit_code
            
        except ImportError as e:
            self.logger.error(f"Error importando componentes GUI: {e}")
            self.logger.info("Ejecutando en modo consola...")
            return self.start_console_mode()
        except Exception as e:
            self.logger.error(f"Error en modo GUI: {e}")
            return 1
    
    def start_console_mode(self):
        """
        Iniciar modo consola (sin interfaz gráfica)
        """
        try:
            self.logger.info("Iniciando en modo consola...")
            
            # Iniciar polling
            self.polling_manager.start()
            self._is_running = True
            
            self.logger.info("Sistema funcionando. Presione Ctrl+C para salir.")
            
            # Mostrar estadísticas cada 30 segundos
            import time
            last_stats_time = time.time()
            
            # Loop principal
            try:
                while self._is_running:
                    time.sleep(1)
                    
                    # Mostrar estadísticas periódicamente
                    current_time = time.time()
                    if current_time - last_stats_time >= 30:  # Cada 30 segundos
                        self._show_console_stats()
                        last_stats_time = current_time
                        
            except KeyboardInterrupt:
                self.logger.info("Interrupción por usuario (Ctrl+C)")
            
            self.shutdown()
            return 0
            
        except Exception as e:
            self.logger.error(f"Error en modo consola: {e}")
            return 1
    
    def _show_console_stats(self):
        """
        Mostrar estadísticas en modo consola
        """
        try:
            if self.module_manager:
                stats = self.module_manager.get_system_statistics()
                online_modules = stats.get('online_modules', 0)
                total_modules = stats.get('total_modules', 0)
                
                print(f"\n--- Estadísticas WPC ---")
                print(f"Módulos online: {online_modules}/{total_modules}")
                print(f"Comunicación: {stats.get('communication_stats', {}).get('success_rate_percentage', 0):.1f}% éxito")
                
                if self.camera_manager:
                    camera_stats = self.camera_manager.get_system_statistics()
                    print(f"Cámaras online: {camera_stats.get('online_devices', 0)}/{camera_stats.get('total_devices', 0)}")
                
                print("-------------------------\n")
                
        except Exception as e:
            log_error(e, "_show_console_stats")
    
    def shutdown(self):
        """
        Cerrar sistema ordenadamente
        """
        if self.logger:
            self.logger.info("=== Cerrando Sistema WPC ===")
        
        self._is_running = False
        
        # Detener polling
        if self.polling_manager:
            self.polling_manager.stop()
        
        # Limpiar sistema de cámaras
        if self.camera_manager:
            self.camera_manager.cleanup()
        
        # Limpieza opcional de imágenes antiguas
        if self.camera_config:
            try:
                deleted_count = self.camera_config.cleanup_old_images()
                if deleted_count > 0 and self.logger:
                    self.logger.info(f"Limpiadas {deleted_count} imágenes antiguas")
            except Exception as e:
                log_error(e, "cleanup_old_images durante shutdown")
        
        # Cerrar base de datos
        close_database()
        
        if self.logger:
            self.logger.info("Sistema cerrado correctamente")
    
    def get_system_status(self) -> dict:
        """
        Obtener estado completo del sistema
        """
        status = {
            'running': self._is_running,
            'timestamp': datetime.now().isoformat()
        }
        
        if self.module_manager:
            status['modules'] = self.module_manager.get_system_statistics()
        
        if self.camera_manager and self.camera_manager.initialized:
            status['cameras'] = self.camera_manager.get_system_statistics()
        
        return status
    
    def restart_polling(self):
        """
        Reiniciar sistema de polling
        Equivalente a Reiniciar_Encuestas en VB6
        """
        try:
            if self.polling_manager:
                self.logger.info("Reiniciando sistema de polling...")
                self.polling_manager.stop()
                
                # Reinicializar
                if self.polling_manager.initialize():
                    self.polling_manager.start()
                    self.logger.info("Sistema de polling reiniciado correctamente")
                    return True
                else:
                    self.logger.error("Error reiniciando sistema de polling")
                    return False
            
            return False
            
        except Exception as e:
            log_error(e, "restart_polling")
            return False


def main():
    """
    Función principal de entrada
    """
    app = WPCApplication()
    
    if not app.initialize():
        print("Error: No se pudo inicializar el sistema WPC")
        return 1
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg == "--console":
            return app.start_console_mode()
        elif arg == "--test":
            # Modo de prueba - mostrar estado y salir
            status = app.get_system_status()
            print("=== Estado del Sistema WPC ===")
            for key, value in status.items():
                print(f"{key}: {value}")
            app.shutdown()
            return 0
        elif arg == "--help":
            print("WPC - Windows Park Control v2.0")
            print("Uso:")
            print("  python main.py           - Iniciar en modo GUI")
            print("  python main.py --console - Iniciar en modo consola")
            print("  python main.py --test    - Probar sistema y mostrar estado")
            print("  python main.py --help    - Mostrar esta ayuda")
            return 0
    
    # Modo GUI por defecto
    return app.start_gui_mode()


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"Error fatal en main: {e}")
        sys.exit(1)