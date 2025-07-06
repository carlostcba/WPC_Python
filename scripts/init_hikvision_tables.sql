"""
Crear tablas necesarias para sistema Hikvision
"""

CREATE_HIKVISION_TABLES = """
-- Tabla de configuración de dispositivos Hikvision
CREATE TABLE configuracion_hikvision (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    Nombre NVARCHAR(100) NOT NULL,
    Valor NVARCHAR(MAX) NOT NULL,
    TipoDato NVARCHAR(20) DEFAULT 'STRING',
    Categoria NVARCHAR(50) DEFAULT 'GENERAL',
    Descripcion NVARCHAR(500),
    ModificablePorUsuario BIT DEFAULT 1,
    Activo BIT DEFAULT 1,
    FechaModificacion DATETIME DEFAULT GETDATE()
);

-- Tabla de mapeo de cámaras Hikvision
CREATE TABLE hikvision_cameras (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    device_id NVARCHAR(50) NOT NULL,
    channel INT NOT NULL,
    camera_legacy_id NVARCHAR(10), -- Para mapear con tabla mdlcam
    description NVARCHAR(200),
    enabled BIT DEFAULT 1,
    created_date DATETIME DEFAULT GETDATE()
);

-- Tabla de imágenes de movimientos (opcional)
CREATE TABLE movement_images (
    ID INT IDENTITY(1,1) PRIMARY KEY,
    MovimientoID BIGINT NOT NULL,
    ImagePath NVARCHAR(500) NOT NULL,
    CaptureDateTime DATETIME DEFAULT GETDATE(),
    FileSize INT,
    ImageType NVARCHAR(10) DEFAULT 'JPG'
);

-- Datos de ejemplo para configuración
INSERT INTO configuracion_hikvision (Nombre, Valor, Categoria, Descripcion) VALUES
('nvr_main', '{"host": "192.168.1.100", "username": "admin", "password": "", "type": "nvr", "max_channels": 16}', 'DEVICE', 'NVR principal del sistema'),
('camera_quality', '{"resolution": "1920x1080", "fps": 25, "bitrate": 2048}', 'QUALITY', 'Configuración de calidad por defecto'),
('storage_settings', '{"retention_days": 30, "auto_cleanup": true, "max_file_size_mb": 10}', 'STORAGE', 'Configuración de almacenamiento');

-- Datos de ejemplo para mapeo de cámaras
INSERT INTO hikvision_cameras (device_id, channel, camera_legacy_id, description) VALUES
('nvr_main', 1, '1', 'Entrada Principal'),
('nvr_main', 2, '2', 'Salida Principal'),
('nvr_main', 3, '3', 'Entrada Peatonal'),
('nvr_main', 4, '4', 'Salida Peatonal');
"""