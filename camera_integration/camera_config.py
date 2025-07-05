# camera_integration/camera_config.py

"""
Configuración y utilidades para sistema de cámaras
"""
from dataclasses import dataclass
from typing import Dict, List, Optional
from pathlib import Path

from config.settings import settings


@dataclass
class CameraQualitySettings:
    """Configuración de calidad de imagen"""
    resolution: str = "1920x1080"  # Resolución
    fps: int = 25                  # Frames por segundo
    bitrate: int = 2048           # Bitrate en kbps
    compression: str = "H.264"     # Codec de compresión


@dataclass
class StorageSettings:
    """Configuración de almacenamiento"""
    base_directory: Path
    max_file_size_mb: int = 10
    retention_days: int = 30
    auto_cleanup: bool = True
    
    def __post_init__(self):
        self.base_directory.mkdir(parents=True, exist_ok=True)


class CameraConfigurationManager:
    """
    Gestor de configuraciones de cámaras
    """
    
    def __init__(self):
        self.quality_presets = {
            "high": CameraQualitySettings("1920x1080", 25, 4096, "H.264"),
            "medium": CameraQualitySettings("1280x720", 15, 2048, "H.264"),
            "low": CameraQualitySettings("640x480", 10, 1024, "H.264")
        }
        
        self.storage = StorageSettings(
            base_directory=settings.CAMERA_TEMP_DIR,
            retention_days=30,
            auto_cleanup=True
        )
    
    def get_quality_preset(self, preset_name: str) -> CameraQualitySettings:
        """Obtener preset de calidad"""
        return self.quality_presets.get(preset_name, self.quality_presets["medium"])
    
    def create_directory_structure(self):
        """Crear estructura de directorios"""
        directories = [
            "movements",   # Fotos automáticas de movimientos
            "manual",      # Capturas manuales
            "test",        # Imágenes de prueba
            "backup"       # Respaldo temporal
        ]
        
        for directory in directories:
            (self.storage.base_directory / directory).mkdir(parents=True, exist_ok=True)
    
    def cleanup_old_images(self) -> int:
        """Limpiar imágenes antiguas según configuración"""
        if not self.storage.auto_cleanup:
            return 0
        
        try:
            from datetime import datetime, timedelta
            import os
            
            cutoff_date = datetime.now() - timedelta(days=self.storage.retention_days)
            deleted_count = 0
            
            for root, dirs, files in os.walk(self.storage.base_directory):
                for file in files:
                    if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                        filepath = Path(root) / file
                        file_mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
                        
                        if file_mtime < cutoff_date:
                            filepath.unlink()
                            deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            log_error(e, "cleanup_old_images")
            return 0
