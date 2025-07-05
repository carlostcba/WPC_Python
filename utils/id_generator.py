# utils/id_generator.py
"""
Generador de IDs únicos para el sistema WPC
Reemplaza las funciones de generación de IDs de VB6
"""
from datetime import datetime, date
import time
from typing import Dict, Any

class IDGenerator:
    """
    Generador de IDs únicos compatible con el sistema VB6
    Mantiene compatibilidad con la lógica original
    """
    
    # Fecha base para cálculos (según documentación VB6)
    BASE_DATE = date(2007, 6, 1)
    
    @classmethod
    def generate_movement_id(cls) -> int:
        """
        Generar ID único para movimientos
        Equivalente a new_id_mvt en VB6
        
        Fórmula: días_desde_base * 100000000 + milisegundos_del_dia
        
        Returns:
            int: ID único para movimiento
        """
        current_date = datetime.now()
        
        # Calcular días desde fecha base
        days_diff = (current_date.date() - cls.BASE_DATE).days
        
        # Calcular milisegundos del día actual
        milliseconds_today = (
            current_date.hour * 3600000 +
            current_date.minute * 60000 +
            current_date.second * 1000 +
            current_date.microsecond // 1000
        )
        
        return days_diff * 100000000 + milliseconds_today
    
    @classmethod
    def generate_ticket_id(cls) -> int:
        """
        Generar ID único para tickets
        Similar a movimientos pero con offset para evitar colisiones
        
        Returns:
            int: ID único para ticket
        """
        return cls.generate_movement_id() + 50000000  # Offset para tickets
    
    @classmethod
    def generate_person_id(cls) -> int:
        """
        Generar ID único para personas
        Basado en timestamp Unix con offset
        
        Returns:
            int: ID único para persona
        """
        return int(time.time() * 1000) % 1000000000  # Últimos 9 dígitos
    
    @classmethod
    def generate_identification_id(cls) -> int:
        """
        Generar ID único para identificaciones
        
        Returns:
            int: ID único para identificación
        """
        return cls.generate_movement_id() + 25000000  # Offset para identificaciones
    
    @classmethod
    def parse_movement_id(cls, movement_id: int) -> Dict[str, Any]:
        """
        Parsear ID de movimiento para extraer información temporal
        
        Args:
            movement_id: ID de movimiento a parsear
            
        Returns:
            dict: Información extraída (fecha, hora, etc.)
        """
        try:
            days_from_base = movement_id // 100000000
            milliseconds_today = movement_id % 100000000
            
            # Calcular fecha
            target_date = cls.BASE_DATE + timedelta(days=days_from_base)
            
            # Calcular hora del día
            total_seconds = milliseconds_today // 1000
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            milliseconds = milliseconds_today % 1000
            
            return {
                'date': target_date,
                'hours': hours,
                'minutes': minutes,
                'seconds': seconds,
                'milliseconds': milliseconds,
                'datetime': datetime.combine(
                    target_date, 
                    time(hours, minutes, seconds, milliseconds * 1000)
                )
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'valid': False
            }
    
    @classmethod
    def validate_id_format(cls, id_value: int, id_type: str = "movement") -> bool:
        """
        Validar formato de ID según tipo
        
        Args:
            id_value: Valor del ID a validar
            id_type: Tipo de ID ("movement", "ticket", "person", "identification")
            
        Returns:
            bool: True si el formato es válido
        """
        try:
            if id_type == "movement":
                # Los IDs de movimiento deben ser positivos y tener formato específico
                if id_value <= 0:
                    return False
                
                parsed = cls.parse_movement_id(id_value)
                return 'error' not in parsed
                
            elif id_type == "ticket":
                # Los tickets tienen offset de 50M
                base_id = id_value - 50000000
                return cls.validate_id_format(base_id, "movement")
                
            elif id_type == "identification":
                # Las identificaciones tienen offset de 25M
                base_id = id_value - 25000000
                return cls.validate_id_format(base_id, "movement")
                
            elif id_type == "person":
                # IDs de persona deben ser positivos y razonables
                return 0 < id_value < 10000000000
                
            else:
                return False
                
        except Exception:
            return False

# Funciones de conveniencia para uso directo
def new_movement_id() -> int:
    """Generar nuevo ID de movimiento"""
    return IDGenerator.generate_movement_id()

def new_ticket_id() -> int:
    """Generar nuevo ID de ticket"""
    return IDGenerator.generate_ticket_id()

def new_person_id() -> int:
    """Generar nuevo ID de persona"""
    return IDGenerator.generate_person_id()

def new_identification_id() -> int:
    """Generar nuevo ID de identificación"""
    return IDGenerator.generate_identification_id()