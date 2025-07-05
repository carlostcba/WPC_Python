# camera_integration/hikvision_manager.py

"""
Gestor principal de cámaras Hikvision
Reemplaza GeoSVR.cls del sistema VB6
"""

import asyncio
import aiofiles
import base64
import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from urllib.parse import urljoin

import cv2
import requests
from requests.auth import HTTPDigestAuth
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings
from config.database import db_manager
from utils.logger import log_system, log_error, log_camera


class HikvisionDeviceType:
    """Tipos de dispositivos Hikvision soportados"""
    NVR = "nvr"
    DVR = "dvr"
    CAMERA = "camera"


class HikvisionDeviceConfig:
    """Configuración de dispositivo Hikvision"""
    def __init__(self, device_id: str, host: str, port: int = 80, 
                 username: str = "admin", password: str = "",
                 device_type: str = HikvisionDeviceType.NVR,
                 max_channels: int = 32, timeout: int = 10):
        self.device_id = device_id
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.device_type = device_type
        self.max_channels = max_channels
        self.timeout = timeout
        self.base_url = f"http://{host}:{port}"
        self.auth = HTTPDigestAuth(username, password)


class CameraChannelConfig:
    """Configuración de canal de cámara"""
    def __init__(self, device_id: str, channel: int, 
                 description: str = "", enabled: bool = True):
        self.device_id = device_id
        self.channel = channel
        self.description = description
        self.enabled = enabled


class HikvisionManager:
    """
    Gestor principal de cámaras Hikvision
    Equivalente a GeoSVR.cls en VB6
    """
    
    def __init__(self):
        """Inicializar gestor de cámaras Hikvision"""
        self.devices: Dict[str, HikvisionDeviceConfig] = {}
        self.module_cameras: Dict[int, CameraChannelConfig] = {}
        self.session = requests.Session()
        self.initialized = False
        
        # Configurar reintentos automáticos
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS", "POST"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Cache para optimización
        self._device_info_cache: Dict[str, Dict] = {}
        self._last_cache_update: Dict[str, datetime] = {}
        
        log_system("HikvisionManager inicializado", "INFO")
    
    def initialize(self) -> bool:
        """
        Inicializar sistema de cámaras
        Equivalente a Cargar_Propiedades_GEO en VB6
        """
        try:
            log_system("Inicializando sistema de cámaras Hikvision...", "INFO")
            
            # Cargar configuración desde base de datos
            if not self._load_configuration_from_database():
                log_system("No se pudo cargar configuración de cámaras", "WARNING")
                return False
            
            # Probar conexión a dispositivos configurados
            online_devices = 0
            for device_id, config in self.devices.items():
                if self._test_device_connection(config):
                    online_devices += 1
                    log_system(f"Dispositivo {device_id} conectado: {config.host}", "INFO")
                else:
                    log_system(f"Dispositivo {device_id} no disponible: {config.host}", "WARNING")
            
            if online_devices == 0:
                log_system("Ningún dispositivo Hikvision disponible", "WARNING")
                return False
            
            self.initialized = True
            log_system(f"Sistema de cámaras inicializado: {online_devices}/{len(self.devices)} dispositivos online", "INFO")
            return True
            
        except Exception as e:
            log_error(e, "HikvisionManager.initialize")
            return False
    
    def _load_configuration_from_database(self) -> bool:
        """
        Cargar configuración de cámaras desde base de datos
        """
        try:
            with db_manager.get_session() as session:
                # Cargar configuración de dispositivos Hikvision
                query = """
                SELECT 
                    Nombre as device_id,
                    Valor as config_value,
                    Descripcion
                FROM configuracion_hikvision 
                WHERE Activo = 1
                ORDER BY Nombre
                """
                
                result = session.execute(query)
                config_data = {}
                
                for row in result:
                    device_id = row.device_id
                    if device_id not in config_data:
                        config_data[device_id] = {}
                    
                    # Parsear configuración JSON
                    try:
                        config_value = json.loads(row.config_value)
                        config_data[device_id].update(config_value)
                    except json.JSONDecodeError:
                        config_data[device_id][row.device_id] = row.config_value
                
                # Crear configuraciones de dispositivos
                for device_id, config in config_data.items():
                    self.devices[device_id] = HikvisionDeviceConfig(
                        device_id=device_id,
                        host=config.get('host', '192.168.1.100'),
                        port=config.get('port', 80),
                        username=config.get('username', 'admin'),
                        password=config.get('password', ''),
                        device_type=config.get('type', HikvisionDeviceType.NVR),
                        max_channels=config.get('max_channels', 32),
                        timeout=config.get('timeout', 10)
                    )
                
                # Cargar mapeo módulo-cámara
                camera_mapping_query = """
                SELECT 
                    m.ModuloID,
                    mc.Camara,
                    hc.device_id,
                    hc.channel,
                    hc.description
                FROM mdl m
                LEFT JOIN mdlcam mc ON m.ModuloID = mc.ModuloID
                LEFT JOIN hikvision_cameras hc ON mc.Camara = hc.camera_legacy_id
                WHERE mc.Camara IS NOT NULL AND mc.Camara != 'N'
                """
                
                camera_result = session.execute(camera_mapping_query)
                for row in camera_result:
                    if row.device_id and row.channel:
                        self.module_cameras[row.ModuloID] = CameraChannelConfig(
                            device_id=row.device_id,
                            channel=int(row.channel),
                            description=row.description or f"Módulo {row.ModuloID}"
                        )
                
                log_system(f"Configuración cargada: {len(self.devices)} dispositivos, {len(self.module_cameras)} cámaras asignadas", "DEBUG")
                return True
                
        except Exception as e:
            log_error(e, "_load_configuration_from_database")
            return False
    
    def _test_device_connection(self, config: HikvisionDeviceConfig) -> bool:
        """
        Probar conexión a dispositivo Hikvision
        """
        try:
            url = urljoin(config.base_url, "/ISAPI/System/deviceInfo")
            response = self.session.get(
                url, 
                auth=config.auth, 
                timeout=config.timeout
            )
            
            if response.status_code == 200:
                # Guardar información del dispositivo en cache
                self._device_info_cache[config.device_id] = {
                    'status': 'online',
                    'device_info': response.text,
                    'last_check': datetime.now()
                }
                return True
            else:
                log_system(f"Error conectando a {config.device_id}: HTTP {response.status_code}", "WARNING")
                return False
                
        except Exception as e:
            log_system(f"Error probando conexión a {config.device_id}: {e}", "WARNING")
            return False
    
    def capture_image(self, module_id: int, movement_id: int = None, 
                     custom_filename: str = None) -> Tuple[bool, Optional[str]]:
        """
        Capturar imagen desde cámara asociada a módulo
        Equivalente a SnapShotToFile en VB6
        
        Args:
            module_id: ID del módulo
            movement_id: ID del movimiento (opcional)
            custom_filename: Nombre personalizado del archivo
            
        Returns:
            Tuple[bool, Optional[str]]: (éxito, ruta_archivo)
        """
        try:
            if not self.initialized:
                log_system("Sistema de cámaras no inicializado", "ERROR")
                return False, None
            
            # Buscar configuración de cámara para el módulo
            camera_config = self.module_cameras.get(module_id)
            if not camera_config:
                log_system(f"No hay cámara configurada para módulo {module_id}", "WARNING")
                return False, None
            
            device_config = self.devices.get(camera_config.device_id)
            if not device_config:
                log_system(f"Dispositivo {camera_config.device_id} no configurado", "ERROR")
                return False, None
            
            # Generar nombre de archivo
            if custom_filename:
                filename = custom_filename
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                if movement_id:
                    filename = f"movements/mvt_{movement_id}_{timestamp}.jpg"
                else:
                    filename = f"manual/module_{module_id}_{timestamp}.jpg"
            
            # Crear directorio si no existe
            filepath = settings.CAMERA_TEMP_DIR / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Capturar imagen
            success = self._capture_snapshot(device_config, camera_config.channel, filepath)
            
            if success:
                log_camera(f"Imagen capturada: {filepath}", module_id)
                return True, str(filepath)
            else:
                return False, None
                
        except Exception as e:
            log_error(e, f"capture_image(module_id={module_id})")
            return False, None
    
    def _capture_snapshot(self, device_config: HikvisionDeviceConfig, 
                         channel: int, filepath: Path) -> bool:
        """
        Capturar snapshot desde dispositivo Hikvision
        """
        try:
            # Construir URL del snapshot según tipo de dispositivo
            if device_config.device_type == HikvisionDeviceType.CAMERA:
                snapshot_url = "/ISAPI/Streaming/channels/101/picture"
            else:
                snapshot_url = f"/ISAPI/Streaming/channels/{channel}01/picture"
            
            url = urljoin(device_config.base_url, snapshot_url)
            
            response = self.session.get(
                url,
                auth=device_config.auth,
                timeout=device_config.timeout,
                stream=True
            )
            
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                log_camera(f"Snapshot capturado: {filepath}", channel)
                return True
            else:
                log_system(f"Error capturando snapshot: HTTP {response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            log_error(e, f"_capture_snapshot(channel={channel})")
            return False
    
    def capture_movement_photo(self, module_id: int, movement_id: int, 
                              identification: str) -> Tuple[bool, Optional[str]]:
        """
        Capturar foto automática en evento de movimiento
        Equivalente a la funcionalidad automática de GeoVision en VB6
        """
        try:
            log_camera(f"Capturando foto automática - Módulo: {module_id}, Movimiento: {movement_id}, ID: {identification}", module_id)
            
            # Generar nombre descriptivo
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"movements/mvt_{movement_id}_{identification}_{timestamp}.jpg"
            
            success, filepath = self.capture_image(module_id, movement_id, filename)
            
            if success:
                # Opcional: Guardar referencia en base de datos
                self._save_image_reference(movement_id, filepath)
                log_camera(f"Foto de movimiento guardada: {filepath}", module_id)
            
            return success, filepath
            
        except Exception as e:
            log_error(e, f"capture_movement_photo(module_id={module_id}, movement_id={movement_id})")
            return False, None
    
    def _save_image_reference(self, movement_id: int, filepath: str):
        """
        Guardar referencia de imagen en base de datos
        """
        try:
            with db_manager.get_session() as session:
                # Insertar referencia en tabla de imágenes (si existe)
                insert_query = """
                INSERT INTO movement_images (MovimientoID, ImagePath, CaptureDateTime)
                VALUES (?, ?, ?)
                """
                session.execute(insert_query, (movement_id, filepath, datetime.now()))
                
        except Exception as e:
            # No es crítico si falla
            log_system(f"Error guardando referencia de imagen: {e}", "WARNING")
    
    def get_rtsp_url(self, module_id: int) -> Optional[str]:
        """
        Obtener URL RTSP para streaming en tiempo real
        """
        try:
            camera_config = self.module_cameras.get(module_id)
            if not camera_config:
                return None
            
            device_config = self.devices.get(camera_config.device_id)
            if not device_config:
                return None
            
            # Construir URL RTSP
            if device_config.device_type == HikvisionDeviceType.CAMERA:
                rtsp_path = "/Streaming/Channels/101"
            else:
                rtsp_path = f"/Streaming/Channels/{camera_config.channel}01"
            
            rtsp_url = f"rtsp://{device_config.username}:{device_config.password}@{device_config.host}:554{rtsp_path}"
            return rtsp_url
            
        except Exception as e:
            log_error(e, f"get_rtsp_url(module_id={module_id})")
            return None
    
    def start_live_preview(self, module_id: int, callback: Callable[[Any], None]) -> bool:
        """
        Iniciar vista previa en vivo
        """
        try:
            rtsp_url = self.get_rtsp_url(module_id)
            if not rtsp_url:
                return False
            
            # Iniciar captura en hilo separado
            def capture_thread():
                cap = cv2.VideoCapture(rtsp_url)
                try:
                    while True:
                        ret, frame = cap.read()
                        if ret:
                            callback(frame)
                        else:
                            break
                        time.sleep(0.033)  # ~30 FPS
                finally:
                    cap.release()
            
            thread = threading.Thread(target=capture_thread, daemon=True)
            thread.start()
            
            return True
            
        except Exception as e:
            log_error(e, f"start_live_preview(module_id={module_id})")
            return False
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """
        Obtener estado detallado de dispositivo
        """
        try:
            device_config = self.devices.get(device_id)
            if not device_config:
                return {"status": "not_configured"}
            
            # Verificar cache
            cache_info = self._device_info_cache.get(device_id)
            if cache_info and (datetime.now() - cache_info['last_check']).seconds < 60:
                return cache_info
            
            # Actualizar información del dispositivo
            if self._test_device_connection(device_config):
                return self._device_info_cache[device_id]
            else:
                return {"status": "offline", "last_check": datetime.now()}
                
        except Exception as e:
            log_error(e, f"get_device_status(device_id={device_id})")
            return {"status": "error", "error": str(e)}
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """
        Obtener estadísticas del sistema de cámaras
        """
        try:
            online_devices = 0
            total_devices = len(self.devices)
            configured_cameras = len(self.module_cameras)
            
            for device_id in self.devices.keys():
                status = self.get_device_status(device_id)
                if status.get("status") == "online":
                    online_devices += 1
            
            return {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": total_devices - online_devices,
                "configured_cameras": configured_cameras,
                "system_status": "healthy" if online_devices > 0 else "degraded",
                "last_update": datetime.now().isoformat()
            }
            
        except Exception as e:
            log_error(e, "get_system_statistics")
            return {"error": str(e)}
    
    def add_device(self, device_id: str, host: str, username: str = "admin", 
                   password: str = "", device_type: str = HikvisionDeviceType.NVR) -> bool:
        """
        Agregar dispositivo dinámicamente
        """
        try:
            config = HikvisionDeviceConfig(
                device_id=device_id,
                host=host,
                username=username,
                password=password,
                device_type=device_type
            )
            
            if self._test_device_connection(config):
                self.devices[device_id] = config
                log_system(f"Dispositivo agregado: {device_id} ({host})", "INFO")
                return True
            else:
                log_system(f"No se pudo conectar al dispositivo: {device_id} ({host})", "ERROR")
                return False
                
        except Exception as e:
            log_error(e, f"add_device(device_id={device_id})")
            return False
    
    def assign_camera_to_module(self, module_id: int, device_id: str, 
                               channel: int, description: str = "") -> bool:
        """
        Asignar cámara a módulo
        """
        try:
            if device_id not in self.devices:
                log_system(f"Dispositivo {device_id} no configurado", "ERROR")
                return False
            
            self.module_cameras[module_id] = CameraChannelConfig(
                device_id=device_id,
                channel=channel,
                description=description or f"Módulo {module_id}"
            )
            
            log_system(f"Cámara asignada: Módulo {module_id} -> {device_id}:{channel}", "INFO")
            return True
            
        except Exception as e:
            log_error(e, f"assign_camera_to_module(module_id={module_id})")
            return False
    
    def test_all_cameras(self) -> Dict[int, bool]:
        """
        Probar todas las cámaras configuradas
        """
        results = {}
        
        for module_id, camera_config in self.module_cameras.items():
            try:
                # Intentar capturar imagen de prueba
                test_filename = f"test/module_{module_id}_test.jpg"
                success, _ = self.capture_image(module_id, custom_filename=test_filename)
                results[module_id] = success
                
                if success:
                    log_system(f"Test OK: Módulo {module_id}", "INFO")
                else:
                    log_system(f"Test FAIL: Módulo {module_id}", "WARNING")
                    
            except Exception as e:
                results[module_id] = False
                log_error(e, f"test_all_cameras(module_id={module_id})")
        
        return results
    
    def cleanup(self):
        """
        Limpiar recursos
        """
        try:
            self.session.close()
            self._device_info_cache.clear()
            log_system("HikvisionManager limpiado", "INFO")
        except Exception as e:
            log_error(e, "cleanup")
