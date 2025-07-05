# main.py
"""
Punto de entrada principal del sistema WPC
Equivalente a MdlConnMain.bas en VB6
"""
import sys
import logging
from pathlib import Path
from typing import Optional

# Configurar path para imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from config.database import init_database, close_database
from utils.logger import setup_logging
from core.communication.polling import PollingManager
from core.modules.module_manager import ModuleManager

class WPCApplication:
    """
    Clase principal de la aplicación WPC
    Reemplaza las funciones de MdlConnMain.bas
    """
    
    def __init__(self):
        self.logger: Optional[logging.Logger] = None
        self.polling_manager: Optional[PollingManager] = None
        self.module_manager: Optional[ModuleManager] = None
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
            
            self.logger.info("Sistema WPC inicializado correctamente")
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error crítico durante inicialización: {e}")
            else:
                print(f"Error crítico durante inicialización: {e}")
            return False
    
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
                module_manager=self.module_manager
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
            
            # Loop principal
            try:
                while self._is_running:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                self.logger.info("Interrupción por usuario (Ctrl+C)")
            
            self.shutdown()
            return 0
            
        except Exception as e:
            self.logger.error(f"Error en modo consola: {e}")
            return 1
    
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
        
        # Cerrar base de datos
        close_database()
        
        if self.logger:
            self.logger.info("Sistema cerrado correctamente")

def main():
    """
    Función principal de entrada
    """
    app = WPCApplication()
    
    if not app.initialize():
        print("Error: No se pudo inicializar el sistema WPC")
        return 1
    
    # Verificar argumentos de línea de comandos
    if len(sys.argv) > 1 and sys.argv[1] == "--console":
        return app.start_console_mode()
    else:
        return app.start_gui_mode()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)