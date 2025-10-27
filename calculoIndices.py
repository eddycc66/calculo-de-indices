from qgis.core import QgsRasterLayer, QgsProject
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis import processing
import os

# Nombres de las capas ráster cargadas
banda_roja = 'RT_L1C_T20HNC_A041849_20250311T140855_B04'
banda_verde = 'RT_L1C_T20HNC_A041849_20250311T140855_B03'
banda_azul = 'RT_L1C_T20HNC_A041849_20250311T140855_B02'
banda_nir = 'RT_L1C_T20HNC_A041849_20250311T140855_B08'
banda_re5 = 'RT_L1C_T20HNC_A041849_20250311T140855_B05'
banda_nir2 = 'RT_L1C_T20HNC_A041849_20250311T140855_B8A'

# Capa de área de interés
area_interes = 'area_interes32720'

# Ruta de salida para los archivos generados
output_dir = "C:/Users/EDWIN/Documents/QGIS_Output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Función para verificar y obtener una capa
def obtener_capa(nombre):
    layers = QgsProject.instance().mapLayersByName(nombre)
    if not layers:
        print(f"Error: No se encontró la capa {nombre}")
        return None
    layer = layers[0]
    if not layer.isValid():
        print(f"Error: La capa {nombre} no es válida")
        return None
    return layer

# Función para redimensionar bandas usando GDAL
def redimensionar_banda_gdal(banda_entrada, nombre_salida, referencia_10m):
    """Redimensiona una banda usando GDAL Warp"""
    capa_entrada = obtener_capa(banda_entrada)
    if not capa_entrada:
        return None
        
    capa_ref = obtener_capa(referencia_10m)
    if not capa_ref:
        return None
        
    output_path = os.path.join(output_dir, nombre_salida + '.tif')
    
    try:
        params = {
            'INPUT': capa_entrada,
            'SOURCE_CRS': capa_entrada.crs(),
            'TARGET_CRS': capa_ref.crs(),
            'RESAMPLING': 0,  # Vecino más cercano
            'TARGET_RESOLUTION': 10,  # 10 metros
            'TARGET_EXTENT': capa_ref.extent(),
            'TARGET_EXTENT_CRS': capa_ref.crs(),
            'OUTPUT': output_path
        }
        
        processing.run("gdal:warpreproject", params)
        
        if os.path.exists(output_path):
            nueva_capa = QgsRasterLayer(output_path, nombre_salida)
            if nueva_capa.isValid():
                QgsProject.instance().addMapLayer(nueva_capa)
                return nueva_capa
            else:
                return None
        else:
            return None
    except Exception as e:
        print(f"Error redimensionando {banda_entrada} con GDAL: {str(e)}")
        return None

# Función para calcular índices usando QgsRasterCalculator
def calcular_indice_con_calculator(expresion, nombre_salida, bandas_dict):
    """Calcula índices usando QgsRasterCalculator directamente"""
    
    # Obtener una capa de referencia para dimensiones
    capa_ref = next(iter(bandas_dict.values()))
    
    # Crear entradas para el calculator
    entradas = []
    for ref, capa in bandas_dict.items():
        entry = QgsRasterCalculatorEntry()
        entry.ref = ref + '@1'  # Añadir @1 para el número de banda
        entry.raster = capa
        entry.bandNumber = 1
        entradas.append(entry)

    output_path = os.path.join(output_dir, nombre_salida + '.tif')
    
    try:
        # Crear el calculador
        calc = QgsRasterCalculator(
            expresion,
            output_path,
            'GTiff',
            capa_ref.extent(),
            capa_ref.width(),
            capa_ref.height(),
            entradas
        )
        
        # Ejecutar el cálculo
        result = calc.processCalculation()
        
        if result == 0:
            print(f"✓ Índice {nombre_salida} calculado correctamente")
            # Cargar la capa resultante
            if os.path.exists(output_path):
                nueva_capa = QgsRasterLayer(output_path, nombre_salida)
                if nueva_capa.isValid():
                    QgsProject.instance().addMapLayer(nueva_capa)
                    return True
                else:
                    print(f"✗ La capa {nombre_salida} no es válida")
                    return False
            else:
                print(f"✗ No se creó el archivo {output_path}")
                return False
        else:
            print(f"✗ Error en cálculo de {nombre_salida}. Código: {result}")
            return False
            
    except Exception as e:
        print(f"✗ Excepción calculando {nombre_salida}: {str(e)}")
        return False

# Función para recortar índices
def recortar_indice(indice_nombre):
    input_path = os.path.join(output_dir, indice_nombre + '.tif')
    
    if not os.path.exists(input_path):
        print(f"✗ No se encontró {input_path}")
        return False
    
    indice_layer = QgsRasterLayer(input_path, indice_nombre)
    if not indice_layer.isValid():
        print(f"✗ No se pudo cargar {indice_nombre}")
        return False
    
    area_layer = obtener_capa(area_interes)
    if not area_layer:
        print(f"✗ No se encontró el área de interés {area_interes}")
        return False
    
    output_clipped = os.path.join(output_dir, indice_nombre + '_clipped.tif')
    
    try:
        params = {
            'INPUT': indice_layer,
            'MASK': area_layer,
            'SOURCE_CRS': indice_layer.crs(),
            'TARGET_CRS': indice_layer.crs(),
            'NODATA': -9999,
            'CROP_TO_CUTLINE': True,
            'KEEP_RESOLUTION': True,
            'OUTPUT': output_clipped
        }
        
        processing.run("gdal:cliprasterbymasklayer", params)
        
        if os.path.exists(output_clipped):
            print(f"✓ {indice_nombre} recortado correctamente")
            clipped_layer = QgsRasterLayer(output_clipped, indice_nombre + '_clipped')
            if clipped_layer.isValid():
                QgsProject.instance().addMapLayer(clipped_layer)
                return True
        return False
            
    except Exception as e:
        print(f"✗ Error recortando {indice_nombre}: {str(e)}")
        return False

# PROGRAMA PRINCIPAL CORREGIDO
print("=== INICIANDO CÁLCULO DE ÍNDICES (VERSIÓN CORREGIDA) ===")

# 1. Primero preparar todas las bandas necesarias
print("Paso 1: Preparando bandas...")

# Obtener bandas base de 10m
bandas_10m = {
    'B02': obtener_capa(banda_azul),
    'B03': obtener_capa(banda_verde),
    'B04': obtener_capa(banda_roja),
    'B08': obtener_capa(banda_nir)
}

# Verificar que tenemos las bandas básicas
for ref, capa in bandas_10m.items():
    if not capa:
        print(f"✗ Error: No se encontró la banda {ref}")
        exit()

print("✓ Bandas base de 10m cargadas correctamente")

# 2. Redimensionar bandas de 20m a 10m si es necesario
print("\nPaso 2: Redimensionando bandas de 20m a 10m...")

# Redimensionar B05 (20m) a 10m
b05_10m = redimensionar_banda_gdal(banda_re5, 'B05_10m', banda_roja)
if b05_10m:
    bandas_10m['B05'] = b05_10m
    print("✓ B05 redimensionada a 10m")
else:
    print("✗ No se pudo redimensionar B05")

# Redimensionar B8A (20m) a 10m
b8a_10m = redimensionar_banda_gdal(banda_nir2, 'B8A_10m', banda_roja)
if b8a_10m:
    bandas_10m['B8A'] = b8a_10m
    print("✓ B8A redimensionada a 10m")
else:
    print("✗ No se pudo redimensionar B8A")

# 3. Calcular índices
print("\nPaso 3: Calculando índices...")

# Definir índices con sus expresiones
# NOTA: Usar la sintaxis correcta para QgsRasterCalculator
indices = [
    ('NDVI', '("B08@1" - "B04@1") / ("B08@1" + "B04@1")'),
    ('GNDVI', '("B08@1" - "B03@1") / ("B08@1" + "B03@1")'),
    ('EVI', '2.5 * (("B08@1" - "B04@1") / ("B08@1" + 6 * "B04@1" - 7.5 * "B02@1" + 1))')
]

# Añadir NDRE solo si tenemos las bandas redimensionadas
if 'B05' in bandas_10m and 'B8A' in bandas_10m:
    indices.append(('NDRE', '("B8A@1" - "B05@1") / ("B8A@1" + "B05@1")'))
    print("✓ NDRE incluido en los cálculos")
else:
    print("✗ NDRE omitido (faltan bandas redimensionadas)")

indices_exitosos = []

for nombre, expresion in indices:
    print(f"\n--- Calculando {nombre} ---")
    print(f"Expresión: {expresion}")
    
    # Filtrar solo las bandas necesarias para este índice
    bandas_necesarias = {}
    if 'B02@1' in expresion and 'B02' in bandas_10m:
        bandas_necesarias['B02'] = bandas_10m['B02']
    if 'B03@1' in expresion and 'B03' in bandas_10m:
        bandas_necesarias['B03'] = bandas_10m['B03']
    if 'B04@1' in expresion and 'B04' in bandas_10m:
        bandas_necesarias['B04'] = bandas_10m['B04']
    if 'B05@1' in expresion and 'B05' in bandas_10m:
        bandas_necesarias['B05'] = bandas_10m['B05']
    if 'B08@1' in expresion and 'B08' in bandas_10m:
        bandas_necesarias['B08'] = bandas_10m['B08']
    if 'B8A@1' in expresion and 'B8A' in bandas_10m:
        bandas_necesarias['B8A'] = bandas_10m['B8A']
    
    if len(bandas_necesarias) == 0:
        print(f"✗ No se encontraron bandas para {nombre}")
        continue
        
    if calcular_indice_con_calculator(expresion, nombre, bandas_necesarias):
        if recortar_indice(nombre):
            indices_exitosos.append(nombre)
            print(f"✓ {nombre} procesado completamente")
    else:
        print(f"✗ Falló el procesamiento de {nombre}")

# 4. Resumen final
print("\n" + "="*50)
print("RESUMEN FINAL")
print("="*50)
if indices_exitosos:
    print(f"Índices calculados exitosamente: {', '.join(indices_exitosos)}")
else:
    print("No se pudo calcular ningún índice")
print(f"Archivos guardados en: {output_dir}")

# Información adicional
print("\nINFORMACIÓN ADICIONAL:")
print("1. Los archivos terminados en '_clipped.tif' son los resultados finales")
print("2. Si algún índice falló, verifica que todas las bandas estén en la misma resolución")
print("3. Las bandas redimensionadas se han añadido al proyecto como 'B05_10m' y 'B8A_10m'")