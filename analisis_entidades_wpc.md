# 📊 Análisis de Entidades del Sistema WPC

## 🎯 **Entidades Centrales**

### **1. Módulos de Control (`mdl`)**
- **Función:** Dispositivos físicos (barreras, molinetes, puertas)
- **Campos clave:**
  - `ModuloID` - Identificador único
  - `Address` - Dirección RS485 para comunicación serie
  - `GrupoModulos` - Agrupación lógica
  - `OrdenEncuesta` - Secuencia de polling
  - `ValidacionTicket` - Si requiere validación de tickets

### **2. Movimientos (`mvt`)**
- **Función:** Registro de todos los eventos de acceso
- **Campos clave:**
  - `MovimientoID` - ID único (algoritmo especial basado en fecha)
  - `ModuloID` - Módulo donde ocurrió el evento
  - `IdentificacionID` - Tarjeta/código utilizado
  - `FechaHora` - Timestamp del evento

### **3. Identificaciones (`idn`)**
- **Función:** Tarjetas de proximidad, códigos de barras
- **Campos clave:**
  - `IdentificacionID` - ID único
  - `Numero` - Código visible de la tarjeta

### **4. Personas (`per`)**
- **Función:** Usuarios del sistema de acceso
- **Campos clave:**
  - `PersonaID` - ID único
  - `Apellido`, `Nombre` - Datos personales
  - `FechaInicio`, `FechaFin` - Período de validez

### **5. Tickets (`tck` y `tckhst`)**
- **Función:** Sistema de estacionamiento con tickets
- **Tablas:**
  - `tck` - Tickets activos (vehículos dentro)
  - `tckhst` - Historial de tickets (vehículos que salieron)

## 🔗 **Relaciones Principales**

### **Persona ↔ Identificación**
```
per (1) ←→ (N) peridn ←→ (N) idn
```
- Una persona puede tener múltiples tarjetas
- Una tarjeta puede ser compartida (raro, pero posible)

### **Módulo ↔ Movimiento**
```
mdl (1) ←→ (N) mvt
```
- Cada movimiento pertenece a un módulo específico

### **Identificación ↔ Movimiento**
```
idn (1) ←→ (N) mvt
```
- Cada movimiento está asociado a una identificación

### **Grupos y Perfiles**
```
per ←→ pergru ←→ gru (grupos)
gru ←→ grumdlprf ←→ prf (perfiles de acceso)
```
- Sistema de permisos basado en grupos y perfiles horarios

## 🎛️ **Sistema de Categorías (EAV)**
El sistema utiliza un patrón **Entity-Attribute-Value** extensivo:

- `cat` - Categorías de atributos
- `catval` - Valores posibles para cada categoría
- `*catval` - Tablas que relacionan entidades con categorías

**Ejemplo:** Una persona puede tener categoría "Tipo Usuario" con valor "Empleado"

## 🏗️ **Arquitectura de Comunicación**

### **Protocolo RS485**
- Comunicación serie con módulos de hardware
- Polling cíclico para consultar estados
- Comandos específicos por tipo de módulo

### **Hardware Soportado**
- Placas controladoras: ST1660, VME100, Cash Park
- Dispositivos: barreras, molinetes, lectores de tarjetas

## 📸 **Integración de Cámaras**
- Sistema actual: GeoVision (ActiveX)
- Sistema propuesto: Hikvision (API REST)
- Captura automática en eventos de acceso

## 🎫 **Sistema de Tickets**
Manejo específico para estacionamientos:
- Generación automática de tickets numerados
- Control de entrada/salida con validación temporal
- Cálculo de tarifas por tiempo de estadía