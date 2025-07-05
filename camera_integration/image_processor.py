# camera_integration/image_processor.py

"""
Procesamiento y análisis de imágenes
"""
import cv2
import numpy as np
from typing import Tuple, Optional, Dict, Any
from pathlib import Path

from utils.logger import log_system, log_error


class ImageProcessor:
    """
    Procesador de imágenes capturadas
    """
    
    def __init__(self):
        self.default_size = (800, 600)
    
    def resize_image(self, image_path: Path, target_size: Tuple[int, int] = None) -> bool:
        """
        Redimensionar imagen manteniendo proporción
        """
        try:
            if target_size is None:
                target_size = self.default_size
            
            # Leer imagen
            image = cv2.imread(str(image_path))
            if image is None:
                return False
            
            # Calcular nuevo tamaño manteniendo proporción
            h, w = image.shape[:2]
            target_w, target_h = target_size
            
            aspect_ratio = w / h
            if aspect_ratio > 1:  # Imagen más ancha que alta
                new_w = target_w
                new_h = int(target_w / aspect_ratio)
            else:  # Imagen más alta que ancha
                new_h = target_h
                new_w = int(target_h * aspect_ratio)
            
            # Redimensionar
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Guardar imagen redimensionada
            cv2.imwrite(str(image_path), resized)
            return True
            
        except Exception as e:
            log_error(e, f"resize_image({image_path})")
            return False
    
    def add_watermark(self, image_path: Path, text: str, 
                     position: str = "bottom_right") -> bool:
        """
        Agregar marca de agua a imagen
        """
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return False
            
            h, w = image.shape[:2]
            
            # Configurar fuente
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.7
            color = (255, 255, 255)  # Blanco
            thickness = 2
            
            # Calcular posición del texto
            text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
            
            if position == "bottom_right":
                x = w - text_size[0] - 10
                y = h - 10
            elif position == "bottom_left":
                x = 10
                y = h - 10
            elif position == "top_right":
                x = w - text_size[0] - 10
                y = text_size[1] + 10
            else:  # top_left
                x = 10
                y = text_size[1] + 10
            
            # Agregar fondo semi-transparente
            overlay = image.copy()
            cv2.rectangle(overlay, (x-5, y-text_size[1]-5), 
                         (x+text_size[0]+5, y+5), (0, 0, 0), -1)
            image = cv2.addWeighted(image, 0.8, overlay, 0.2, 0)
            
            # Agregar texto
            cv2.putText(image, text, (x, y), font, font_scale, color, thickness)
            
            # Guardar imagen con marca de agua
            cv2.imwrite(str(image_path), image)
            return True
            
        except Exception as e:
            log_error(e, f"add_watermark({image_path})")
            return False
    
    def enhance_image(self, image_path: Path) -> bool:
        """
        Mejorar calidad de imagen (brillo, contraste)
        """
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return False
            
            # Mejorar contraste y brillo
            alpha = 1.2  # Contraste
            beta = 10    # Brillo
            
            enhanced = cv2.convertScaleAbs(image, alpha=alpha, beta=beta)
            
            # Opcional: Aplicar filtro de nitidez
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
            
            # Guardar imagen mejorada
            cv2.imwrite(str(image_path), sharpened)
            return True
            
        except Exception as e:
            log_error(e, f"enhance_image({image_path})")
            return False
    
    def create_thumbnail(self, image_path: Path, thumbnail_size: Tuple[int, int] = (150, 150)) -> Optional[Path]:
        """
        Crear miniatura de imagen
        """
        try:
            image = cv2.imread(str(image_path))
            if image is None:
                return None
            
            # Crear thumbnail
            thumbnail = cv2.resize(image, thumbnail_size, interpolation=cv2.INTER_AREA)
            
            # Generar nombre del thumbnail
            thumb_path = image_path.parent / f"thumb_{image_path.name}"
            
            # Guardar thumbnail
            cv2.imwrite(str(thumb_path), thumbnail)
            return thumb_path
            
        except Exception as e:
            log_error(e, f"create_thumbnail({image_path})")
            return None
    
    def detect_motion_area(self, image_path: Path, reference_image_path: Path = None) -> Dict[str, Any]:
        """
        Detectar área de movimiento comparando con imagen de referencia
        """
        try:
            current_image = cv2.imread(str(image_path))
            if current_image is None:
                return {"motion_detected": False, "error": "Cannot read current image"}
            
            if reference_image_path and reference_image_path.exists():
                reference_image = cv2.imread(str(reference_image_path))
                if reference_image is not None:
                    # Convertir a escala de grises
                    gray_current = cv2.cvtColor(current_image, cv2.COLOR_BGR2GRAY)
                    gray_reference = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)
                    
                    # Calcular diferencia
                    diff = cv2.absdiff(gray_current, gray_reference)
                    
                    # Aplicar threshold
                    _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
                    
                    # Encontrar contornos
                    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    
                    # Calcular área de movimiento
                    motion_area = sum(cv2.contourArea(contour) for contour in contours)
                    total_area = gray_current.shape[0] * gray_current.shape[1]
                    motion_percentage = (motion_area / total_area) * 100
                    
                    return {
                        "motion_detected": motion_percentage > 5.0,  # 5% threshold
                        "motion_percentage": motion_percentage,
                        "motion_area": motion_area,
                        "contours_count": len(contours)
                    }
            
            return {"motion_detected": False, "info": "No reference image"}
            
        except Exception as e:
            log_error(e, f"detect_motion_area({image_path})")
            return {"motion_detected": False, "error": str(e)}