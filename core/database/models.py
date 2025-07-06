# core/database/models.py
"""
Modelos SQLAlchemy para las tablas principales del sistema WPC
Basado en el esquema SQL Server existente - 100% compatible con VB6
"""
from sqlalchemy import (
    Column, Integer, BigInteger, String, DateTime, Boolean, 
    Text, ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List

# Base declarativa importada desde config
from config.database import Base

# =======================================================
# MODELOS PRINCIPALES
# =======================================================

class Movement(Base):
    """
    Tabla de movimientos - mvt
    Registra todos los eventos de acceso al sistema
    """
    __tablename__ = 'mvt'
    
    # Campos principales
    MovimientoID = Column(BigInteger, primary_key=True, comment="ID único del movimiento")
    ModuloID = Column(Integer, ForeignKey('mdl.ModuloID'), nullable=False,
                      comment="ID del módulo donde ocurrió")
    IdentificacionID = Column(Integer, ForeignKey('idn.IdentificacionID'),
                             nullable=False,
                             comment="ID de la identificación usada")
    FechaHora = Column(DateTime, nullable=True, default=func.now(), comment="Timestamp del evento")
    
    # Índices para optimización
    __table_args__ = (
        Index('Index_2', 'FechaHora'),
        Index('Index_3', 'IdentificacionID', 'FechaHora'),
        {'comment': 'Registro de movimientos de acceso'}
    )
    
    # Relaciones
    module = relationship("Module", back_populates="movements", lazy="select")
    identification = relationship("Identification", back_populates="movements", lazy="select")
    
    def __repr__(self):
        return f"<Movement(id={self.MovimientoID}, module={self.ModuloID}, fecha={self.FechaHora})>"

class Module(Base):
    """
    Tabla de módulos - mdl
    Configuración de módulos de hardware (barreras, molinetes, etc.)
    """
    __tablename__ = 'mdl'
    
    # Campos principales
    ModuloID = Column(Integer, primary_key=True, comment="ID único del módulo")
    Nombre = Column(String(32), nullable=True, comment="Nombre descriptivo")
    Descripcion = Column(Text, nullable=True, comment="Descripción detallada")
    Address = Column(Integer, nullable=True, comment="Dirección RS485 para comunicación")
    ModuloEntradaID = Column(Integer, nullable=False, comment="ID módulo de entrada relacionado")
    ModuloSalidaID = Column(Integer, nullable=False, comment="ID módulo de salida relacionado")
    GrupoModulos = Column(Integer, nullable=True, comment="Agrupación lógica de módulos")
    OrdenEncuesta = Column(Integer, nullable=True, comment="Orden en el polling cíclico")
    duracion_pulso = Column(BigInteger, nullable=True, default=0, comment="Duración pulso en ms")
    ValidacionTicket = Column(Boolean, nullable=True, default=False, comment="Requiere validación de tickets")
    
    # Restricciones
    __table_args__ = (
        UniqueConstraint('Nombre', name='mdl$Nombre'),
        {'comment': 'Configuración de módulos de hardware'}
    )
    
    # Relaciones
    movements = relationship("Movement", back_populates="module", lazy="dynamic")
    camera_config = relationship("ModuleCamera", back_populates="module", uselist=False)
    
    def __repr__(self):
        return f"<Module(id={self.ModuloID}, nombre='{self.Nombre}', address={self.Address})>"

class Identification(Base):
    """
    Tabla de identificaciones - idn
    Tarjetas de proximidad, códigos de barras, etc.
    """
    __tablename__ = 'idn'
    
    # Campos principales
    IdentificacionID = Column(Integer, primary_key=True, comment="ID único de identificación")
    Numero = Column(String(32), nullable=True, comment="Número visible de la tarjeta/código")
    
    # Restricciones
    __table_args__ = (
        UniqueConstraint('Numero', name='idn$IndiceUnico'),
        Index('IndiceNumero', 'Numero'),
        {'comment': 'Tarjetas y códigos de identificación'}
    )
    
    # Relaciones
    movements = relationship("Movement", back_populates="identification", lazy="dynamic")
    person_relations = relationship("PersonIdentification", back_populates="identification")
    
    def __repr__(self):
        return f"<Identification(id={self.IdentificacionID}, numero='{self.Numero}')>"

class Person(Base):
    """
    Tabla de personas - per
    Usuarios del sistema de control de acceso
    """
    __tablename__ = 'per'
    
    # Campos principales
    PersonaID = Column(Integer, primary_key=True, comment="ID único de persona")
    Apellido = Column(String(64), nullable=True, comment="Apellido")
    Nombre = Column(String(64), nullable=True, comment="Nombre")
    Sexo = Column(String(1), nullable=True, comment="M/F")
    FechaNacimiento = Column(DateTime, nullable=True, comment="Fecha de nacimiento")
    Pais = Column(String(32), nullable=True, comment="País")
    
    # Campos de auditoría
    CreationDate = Column(DateTime, nullable=True, comment="Fecha creación")
    CREATEdByID = Column(Integer, nullable=False, comment="Usuario que creó")
    LastUpdateDate = Column(DateTime, nullable=True, comment="Última modificación")
    LastUpdateDateByID = Column(Integer, nullable=False, comment="Usuario que modificó")
    
    # Vigencia
    FechaInicio = Column(DateTime, nullable=False, comment="Inicio de vigencia")
    FechaFin = Column(DateTime, nullable=False, comment="Fin de vigencia")
    
    # Índices
    __table_args__ = (
        Index('Index_2', 'Apellido', 'Nombre'),
        {'comment': 'Personas con acceso al sistema'}
    )
    
    # Relaciones
    identification_relations = relationship("PersonIdentification", back_populates="person")
    group_relations = relationship("PersonGroup", back_populates="person")
    
    @property
    def full_name(self) -> str:
        """Nombre completo formato VB6: Apellido, Nombre"""
        if self.Apellido and self.Nombre:
            return f"{self.Apellido}, {self.Nombre}"
        return self.Apellido or self.Nombre or ""
    
    def __repr__(self):
        return f"<Person(id={self.PersonaID}, nombre='{self.full_name}')>"

class Ticket(Base):
    """
    Tabla de tickets activos - tck
    Tickets de estacionamiento que están dentro del sistema
    """
    __tablename__ = 'tck'
    
    # Campos principales
    TicketID = Column(BigInteger, primary_key=True, comment="ID único del ticket")
    Numero = Column(BigInteger, nullable=False, comment="Número visible del ticket")
    FechaHoraIngreso = Column(DateTime, nullable=False, default='1899-12-31 00:00:00', comment="Timestamp de ingreso")
    ModuloIngresoID = Column(BigInteger, nullable=False, comment="Módulo donde ingresó")
    Validado = Column(Boolean, nullable=True, default=False, comment="Si fue validado en egreso")
    
    # Índices
    __table_args__ = (
        Index('Numero', 'Numero'),
        {'comment': 'Tickets activos en el sistema'}
    )
    
    def __repr__(self):
        return f"<Ticket(id={self.TicketID}, numero={self.Numero}, ingreso={self.FechaHoraIngreso})>"

class TicketHistory(Base):
    """
    Tabla de historial de tickets - tckhst
    Tickets que ya salieron del sistema
    """
    __tablename__ = 'tckhst'
    
    # Campos principales
    TicketID = Column(BigInteger, primary_key=True, comment="ID único del ticket")
    Numero = Column(BigInteger, nullable=False, comment="Número visible del ticket")
    FechaHoraIngreso = Column(DateTime, nullable=False, default='1899-12-31 00:00:00', comment="Timestamp de ingreso")
    ModuloIngresoID = Column(BigInteger, nullable=False, comment="Módulo donde ingresó")
    FechaHoraSalida = Column(DateTime, nullable=False, default='1899-12-31 00:00:00', comment="Timestamp de salida")
    ModuloSalidaID = Column(BigInteger, nullable=False, comment="Módulo donde salió")
    
    # Índices
    __table_args__ = (
        Index('Numero', 'Numero'),
        {'comment': 'Historial de tickets procesados'}
    )
    
    @property
    def duration_minutes(self) -> Optional[int]:
        """Calcular duración de estadía en minutos"""
        if self.FechaHoraSalida and self.FechaHoraIngreso:
            delta = self.FechaHoraSalida - self.FechaHoraIngreso
            return int(delta.total_seconds() / 60)
        return None
    
    def __repr__(self):
        return f"<TicketHistory(numero={self.Numero}, entrada={self.FechaHoraIngreso}, salida={self.FechaHoraSalida})>"

# =======================================================
# TABLAS DE RELACIÓN (MUCHOS A MUCHOS)
# =======================================================

class PersonIdentification(Base):
    """
    Relación personas-identificaciones - peridn
    Una persona puede tener múltiples tarjetas
    """
    __tablename__ = 'peridn'
    
    PersonaID = Column(Integer, ForeignKey('per.PersonaID'), primary_key=True)
    IdentificacionID = Column(Integer, ForeignKey('idn.IdentificacionID'), primary_key=True)
    
    # Índices
    __table_args__ = (
        Index('Index_2', 'IdentificacionID'),
        {'comment': 'Relación personas-identificaciones'}
    )
    
    # Relaciones
    person = relationship("Person", back_populates="identification_relations")
    identification = relationship("Identification", back_populates="person_relations")

class Group(Base):
    """
    Tabla de grupos - gru
    Agrupaciones lógicas de personas para permisos
    """
    __tablename__ = 'gru'
    
    GrupoID = Column(Integer, primary_key=True, comment="ID único del grupo")
    Nombre = Column(String(32), nullable=True, comment="Nombre del grupo")
    Descripcion = Column(Text, nullable=True, comment="Descripción del grupo")
    
    # Restricciones
    __table_args__ = (
        UniqueConstraint('Nombre', name='gru$Nombre'),
        {'comment': 'Grupos de personas para control de acceso'}
    )
    
    # Relaciones
    person_relations = relationship("PersonGroup", back_populates="group")

class PersonGroup(Base):
    """
    Relación personas-grupos - pergru
    """
    __tablename__ = 'pergru'
    
    PersonaID = Column(Integer, ForeignKey('per.PersonaID'), primary_key=True)
    GrupoID = Column(Integer, ForeignKey('gru.GrupoID'), primary_key=True)
    CategoriaID = Column(Integer, nullable=False, comment="Categoría de la relación")
    ValorID = Column(Integer, nullable=False, comment="Valor de la categoría")
    
    # Relaciones
    person = relationship("Person", back_populates="group_relations")
    group = relationship("Group", back_populates="person_relations")

# =======================================================
# TABLAS AUXILIARES
# =======================================================

class ModuleCamera(Base):
    """
    Configuración de cámaras por módulo - mdlcam
    """
    __tablename__ = 'mdlcam'
    
    ModuloID = Column(BigInteger, ForeignKey('mdl.ModuloID'), primary_key=True)
    Camara = Column(String(2), nullable=False, default='N', comment="Configuración de cámara")
    
    # Relaciones
    module = relationship("Module", back_populates="camera_config")

class Category(Base):
    """
    Tabla de categorías - cat
    Sistema EAV (Entity-Attribute-Value) para atributos dinámicos
    """
    __tablename__ = 'cat'
    
    CategoriaID = Column(Integer, primary_key=True, comment="ID único de categoría")
    Nombre = Column(String(32), nullable=True, comment="Nombre de la categoría")
    SystemParameter = Column(Integer, nullable=True, comment="Parámetro del sistema")
    
    # Restricciones
    __table_args__ = (
        UniqueConstraint('Nombre', name='cat$Nombre'),
        {'comment': 'Categorías para sistema EAV'}
    )

class CategoryValue(Base):
    """
    Valores de categorías - catval
    """
    __tablename__ = 'catval'
    
    CategoriaID = Column(Integer, ForeignKey('cat.CategoriaID'), primary_key=True)
    ValorID = Column(Integer, primary_key=True)
    Nombre = Column(String(32), nullable=True, comment="Nombre del valor")
    SystemParameter = Column(Integer, nullable=True, comment="Parámetro del sistema")
    
    # Restricciones
    __table_args__ = (
        UniqueConstraint('CategoriaID', 'Nombre', name='catval$CategoriaID'),
        {'comment': 'Valores posibles para cada categoría'}
    )

class MovementCategoryValue(Base):
    """
    Categorías de movimientos - mvtcatval
    Permite asociar atributos dinámicos a movimientos
    """
    __tablename__ = 'mvtcatval'
    
    MovimientoID = Column(BigInteger, ForeignKey('mvt.MovimientoID'), primary_key=True)
    CategoriaID = Column(Integer, primary_key=True)
    ValorID = Column(Integer, primary_key=True)

# =======================================================
# FUNCIONES DE UTILIDAD
# =======================================================

def get_active_tickets() -> List[Ticket]:
    """
    Obtener todos los tickets activos en el sistema
    Equivalente a consultas VB6 sobre tabla tck
    """
    from config.database import db_manager
    with db_manager.get_session() as session:
        return session.query(Ticket).all()

def get_person_by_identification(identification_number: str) -> Optional[Person]:
    """
    Buscar persona por número de identificación
    Equivalente a búsquedas frecuentes en VB6
    """
    from config.database import db_manager
    with db_manager.get_session() as session:
        identification = session.query(Identification).filter(
            Identification.Numero == identification_number
        ).first()
        
        if identification:
            person_relation = session.query(PersonIdentification).filter(
                PersonIdentification.IdentificacionID == identification.IdentificacionID
            ).first()
            
            if person_relation:
                return session.query(Person).filter(
                    Person.PersonaID == person_relation.PersonaID
                ).first()
        
        return None

def get_module_by_address(address: int) -> Optional[Module]:
    """
    Buscar módulo por dirección RS485
    """
    from config.database import db_manager
    with db_manager.get_session() as session:
        return session.query(Module).filter(Module.Address == address).first()