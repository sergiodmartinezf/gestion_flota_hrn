"""
Utilidades para exportación y generación de reportes
"""
import requests
from django.conf import settings
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse
from datetime import datetime
from .models import normalizar_estado_oc, normalizar_estado_visual


def crear_estilos_excel():
    """
    Crea y retorna un diccionario de estilos para Excel.
    """
    # Estilo para títulos
    estilo_titulo = Font(name='Arial', size=14, bold=True)
    
    # Estilo para encabezados
    estilo_encabezado_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    estilo_encabezado_fill = PatternFill(start_color='366092', end_color='366092', fill_type='solid')
    
    # Estilo para centrado
    centrado = Alignment(horizontal='center', vertical='center')
    
    # Estilo para alineación derecha
    derecha = Alignment(horizontal='right', vertical='center')
    
    # Borde
    borde = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    return {
        'titulo': estilo_titulo,
        'encabezado_font': estilo_encabezado_font,
        'encabezado_fill': estilo_encabezado_fill,
        'centrado': centrado,
        'derecha': derecha,
        'borde': borde,
    }


def consultar_oc_mercado_publico(codigo_oc):
    """
    Consulta la API de Mercado Público y retorna un diccionario con datos limpios
    """
    try:
        ticket = getattr(settings, 'MERCADO_PUBLICO_TICKET', None)

        if not ticket or ticket == 'BLABLABLA':
            return {'error': 'Ticket no configurado.'}
        
        url = f"https://api.mercadopublico.cl/servicios/v1/publico/ordenesdecompra.json?codigo={codigo_oc}&ticket={ticket}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
        }
        
        response = requests.get(url, headers=headers, timeout=30, verify=True)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get('Cantidad', 0) == 0:
            return {'error': f'No se encontró la orden de compra {codigo_oc}.'}

        if 'Listado' not in data or not data['Listado']:
            return {'error': 'La API no devolvió datos en el formato esperado.'}

        oc_data = data['Listado'][0]

        # Extraer items
        items_str = ""
        if 'Listado' in oc_data.get('Items', {}):
            items = []
            lista = oc_data['Items']['Listado']
            if isinstance(lista, dict):
                lista = [lista]
                
            for item in lista:
                nombre = item.get('Producto', '')
                espec = item.get('EspecificacionComprador', '')
                items.append(f"{nombre} - {espec}")
            
            items_str = "\n".join(items)

        # Datos básicos
        estado_original = oc_data.get('Estado', 'Emitida')
        
        estado_normalizado = normalizar_estado_oc(estado_original)
        estado_visual = normalizar_estado_visual(estado_normalizado)

        # Datos básicos
        info_limpia = {
            'codigo': oc_data.get('Codigo', codigo_oc),
            'estado_original': estado_original,
            'fecha_emision': oc_data.get('Fechas', {}).get('FechaCreacion', '').split('T')[0],
            'descripcion': oc_data.get('Descripcion', oc_data.get('Nombre', f'Orden de compra {codigo_oc}'))[:500],
            'monto_neto': oc_data.get('TotalNeto', 0),
            'monto_total': oc_data.get('Total', 0),
            'impuestos': oc_data.get('Impuestos', 0),
            'proveedor_rut': oc_data.get('Proveedor', {}).get('RutSucursal', ''),
            'proveedor_nombre': oc_data.get('Proveedor', {}).get('Nombre', 'Proveedor Desconocido'),
            'id_licitacion': oc_data.get('CodigoLicitacion', ''),
            'items_str': items_str
        }
        
        # ========== EXTRACCIÓN DE DATOS CLAVE ==========
        texto_completo = f"{info_limpia['descripcion']} {items_str}".upper()
        
        # 1. Buscar CÓDIGO PRESUPUESTARIO (22.06.002.002)
        import re
        codigo_match = re.search(r'(\d{2}\.\d{2}\.\d{3}\.\d{3})', texto_completo)
        if codigo_match:
            info_limpia['codigo_presupuestario'] = codigo_match.group(1)
        else:
            # Intentar con formato 22-06-002
            codigo_match = re.search(r'(\d{2}-\d{2}-\d{3})', texto_completo)
            if codigo_match:
                info_limpia['codigo_presupuestario'] = codigo_match.group(1).replace('-', '.')
            else:
                info_limpia['codigo_presupuestario'] = None

        # 2. Buscar PATENTES con patrones mejorados
        patentes_encontradas = []

        # Nuevos patrones para capturar formatos específicos
        patrones_patentes = [
            r'\b(HR\.PG-25)\b',  # Patente específica de este caso
            r'\b([A-Z]{2}\.[A-Z]{2}-\d{2})\b',  # Formato XX.XX-XX (HR.PG-25)
            r'\b([A-Z]{2}-[A-Z]{2}-\d{2})\b',   # Formato XX-XX-XX (LX-FG-16)
            r'\b([A-Z]{2}\.[A-Z]{2}\d{2})\b',   # Formato XX.XXXX (HR.PG25)
            r'\b([A-Z]{4}\d{2})\b',             # Formato XXXXNN (HRPG25)
            r'\b([A-Z]{2}\d{4})\b',             # Formato XXNNNN
            r'Patente Vehículo\s+([A-Z0-9\.\-]+)',  # Buscar específicamente después de "Patente Vehículo"
        ]

        for patron in patrones_patentes:
            matches = re.findall(patron, texto_completo, re.IGNORECASE)
            if matches:
                print(f"Patrón '{patron}' encontró: {matches}")
                patentes_encontradas.extend(matches)

        # También buscar en todo el texto sin patrones específicos
        # Buscar cualquier cosa que parezca patente chilena
        if not patentes_encontradas:
            # Patrón general para patentes chilenas
            patron_general = r'\b([A-Z]{2}[\.\-]?[A-Z]{2}[\.\-]?\d{2,3})\b'
            matches_general = re.findall(patron_general, texto_completo, re.IGNORECASE)
            if matches_general:
                print(f"Patrón general encontró: {matches_general}")
                patentes_encontradas.extend(matches_general)

        # Limpiar y normalizar
        patentes_limpias = []
        for patente in set(patentes_encontradas):
            # Convertir a mayúsculas
            patente = patente.upper()
            
            # Si ya tiene formato con punto y guión (HR.PG-25), mantenerlo
            if re.match(r'^[A-Z]{2}\.[A-Z]{2}-\d{2}$', patente):
                patentes_limpias.append(patente)
            # Si tiene formato con guión (LX-FG-16), mantenerlo
            elif re.match(r'^[A-Z]{2}-[A-Z]{2}-\d{2}$', patente):
                patentes_limpias.append(patente)
            # Si tiene formato compacto (HRPG25), formatearlo
            elif re.match(r'^[A-Z]{4}\d{2}$', patente):
                patente_formateada = f"{patente[:2]}.{patente[2:4]}-{patente[4:]}"
                patentes_limpias.append(patente_formateada)
            else:
                # Mantener cualquier otro formato
                patentes_limpias.append(patente)

        info_limpia['patentes_posibles'] = patentes_limpias
        
        return info_limpia

    except Exception as e:
        return {'error': f'Error: {str(e)}'}

def exportar_reporte_excel(titulo, datos, columnas, nombre_archivo=None):
    """
    Genera un archivo Excel a partir de datos
    
    Args:
        titulo: Título del reporte
        datos: Lista de diccionarios con los datos
        columnas: Lista de tuplas (nombre_columna, clave_dato, formato)
        nombre_archivo: Nombre del archivo (opcional)
    
    Returns:
        HttpResponse con el archivo Excel
    """
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"
    
    estilos = crear_estilos_excel()
    
    # Título
    ws.merge_cells('A1:{}1'.format(get_column_letter(len(columnas))))
    celda_titulo = ws['A1']
    celda_titulo.value = titulo
    celda_titulo.font = estilos['titulo']
    celda_titulo.alignment = estilos['centrado']
    ws.row_dimensions[1].height = 25
    
    # Fecha de generación
    ws.merge_cells('A2:{}2'.format(get_column_letter(len(columnas))))
    celda_fecha = ws['A2']
    celda_fecha.value = f"Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    celda_fecha.alignment = estilos['centrado']
    ws.row_dimensions[2].height = 20
    
    # Encabezados
    fila_encabezado = 3
    for idx, (nombre_col, _, _) in enumerate(columnas, start=1):
        celda = ws.cell(row=fila_encabezado, column=idx)
        celda.value = nombre_col
        celda.font = estilos['encabezado_font']
        celda.fill = estilos['encabezado_fill']
        celda.alignment = estilos['centrado']
        celda.border = estilos['borde']
    
    ws.row_dimensions[fila_encabezado].height = 20
    
    # Datos
    fila_actual = fila_encabezado + 1
    for item in datos:
        for idx, (_, clave_dato, formato) in enumerate(columnas, start=1):
            celda = ws.cell(row=fila_actual, column=idx)
            valor = item.get(clave_dato, '')
            
            if formato == 'moneda':
                celda.value = float(valor) if valor else 0
                celda.number_format = '$#,##0'
            elif formato == 'decimal':
                celda.value = float(valor) if valor else 0
                celda.number_format = '#,##0.00'
            elif formato == 'entero':
                celda.value = int(valor) if valor else 0
            elif formato == 'fecha':
                if valor:
                    if hasattr(valor, 'strftime'):
                        celda.value = valor.strftime('%d/%m/%Y')
                    else:
                        celda.value = str(valor)
            else:
                celda.value = str(valor) if valor else ''
            
            celda.border = estilos['borde']
            if formato in ['moneda', 'decimal', 'entero']:
                celda.alignment = estilos['derecha']
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
        
        fila_actual += 1
    
    # Ajustar ancho de columnas
    for idx, (nombre_col, _, _) in enumerate(columnas, start=1):
        col_letter = get_column_letter(idx)
        # Ancho mínimo basado en el nombre de la columna
        ancho = max(len(nombre_col) + 2, 12)
        ws.column_dimensions[col_letter].width = ancho
    
    # Preparar respuesta
    if not nombre_archivo:
        nombre_archivo = f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    if not nombre_archivo.endswith('.xlsx'):
        nombre_archivo += '.xlsx'
    
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    
    wb.save(response)
    return response


def exportar_planilla_mantenimientos_excel(anio=None):
    """
    Exporta un Excel similar a "PLANILLA MANTENIMIENTO VEHÍCULOS" con estructura:
    - Hoja 1: CATASTRO Y PLANIFICACIÓN MP (vehículos y mantenimientos planificados)
    - Hoja 2: SEGUIMIENTO GASTO (gastos reales preventivos y correctivos)
    """
    from .models import Vehiculo, Mantenimiento, Presupuesto, CuentaPresupuestaria
    from datetime import datetime
    
    if not anio:
        anio = datetime.now().year
    
    wb = Workbook()
    estilos = crear_estilos_excel()
    
    # ========== HOJA 1: CATASTRO Y PLANIFICACIÓN MP ==========
    ws1 = wb.active
    ws1.title = "CATASTRO Y PLANIFICACIÓN MP"
    
    # Encabezado
    ws1.merge_cells('A1:AA1')
    celda_titulo = ws1['A1']
    celda_titulo.value = f"CATASTRO Y PLANIFICACIÓN MP - AÑO {anio}"
    celda_titulo.font = estilos['titulo']
    celda_titulo.alignment = estilos['centrado']
    ws1.row_dimensions[1].height = 25
    
    # Encabezados de columnas
    encabezados = [
        'Establecimiento', 'Tipo Carrocería', 'Tipo Ambulancia', 'Clase Ambulancia',
        'Es SAMU', 'Función', 'Marca', 'Modelo', 'Patente', 'Número Motor',
        'Kilometraje', 'Situación Estado', 'Estado Conservación', 'Año Adquisición',
        'Vida Útil', 'Vida Útil Residual', 'Nivel Importancia', 'Es Backup',
        'Tipo Mantenimiento', 'Fecha Programada', 'Fecha Ejecución', 'Kilometraje al Ingreso',
        'Estado', 'Costo Estimado', 'Costo Real', 'Subasignación SIGFE', 'N° Orden Compra'
    ]
    
    fila = 3
    for idx, encabezado in enumerate(encabezados, start=1):
        celda = ws1.cell(row=fila, column=idx)
        celda.value = encabezado
        celda.font = estilos['encabezado_font']
        celda.fill = estilos['encabezado_fill']
        celda.alignment = estilos['centrado']
        celda.border = estilos['borde']
    
    ws1.row_dimensions[fila].height = 20
    
    # Datos: Una fila por vehículo, luego filas por cada mantenimiento
    fila_actual = fila + 1
    vehiculos = Vehiculo.objects.all().order_by('patente')
    
    for vehiculo in vehiculos:
        # Calcular vida útil residual
        años_transcurridos = anio - vehiculo.anio_adquisicion
        vida_util_residual = vehiculo.vida_util - años_transcurridos
        
        # Fila del vehículo (primera fila)
        datos_vehiculo = [
            vehiculo.establecimiento,
            vehiculo.get_tipo_carroceria_display(),
            '',
            vehiculo.clase_ambulancia or '',
            'Sí' if vehiculo.es_samu else 'No',
            '', 
            vehiculo.marca,
            vehiculo.modelo,
            vehiculo.patente,
            vehiculo.nro_motor or '',
            vehiculo.kilometraje_actual,
            vehiculo.get_tipo_propiedad_display(),
            '',  # Estado conservación (no está en modelo)
            vehiculo.anio_adquisicion,
            vehiculo.vida_util,
            vida_util_residual,
            vehiculo.get_criticidad_display(),
            'Sí' if vehiculo.es_backup else 'No',
            '', '', '', '', '', '', '', ''
        ]
        
        for idx, valor in enumerate(datos_vehiculo, start=1):
            celda = ws1.cell(row=fila_actual, column=idx)
            celda.value = valor
            celda.border = estilos['borde']
            if idx == 11:  # Kilometraje
                celda.alignment = estilos['derecha']
            elif idx >= 24:  # Costos
                celda.alignment = estilos['derecha']
            else:
                celda.alignment = Alignment(horizontal='left', vertical='center')
        
        fila_actual += 1
        
        # Filas de mantenimientos para este vehículo
        mantenimientos = Mantenimiento.objects.filter(
            vehiculo=vehiculo,
            fecha_ingreso__year=anio
        ).order_by('fecha_ingreso')
        
        for mant in mantenimientos:
            # Estado visual: ✓ (hecho), X (no hecho), R (reprogramado)
            estado_visual = ''
            if mant.estado == 'Finalizado':
                estado_visual = '✓'
            elif mant.estado == 'Cancelado':
                estado_visual = 'X'
            elif mant.estado == 'Programado':
                estado_visual = 'R'
            
            cuenta_sigfe = mant.cuenta_presupuestaria.codigo if mant.cuenta_presupuestaria else ''
            nro_oc = mant.orden_compra.nro_oc if mant.orden_compra else ''
            if not nro_oc and mant.orden_trabajo and mant.orden_trabajo.orden_compra:
                nro_oc = mant.orden_trabajo.orden_compra.nro_oc
            
            datos_mant = [
                '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '',  # Repetir datos vehículo (vacío)
                mant.get_tipo_mantencion_display(),
                mant.fecha_programada.strftime('%d/%m/%Y') if mant.fecha_programada else '',
                mant.fecha_ingreso.strftime('%d/%m/%Y'),
                mant.km_al_ingreso,
                estado_visual,
                float(mant.costo_estimado) if mant.costo_estimado else 0,
                float(mant.costo_total_real) if mant.costo_total_real else 0,
                cuenta_sigfe,
                nro_oc
            ]
            
            for idx, valor in enumerate(datos_mant, start=1):
                celda = ws1.cell(row=fila_actual, column=idx)
                celda.value = valor
                celda.border = estilos['borde']
                if idx == 21:  # Kilometraje
                    celda.alignment = estilos['derecha']
                elif idx >= 24:  # Costos
                    celda.alignment = estilos['derecha']
                    if idx == 24 or idx == 25:  # Costos
                        celda.number_format = '$#,##0'
                else:
                    celda.alignment = Alignment(horizontal='left', vertical='center')
            
            fila_actual += 1
    
    # Ajustar anchos de columnas
    anchos = [15, 15, 15, 15, 10, 15, 12, 15, 12, 15, 12, 15, 15, 12, 10, 12, 15, 10,
              15, 15, 15, 12, 10, 15, 15, 15, 15]
    for idx, ancho in enumerate(anchos, start=1):
        ws1.column_dimensions[get_column_letter(idx)].width = ancho
    
    # ========== HOJA 2: SEGUIMIENTO GASTO ==========
    ws2 = wb.create_sheet("SEGUIMIENTO GASTO")
    
    # Título
    ws2.merge_cells('A1:H1')
    celda_titulo2 = ws2['A1']
    celda_titulo2.value = f"SEGUIMIENTO GASTO - AÑO {anio}"
    celda_titulo2.font = estilos['titulo']
    celda_titulo2.alignment = estilos['centrado']
    ws2.row_dimensions[1].height = 25
    
    # Subtítulo: Mantenimientos Preventivos
    ws2.merge_cells('A2:H2')
    celda_subtitulo = ws2['A2']
    celda_subtitulo.value = "MANTENIMIENTOS PREVENTIVOS"
    celda_subtitulo.font = Font(bold=True, size=12)
    celda_subtitulo.alignment = estilos['centrado']
    ws2.row_dimensions[2].height = 20
    
    # Encabezados preventivos
    encabezados_preventivos = [
        'Vehículo', 'Fecha', 'Tipo', 'Proveedor', 'Costo Mano Obra',
        'Costo Repuestos', 'Costo Total', 'Cuenta SIGFE', 'N° OC'
    ]
    
    fila = 3
    for idx, encabezado in enumerate(encabezados_preventivos, start=1):
        celda = ws2.cell(row=fila, column=idx)
        celda.value = encabezado
        celda.font = estilos['encabezado_font']
        celda.fill = estilos['encabezado_fill']
        celda.alignment = estilos['centrado']
        celda.border = estilos['borde']
    
    fila_actual = fila + 1
    
    # Mantenimientos preventivos
    mantenimientos_preventivos = Mantenimiento.objects.filter(
        tipo_mantencion='Preventivo',
        fecha_ingreso__year=anio
    ).order_by('vehiculo__patente', 'fecha_ingreso')
    
    for mant in mantenimientos_preventivos:
        datos = [
            mant.vehiculo.patente,
            mant.fecha_ingreso.strftime('%d/%m/%Y'),
            mant.get_tipo_mantencion_display(),
            mant.proveedor.nombre_fantasia,
            float(mant.costo_mano_obra) if mant.costo_mano_obra else 0,
            float(mant.costo_repuestos) if mant.costo_repuestos else 0,
            float(mant.costo_total_real) if mant.costo_total_real else 0,
            mant.cuenta_presupuestaria.codigo if mant.cuenta_presupuestaria else '',
            mant.orden_compra.nro_oc if mant.orden_compra else ''
        ]
        
        for idx, valor in enumerate(datos, start=1):
            celda = ws2.cell(row=fila_actual, column=idx)
            if idx >= 5 and idx <= 7:  # Costos
                celda.value = float(valor) if valor else 0
                celda.number_format = '$#,##0'
                celda.alignment = estilos['derecha']
            else:
                celda.value = valor
                celda.alignment = Alignment(horizontal='left', vertical='center')
            celda.border = estilos['borde']
        
        fila_actual += 1
    
    # Separador y título para correctivos
    fila_actual += 2
    ws2.merge_cells(f'A{fila_actual}:H{fila_actual}')
    celda_subtitulo2 = ws2[f'A{fila_actual}']
    celda_subtitulo2.value = "MANTENIMIENTOS CORRECTIVOS (REPARATIVOS)"
    celda_subtitulo2.font = Font(bold=True, size=12)
    celda_subtitulo2.alignment = estilos['centrado']
    ws2.row_dimensions[fila_actual].height = 20
    
    fila_actual += 1
    
    # Encabezados correctivos (mismos que preventivos)
    for idx, encabezado in enumerate(encabezados_preventivos, start=1):
        celda = ws2.cell(row=fila_actual, column=idx)
        celda.value = encabezado
        celda.font = estilos['encabezado_font']
        celda.fill = estilos['encabezado_fill']
        celda.alignment = estilos['centrado']
        celda.border = estilos['borde']
    
    fila_actual += 1
    
    # Mantenimientos correctivos
    mantenimientos_correctivos = Mantenimiento.objects.filter(
        tipo_mantencion='Correctivo',
        fecha_ingreso__year=anio
    ).order_by('vehiculo__patente', 'fecha_ingreso')
    
    for mant in mantenimientos_correctivos:
        datos = [
            mant.vehiculo.patente,
            mant.fecha_ingreso.strftime('%d/%m/%Y'),
            mant.get_tipo_mantencion_display(),
            mant.proveedor.nombre_fantasia,
            float(mant.costo_mano_obra) if mant.costo_mano_obra else 0,
            float(mant.costo_repuestos) if mant.costo_repuestos else 0,
            float(mant.costo_total_real) if mant.costo_total_real else 0,
            mant.cuenta_presupuestaria.codigo if mant.cuenta_presupuestaria else '',
            mant.orden_compra.nro_oc if mant.orden_compra else ''
        ]
        
        for idx, valor in enumerate(datos, start=1):
            celda = ws2.cell(row=fila_actual, column=idx)
            if idx >= 5 and idx <= 7:  # Costos
                celda.value = float(valor) if valor else 0
                celda.number_format = '$#,##0'
                celda.alignment = estilos['derecha']
            else:
                celda.value = valor
                celda.alignment = Alignment(horizontal='left', vertical='center')
            celda.border = estilos['borde']
        
        fila_actual += 1
    
    # Ajustar anchos de columnas hoja 2
    anchos2 = [12, 12, 15, 25, 15, 15, 15, 15, 15]
    for idx, ancho in enumerate(anchos2, start=1):
        ws2.column_dimensions[get_column_letter(idx)].width = ancho
    
    # Preparar respuesta
    nombre_archivo = f'PLANILLA_MANTENIMIENTO_VEHICULOS_{anio}_{datetime.now().strftime("%Y%m%d")}.xlsx'
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    
    wb.save(response)
    return response

