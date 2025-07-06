# scripts/test_cameras.py
"""
Script para probar el sistema de cámaras
"""

def test_hikvision_system():
    """
    Script de prueba completo del sistema Hikvision
    """
    print("=== Test Sistema de Cámaras Hikvision ===")
    
    # Inicializar componentes
    camera_manager = HikvisionManager()
    image_processor = ImageProcessor()
    config_manager = CameraConfigurationManager()
    
    try:
        # 1. Inicializar sistema
        print("\n1. Inicializando sistema...")
        if camera_manager.initialize():
            print("✓ Sistema inicializado correctamente")
        else:
            print("✗ Error en inicialización")
            return False
        
        # 2. Mostrar estadísticas
        print("\n2. Estadísticas del sistema:")
        stats = camera_manager.get_system_statistics()
        for key, value in stats.items():
            print(f"   {key}: {value}")
        
        # 3. Probar captura de imágenes
        print("\n3. Probando captura de imágenes:")
        test_results = camera_manager.test_all_cameras()
        
        for module_id, success in test_results.items():
            status = "✓ OK" if success else "✗ FAIL"
            print(f"   Módulo {module_id}: {status}")
        
        # 4. Test de procesamiento de imágenes
        print("\n4. Test de procesamiento:")
        test_image_path = config_manager.storage.base_directory / "test/sample.jpg"
        
        if test_image_path.exists():
            # Crear thumbnail
            thumb_path = image_processor.create_thumbnail(test_image_path)
            if thumb_path:
                print("   ✓ Thumbnail creado")
            
            # Agregar marca de agua
            if image_processor.add_watermark(test_image_path, "WPC Test"):
                print("   ✓ Marca de agua agregada")
            
            # Mejorar imagen
            if image_processor.enhance_image(test_image_path):
                print("   ✓ Imagen mejorada")
        
        # 5. Limpieza
        print("\n5. Limpieza:")
        deleted_count = config_manager.cleanup_old_images()
        print(f"   {deleted_count} archivos antiguos eliminados")
        
        print("\n=== Test completado exitosamente ===")
        return True
        
    except Exception as e:
        print(f"\n✗ Error durante test: {e}")
        return False
    
    finally:
        camera_manager.cleanup()

if __name__ == "__main__":
    # Configurar logging para test
    setup_logging()
    
    # Ejecutar test
    success = test_hikvision_system()
    exit(0 if success else 1)