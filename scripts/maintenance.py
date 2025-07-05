# scripts/maintenance.py - SCRIPT DE MANTENIMIENTO
# ========================================
"""
Script de mantenimiento para el sistema WPC
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from config.database import init_database, db_manager
from camera_integration.hikvision_manager import HikvisionManager
from camera_integration.camera_config import CameraConfigurationManager
from utils.logger import setup_logging, log_system
from utils.helpers import cleanup_temp_directory, get_system_info, format_file_size


class MaintenanceManager:
    """
    Gestor de tareas de mantenimiento
    """
    
    def __init__(self):
        self.camera_manager = None
        self.camera_config = None
    
    def run_full_maintenance(self) -> Dict[str, Any]:
        """
        Ejecutar mantenimiento completo
        
        Returns:
            Dict[str, Any]: Resultados del mantenimiento
        """
        results = {
            'start_time': datetime.now().isoformat(),
            'tasks': {},
            'errors': []
        }
        
        try:
            log_system("=== Iniciando Mantenimiento Completo ===", "INFO")
            
            # 1. Información del sistema
            results['tasks']['system_info'] = self._get_system_info()
            
            # 2. Limpieza de archivos temporales
            results['tasks']['cleanup_temp'] = self._cleanup_temporary_files()
            
            # 3. Limpieza de imágenes antiguas
            results['tasks']['cleanup_images'] = self._cleanup_old_images()
            
            # 4. Verificación de base de datos
            results['tasks']['database_check'] = self._check_database_health()
            
            # 5. Verificación de cámaras
            results['tasks']['camera_check'] = self._check_camera_system()
            
            # 6. Optimización de base de datos
            results['tasks']['database_optimization'] = self._optimize_database()
            
            # 7. Backup de configuración
            results['tasks']['config_backup'] = self._backup_configuration()
            
            results['end_time'] = datetime.now().isoformat()
            results['success'] = True
            
            log_system("=== Mantenimiento Completado ===", "INFO")
            
        except Exception as e:
            results['errors'].append(str(e))
            results['success'] = False
            log_system(f"Error durante mantenimiento: {e}", "ERROR")
        
        return results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Obtener información del sistema"""
        try:
            info = get_system_info()
            log_system(f"Sistema: {info.get('platform', 'Unknown')}", "INFO")
            return {'success': True, 'info': info}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _cleanup_temporary_files(self) -> Dict[str, Any]:
        """Limpiar archivos temporales"""
        try:
            temp_dirs = [
                settings.TEMP_DIR,
                settings.LOGS_DIR / 'old',
                Path('./temp')
            ]
            
            total_deleted = 0
            
            for temp_dir in temp_dirs:
                if temp_dir.exists():
                    deleted = cleanup_temp_directory(temp_dir, max_age_days=7)
                    total_deleted += deleted
            
            log_system(f"Archivos temporales eliminados: {total_deleted}", "INFO")
            return {'success': True, 'files_deleted': total_deleted}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _cleanup_old_images(self) -> Dict[str, Any]:
        """Limpiar imágenes antiguas"""
        try:
            if not self.camera_config:
                self.camera_config = CameraConfigurationManager()
            
            deleted_count = self.camera_config.cleanup_old_images()
            log_system(f"Imágenes antiguas eliminadas: {deleted_count}", "INFO")
            
            return {'success': True, 'images_deleted': deleted_count}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Verificar salud de base de datos"""
        try:
            if not init_database():
                return {'success': False, 'error': 'No se pudo conectar a la base de datos'}
            
            with db_manager.get_session() as session:
                # Verificar tablas principales
                essential_tables = ['mvt', 'mdl', 'idn', 'per', 'tck']
                missing_tables = []
                
                for table in essential_tables:
                    try:
                        result = session.execute(f"SELECT COUNT(*) FROM {table}")
                        count = result.scalar()
                        log_system(f"Tabla {table}: {count} registros", "DEBUG")
                    except Exception:
                        missing_tables.append(table)
                
                if missing_tables:
                    return {
                        'success': False, 
                        'error': f'Tablas faltantes: {", ".join(missing_tables)}'
                    }
                
                return {'success': True, 'status': 'healthy'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _check_camera_system(self) -> Dict[str, Any]:
        """Verificar sistema de cámaras"""
        try:
            if not self.camera_manager:
                self.camera_manager = HikvisionManager()
                
            if not self.camera_manager.initialize():
                return {'success': False, 'error': 'No se pudo inicializar sistema de cámaras'}
            
            # Obtener estadísticas
            stats = self.camera_manager.get_system_statistics()
            
            # Probar cámaras
            test_results = self.camera_manager.test_all_cameras()
            working_cameras = sum(1 for result in test_results.values() if result)
            
            log_system(f"Cámaras funcionando: {working_cameras}/{len(test_results)}", "INFO")
            
            return {
                'success': True,
                'statistics': stats,
                'test_results': test_results,
                'working_cameras': working_cameras,
                'total_cameras': len(test_results)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            if self.camera_manager:
                self.camera_manager.cleanup()
    
    def _optimize_database(self) -> Dict[str, Any]:
        """Optimizar base de datos"""
        try:
            with db_manager.get_session() as session:
                # Actualizar estadísticas de tablas principales
                optimization_queries = [
                    "UPDATE STATISTICS mvt",
                    "UPDATE STATISTICS mdl", 
                    "UPDATE STATISTICS idn",
                    "UPDATE STATISTICS per"
                ]
                
                for query in optimization_queries:
                    try:
                        session.execute(query)
                        log_system(f"Ejecutado: {query}", "DEBUG")
                    except Exception as e:
                        log_system(f"Error en optimización: {query} - {e}", "WARNING")
                
                return {'success': True, 'optimizations_run': len(optimization_queries)}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _backup_configuration(self) -> Dict[str, Any]:
        """Crear backup de configuración"""
        try:
            from utils.helpers import create_backup_filename
            import json
            
            backup_dir = settings.BASE_DIR / 'backups'
            backup_dir.mkdir(exist_ok=True)
            
            # Backup de configuración
            config_data = {
                'timestamp': datetime.now().isoformat(),
                'settings': {
                    'DB_SERVER': settings.DB_SERVER,
                    'DB_DATABASE': settings.DB_DATABASE,
                    'SERIAL_PORT': settings.SERIAL_PORT,
                    'POLLING_INTERVAL': settings.POLLING_INTERVAL
                }
            }
            
            config_backup_path = create_backup_filename('config.json', backup_dir)
            
            with open(config_backup_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            log_system(f"Backup de configuración creado: {config_backup_path}", "INFO")
            
            return {
                'success': True,
                'backup_path': str(config_backup_path),
                'backup_size': format_file_size(config_backup_path.stat().st_size)
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}


def main():
    """
    Función principal del script de mantenimiento
    """
    print("=== Script de Mantenimiento WPC ===")
    
    # Configurar logging
    setup_logging()
    
    # Ejecutar mantenimiento
    maintenance = MaintenanceManager()
    results = maintenance.run_full_maintenance()
    
    # Mostrar resultados
    print(f"\nMantenimiento {'EXITOSO' if results['success'] else 'FALLIDO'}")
    print(f"Inicio: {results['start_time']}")
    print(f"Fin: {results.get('end_time', 'N/A')}")
    
    print("\nResultados por tarea:")
    for task_name, task_result in results['tasks'].items():
        status = "✓" if task_result.get('success', False) else "✗"
        print(f"  {status} {task_name}: {task_result}")
    
    if results['errors']:
        print(f"\nErrores encontrados: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    return 0 if results['success'] else 1


if __name__ == "__main__":
    exit(main())
