# utils/helpers.py - UTILIDADES ADICIONALES
# ========================================
"""
Funciones auxiliares adicionales para el sistema
"""
import os
import platform
import psutil
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path


def format_identification(identification: str) -> str:
    """
    Formatear número de identificación
    
    Args:
        identification: Número sin formatear
        
    Returns:
        str: Número formateado
    """
    if not identification:
        return ""
    
    # Remover espacios y caracteres especiales
    clean_id = ''.join(filter(str.isalnum, identification))
    
    # Agregar ceros a la izquierda si es necesario (longitud estándar: 8)
    return clean_id.zfill(8)


def validate_datetime_range(start_date: datetime, end_date: datetime) -> bool:
    """
    Validar rango de fechas
    
    Args:
        start_date: Fecha de inicio
        end_date: Fecha de fin
        
    Returns:
        bool: True si el rango es válido
    """
    if not start_date or not end_date:
        return False
    
    # Fecha de inicio no puede ser mayor que fecha de fin
    if start_date > end_date:
        return False
    
    # El rango no puede ser mayor a 1 año
    if (end_date - start_date).days > 365:
        return False
    
    return True


def get_system_info() -> Dict[str, Any]:
    """
    Obtener información del sistema
    
    Returns:
        Dict[str, Any]: Información del sistema
    """
    try:
        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'release': platform.release(),
            'version': platform.version(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'disk_usage': {
                'total_gb': round(psutil.disk_usage('/').total / (1024**3), 2),
                'free_gb': round(psutil.disk_usage('/').free / (1024**3), 2),
                'used_percent': psutil.disk_usage('/').percent
            },
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'error': str(e), 'timestamp': datetime.now().isoformat()}


def cleanup_temp_directory(directory: Path, max_age_days: int = 7) -> int:
    """
    Limpiar directorio temporal
    
    Args:
        directory: Directorio a limpiar
        max_age_days: Edad máxima de archivos en días
        
    Returns:
        int: Número de archivos eliminados
    """
    if not directory.exists():
        return 0
    
    try:
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
        
        return deleted_count
        
    except Exception as e:
        from utils.logger import log_error
        log_error(e, f"cleanup_temp_directory({directory})")
        return 0


def validate_ip_address(ip: str) -> bool:
    """
    Validar dirección IP
    
    Args:
        ip: Dirección IP a validar
        
    Returns:
        bool: True si es válida
    """
    try:
        import ipaddress
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def format_file_size(size_bytes: int) -> str:
    """
    Formatear tamaño de archivo en formato legible
    
    Args:
        size_bytes: Tamaño en bytes
        
    Returns:
        str: Tamaño formateado
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.1f} {units[unit_index]}"


def create_backup_filename(original_filename: str, backup_dir: Path) -> Path:
    """
    Crear nombre de archivo de backup único
    
    Args:
        original_filename: Nombre original
        backup_dir: Directorio de backup
        
    Returns:
        Path: Ruta completa del backup
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name_parts = Path(original_filename).stem, timestamp, Path(original_filename).suffix
    backup_filename = f"{name_parts[0]}_backup_{name_parts[1]}{name_parts[2]}"
    
    return backup_dir / backup_filename