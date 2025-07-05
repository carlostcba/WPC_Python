# core/database/managers.py
"""
Gestores de lógica de negocio para el sistema WPC
Equivalente a ClsMvt.cls y TckSVR.cls en VB6
"""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func

from .models import (
    Movement, Module, Identification, Person, Ticket, TicketHistory,
    PersonIdentification, PersonGroup, Group, MovementCategoryValue
)
from config.database import db_manager
from utils.id_generator import IDGenerator
from utils.logger import log_movement, log_error

class AccessResult:
    """
    Resultado de validación de acceso
    Equivalente a los resultados de Identificacion_Habilitada en VB6
    """
    def __init__(self, allowed: bool, reason: str = "", person: Optional[Person] = None):
        self.allowed = allowed
        self.reason = reason
        self.person = person
        self.timestamp = datetime.now()

class MovementManager:
    """
    Gestor de movimientos de acceso
    Equivalente a ClsMvt.cls en VB6
    """
    
    def __init__(self):
        self.db = db_manager
    
    def validate_identification(self, identification_number: str, module_id: int, 
                              event_datetime: Optional[datetime] = None) -> AccessResult:
        """
        Validar si una identificación tiene acceso
        Equivalente a Identificacion_Habilitada en VB6
        
        Args:
            identification_number: Número de tarjeta/código
            module_id: ID del módulo donde se presenta
            event_datetime: Momento del evento (default: ahora)
            
        Returns:
            AccessResult: Resultado de la validación
        """
        if event_datetime is None:
            event_datetime = datetime.now()
        
        try:
            with self.db.get_session() as session:
                # 1. Buscar identificación
                identification = session.query(Identification).filter(
                    Identification.Numero == identification_number
                ).first()
                
                if not identification:
                    return AccessResult(False, "Identificación no encontrada")
                
                # 2. Buscar persona asociada
                person_relation = session.query(PersonIdentification).filter(
                    PersonIdentification.IdentificacionID == identification.IdentificacionID
                ).first()
                
                if not person_relation:
                    return AccessResult(False, "Identificación sin persona asociada")
                
                person = session.query(Person).filter(
                    Person.PersonaID == person_relation.PersonaID
                ).first()
                
                if not person:
                    return AccessResult(False, "Persona no encontrada")
                
                # 3. Validar vigencia de la persona
                if person.FechaInicio and event_datetime < person.FechaInicio:
                    return AccessResult(False, "Acceso no vigente aún", person)
                
                if person.FechaFin and event_datetime > person.FechaFin:
                    return AccessResult(False, "Acceso vencido", person)
                
                # 4. Validar antipassback si es necesario
                if not self._validate_antipassback(person.PersonaID, module_id, session):
                    return AccessResult(False, "Violación de antipassback", person)
                
                # 5. Validar permanencia mínima si aplica
                if not self._validate_minimum_stay(person.PersonaID, module_id, session):
                    return AccessResult(False, "Permanencia mínima no cumplida", person)
                
                # 6. Validaciones de perfiles horarios (simplificado)
                # TODO: Implementar validación completa de perfiles
                
                return AccessResult(True, "Acceso autorizado", person)
                
        except Exception as e:
            log_error(e, f"validate_identification({identification_number}, {module_id})")
            return AccessResult(False, f"Error interno: {str(e)}")
    
    def create_movement(self, identification_number: str, module_id: int,
                       event_datetime: Optional[datetime] = None,
                       movement_type: str = "Peatonal",
                       direction: str = "Entrada") -> Tuple[bool, Optional[int]]:
        """
        Crear un nuevo movimiento en la base de datos
        Equivalente a Crear_Movimiento en VB6
        
        Args:
            identification_number: Número de identificación
            module_id: ID del módulo
            event_datetime: Timestamp del evento
            movement_type: Tipo de movimiento
            direction: Dirección (Entrada/Salida)
            
        Returns:
            Tuple[bool, Optional[int]]: (éxito, movement_id)
        """
        if event_datetime is None:
            event_datetime = datetime.now()
        
        try:
            with self.db.get_session() as session:
                # 1. Validar que existe la identificación
                identification = session.query(Identification).filter(
                    Identification.Numero == identification_number
                ).first()
                
                if not identification:
                    log_error(Exception("Identificación no encontrada"), 
                            f"create_movement({identification_number})")
                    return False, None
                
                # 2. Validar que existe el módulo
                module = session.query(Module).filter(
                    Module.ModuloID == module_id
                ).first()
                
                if not module:
                    log_error(Exception("Módulo no encontrado"), 
                            f"create_movement(module_id={module_id})")
                    return False, None
                
                # 3. Generar ID único usando algoritmo VB6
                movement_id = IDGenerator.generate_movement_id()
                
                # 4. Crear el movimiento
                movement = Movement(
                    MovimientoID=movement_id,
                    ModuloID=module_id,
                    IdentificacionID=identification.IdentificacionID,
                    FechaHora=event_datetime
                )
                
                session.add(movement)
                session.flush()  # Para obtener el ID antes del commit
                
                # 5. Agregar categorías del movimiento (tipo y dirección)
                self._add_movement_categories(session, movement_id, movement_type, direction)
                
                # Log del movimiento
                log_movement(movement_id, module_id, identification_number, "Creado exitosamente")
                
                return True, movement_id
                
        except Exception as e:
            log_error(e, f"create_movement({identification_number}, {module_id})")
            return False, None
    
    def get_last_movement(self, person_id: int, limit_hours: int = 24) -> Optional[Movement]:
        """
        Obtener último movimiento de una persona
        Para validaciones de antipassback
        """
        try:
            with self.db.get_session() as session:
                # Buscar identificaciones de la persona
                person_identifications = session.query(PersonIdentification).filter(
                    PersonIdentification.PersonaID == person_id
                ).all()
                
                identification_ids = [pi.IdentificacionID for pi in person_identifications]
                
                if not identification_ids:
                    return None
                
                # Buscar último movimiento dentro del límite de tiempo
                limit_time = datetime.now() - timedelta(hours=limit_hours)
                
                return session.query(Movement).filter(
                    and_(
                        Movement.IdentificacionID.in_(identification_ids),
                        Movement.FechaHora >= limit_time
                    )
                ).order_by(desc(Movement.FechaHora)).first()
                
        except Exception as e:
            log_error(e, f"get_last_movement({person_id})")
            return None
    
    def _validate_antipassback(self, person_id: int, module_id: int, session: Session) -> bool:
        """
        Validar reglas de antipassback
        Evita accesos duplicados sin salida previa
        """
        # Obtener último movimiento de la persona
        last_movement = self.get_last_movement(person_id, limit_hours=48)
        
        if not last_movement:
            return True  # Sin movimientos previos, permitir
        
        # TODO: Implementar lógica específica de antipassback
        # según configuración de módulos entrada/salida
        
        return True  # Por ahora permitir (implementar según reglas de negocio)
    
    def _validate_minimum_stay(self, person_id: int, module_id: int, session: Session) -> bool:
        """
        Validar permanencia mínima entre accesos
        """
        last_movement = self.get_last_movement(person_id, limit_hours=1)
        
        if not last_movement:
            return True
        
        # Validar que han pasado al menos X minutos desde último acceso
        min_minutes = 5  # Configurable
        time_diff = datetime.now() - last_movement.FechaHora
        
        return time_diff.total_seconds() >= (min_minutes * 60)
    
    def _add_movement_categories(self, session: Session, movement_id: int, 
                                movement_type: str, direction: str):
        """
        Agregar categorías al movimiento (tipo y dirección)
        Equivalente al sistema EAV de VB6
        """
        # Categoría 23: Tipo de movimiento (Peatonal, Vehicular)
        if movement_type == "Peatonal":
            type_category = MovementCategoryValue(
                MovimientoID=movement_id,
                CategoriaID=23,
                ValorID=1  # Valor para "Peatonal"
            )
            session.add(type_category)
        
        # Categoría 4: Dirección (Entrada, Salida)
        direction_value = 1 if direction == "Entrada" else 2
        direction_category = MovementCategoryValue(
            MovimientoID=movement_id,
            CategoriaID=4,
            ValorID=direction_value
        )
        session.add(direction_category)

class TicketManager:
    """
    Gestor de tickets de estacionamiento
    Equivalente a TckSVR.cls en VB6
    """
    
    def __init__(self):
        self.db = db_manager
    
    def create_ticket(self, module_id: int, entry_datetime: Optional[datetime] = None) -> Tuple[bool, Optional[int]]:
        """
        Crear nuevo ticket de ingreso
        Equivalente a Crear_Movimiento_Tck en VB6
        
        Returns:
            Tuple[bool, Optional[int]]: (éxito, ticket_number)
        """
        if entry_datetime is None:
            entry_datetime = datetime.now()
        
        try:
            with self.db.get_session() as session:
                # 1. Generar IDs únicos
                ticket_id = IDGenerator.generate_ticket_id()
                ticket_number = self._generate_ticket_number()
                
                # 2. Crear ticket
                ticket = Ticket(
                    TicketID=ticket_id,
                    Numero=ticket_number,
                    FechaHoraIngreso=entry_datetime,
                    ModuloIngresoID=module_id,
                    Validado=False
                )
                
                session.add(ticket)
                
                log_movement(ticket_id, module_id, str(ticket_number), "Ticket creado")
                
                return True, ticket_number
                
        except Exception as e:
            log_error(e, f"create_ticket({module_id})")
            return False, None
    
    def process_ticket_exit(self, ticket_number: int, module_id: int,
                           exit_datetime: Optional[datetime] = None) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Procesar salida de ticket
        Mueve ticket de tck a tckhst
        
        Returns:
            Tuple[bool, Optional[Dict]]: (éxito, info_ticket)
        """
        if exit_datetime is None:
            exit_datetime = datetime.now()
        
        try:
            with self.db.get_session() as session:
                # 1. Buscar ticket activo
                active_ticket = session.query(Ticket).filter(
                    Ticket.Numero == ticket_number
                ).first()
                
                if not active_ticket:
                    return False, {"error": "Ticket no encontrado o ya procesado"}
                
                # 2. Calcular información de estadía
                duration = exit_datetime - active_ticket.FechaHoraIngreso
                duration_minutes = int(duration.total_seconds() / 60)
                
                # 3. Crear registro en historial
                ticket_history = TicketHistory(
                    TicketID=active_ticket.TicketID,
                    Numero=active_ticket.Numero,
                    FechaHoraIngreso=active_ticket.FechaHoraIngreso,
                    ModuloIngresoID=active_ticket.ModuloIngresoID,
                    FechaHoraSalida=exit_datetime,
                    ModuloSalidaID=module_id
                )
                
                session.add(ticket_history)
                
                # 4. Eliminar de tickets activos
                session.delete(active_ticket)
                
                # 5. Información del ticket procesado
                ticket_info = {
                    "ticket_number": ticket_number,
                    "entry_time": active_ticket.FechaHoraIngreso,
                    "exit_time": exit_datetime,
                    "duration_minutes": duration_minutes,
                    "entry_module": active_ticket.ModuloIngresoID,
                    "exit_module": module_id
                }
                
                log_movement(active_ticket.TicketID, module_id, str(ticket_number), 
                           f"Ticket procesado - {duration_minutes} minutos")
                
                return True, ticket_info
                
        except Exception as e:
            log_error(e, f"process_ticket_exit({ticket_number}, {module_id})")
            return False, {"error": f"Error procesando ticket: {str(e)}"}
    
    def validate_ticket(self, ticket_number: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Validar ticket para salida
        Verificar que existe y calcular tiempo de estadía
        """
        try:
            with self.db.get_session() as session:
                ticket = session.query(Ticket).filter(
                    Ticket.Numero == ticket_number
                ).first()
                
                if not ticket:
                    return False, {"error": "Ticket no válido"}
                
                # Calcular tiempo de estadía
                now = datetime.now()
                duration = now - ticket.FechaHoraIngreso
                duration_minutes = int(duration.total_seconds() / 60)
                
                ticket_info = {
                    "ticket_number": ticket_number,
                    "entry_time": ticket.FechaHoraIngreso,
                    "duration_minutes": duration_minutes,
                    "entry_module": ticket.ModuloIngresoID,
                    "valid": True
                }
                
                return True, ticket_info
                
        except Exception as e:
            log_error(e, f"validate_ticket({ticket_number})")
            return False, {"error": f"Error validando ticket: {str(e)}"}
    
    def get_active_tickets_count(self) -> int:
        """
        Obtener cantidad de tickets activos
        """
        try:
            with self.db.get_session() as session:
                return session.query(Ticket).count()
        except Exception as e:
            log_error(e, "get_active_tickets_count")
            return 0
    
    def get_tickets_by_date_range(self, start_date: datetime, end_date: datetime) -> List[TicketHistory]:
        """
        Obtener tickets procesados en rango de fechas
        """
        try:
            with self.db.get_session() as session:
                return session.query(TicketHistory).filter(
                    and_(
                        TicketHistory.FechaHoraIngreso >= start_date,
                        TicketHistory.FechaHoraIngreso <= end_date
                    )
                ).order_by(TicketHistory.FechaHoraIngreso).all()
        except Exception as e:
            log_error(e, f"get_tickets_by_date_range({start_date}, {end_date})")
            return []
    
    def _generate_ticket_number(self) -> int:
        """
        Generar número secuencial de ticket
        """
        try:
            with self.db.get_session() as session:
                # Obtener último número usado
                last_active = session.query(func.max(Ticket.Numero)).scalar()
                last_history = session.query(func.max(TicketHistory.Numero)).scalar()
                
                last_number = max(last_active or 0, last_history or 0)
                return last_number + 1
                
        except Exception as e:
            # Fallback: usar timestamp
            return int(datetime.now().timestamp()) % 1000000

class ModuleManager:
    """
    Gestor de módulos de hardware
    Equivalente a funciones de gestión de módulos en VB6
    """
    
    def __init__(self):
        self.db = db_manager
    
    def get_all_modules(self) -> List[Module]:
        """
        Obtener todos los módulos configurados
        """
        try:
            with self.db.get_session() as session:
                return session.query(Module).order_by(Module.OrdenEncuesta).all()
        except Exception as e:
            log_error(e, "get_all_modules")
            return []
    
    def get_module_by_id(self, module_id: int) -> Optional[Module]:
        """
        Obtener módulo por ID
        """
        try:
            with self.db.get_session() as session:
                return session.query(Module).filter(Module.ModuloID == module_id).first()
        except Exception as e:
            log_error(e, f"get_module_by_id({module_id})")
            return None
    
    def get_module_by_address(self, address: int) -> Optional[Module]:
        """
        Obtener módulo por dirección RS485
        """
        try:
            with self.db.get_session() as session:
                return session.query(Module).filter(Module.Address == address).first()
        except Exception as e:
            log_error(e, f"get_module_by_address({address})")
            return None
    
    def get_modules_for_polling(self) -> List[Module]:
        """
        Obtener módulos ordenados para polling
        Solo módulos con dirección RS485 válida
        """
        try:
            with self.db.get_session() as session:
                return session.query(Module).filter(
                    and_(
                        Module.Address.isnot(None),
                        Module.Address > 0
                    )
                ).order_by(Module.OrdenEncuesta, Module.ModuloID).all()
        except Exception as e:
            log_error(e, "get_modules_for_polling")
            return []
    
    def update_module_config(self, module_id: int, **kwargs) -> bool:
        """
        Actualizar configuración de módulo
        """
        try:
            with self.db.get_session() as session:
                module = session.query(Module).filter(Module.ModuloID == module_id).first()
                
                if not module:
                    return False
                
                # Actualizar campos permitidos
                allowed_fields = [
                    'Nombre', 'Descripcion', 'Address', 'GrupoModulos',
                    'OrdenEncuesta', 'duracion_pulso', 'ValidacionTicket'
                ]
                
                for field, value in kwargs.items():
                    if field in allowed_fields and hasattr(module, field):
                        setattr(module, field, value)
                
                return True
                
        except Exception as e:
            log_error(e, f"update_module_config({module_id})")
            return False

class PersonManager:
    """
    Gestor de personas y permisos
    """
    
    def __init__(self):
        self.db = db_manager
    
    def get_person_by_identification(self, identification_number: str) -> Optional[Person]:
        """
        Buscar persona por número de identificación
        """
        try:
            with self.db.get_session() as session:
                identification = session.query(Identification).filter(
                    Identification.Numero == identification_number
                ).first()
                
                if not identification:
                    return None
                
                person_relation = session.query(PersonIdentification).filter(
                    PersonIdentification.IdentificacionID == identification.IdentificacionID
                ).first()
                
                if not person_relation:
                    return None
                
                return session.query(Person).filter(
                    Person.PersonaID == person_relation.PersonaID
                ).first()
                
        except Exception as e:
            log_error(e, f"get_person_by_identification({identification_number})")
            return None
    
    def get_person_groups(self, person_id: int) -> List[Group]:
        """
        Obtener grupos de una persona
        """
        try:
            with self.db.get_session() as session:
                group_relations = session.query(PersonGroup).filter(
                    PersonGroup.PersonaID == person_id
                ).all()
                
                group_ids = [gr.GrupoID for gr in group_relations]
                
                return session.query(Group).filter(
                    Group.GrupoID.in_(group_ids)
                ).all()
                
        except Exception as e:
            log_error(e, f"get_person_groups({person_id})")
            return []
    
    def is_person_active(self, person_id: int, check_datetime: Optional[datetime] = None) -> bool:
        """
        Verificar si una persona está activa en fecha específica
        """
        if check_datetime is None:
            check_datetime = datetime.now()
        
        try:
            with self.db.get_session() as session:
                person = session.query(Person).filter(Person.PersonaID == person_id).first()
                
                if not person:
                    return False
                
                # Verificar vigencia
                if person.FechaInicio and check_datetime < person.FechaInicio:
                    return False
                
                if person.FechaFin and check_datetime > person.FechaFin:
                    return False
                
                return True
                
        except Exception as e:
            log_error(e, f"is_person_active({person_id})")
            return False

# =======================================================
# FUNCIONES DE CONVENIENCIA
# =======================================================

def validate_access(identification_number: str, module_id: int) -> AccessResult:
    """
    Función de conveniencia para validar acceso
    """
    movement_manager = MovementManager()
    return movement_manager.validate_identification(identification_number, module_id)

def create_access_movement(identification_number: str, module_id: int, 
                          direction: str = "Entrada") -> Tuple[bool, Optional[int]]:
    """
    Función de conveniencia para crear movimiento de acceso
    """
    movement_manager = MovementManager()
    return movement_manager.create_movement(identification_number, module_id, 
                                          direction=direction)

def create_parking_ticket(module_id: int) -> Tuple[bool, Optional[int]]:
    """
    Función de conveniencia para crear ticket de estacionamiento
    """
    ticket_manager = TicketManager()
    return ticket_manager.create_ticket(module_id)

def process_parking_exit(ticket_number: int, module_id: int) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Función de conveniencia para procesar salida de estacionamiento
    """
    ticket_manager = TicketManager()
    return ticket_manager.process_ticket_exit(ticket_number, module_id)