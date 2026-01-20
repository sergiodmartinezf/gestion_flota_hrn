from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
import re
from ..models import OrdenCompra, OrdenTrabajo, Proveedor, Vehiculo, Mantenimiento, CuentaPresupuestaria
from ..forms import OrdenCompraForm, OrdenTrabajoForm
from .utilidades import es_administrador
from flota.utils import consultar_oc_mercado_publico

def importar_orden_compra(request):
    if request.method == 'POST':
        codigo_oc = request.POST.get('codigo_oc', '').strip().upper()
        
        if not codigo_oc:
            messages.error(request, "Debe ingresar un código de Orden de Compra.")
            return redirect('importar_oc')

        # 1. Consultar API
        datos = consultar_oc_mercado_publico(codigo_oc)

        if 'error' in datos:
            messages.error(request, datos['error'])
        else:
            try:
                # 2. Gestionar Proveedor
                proveedor, created_prov = Proveedor.objects.get_or_create(
                    rut_empresa=datos['proveedor_rut'],
                    defaults={
                        'nombre_fantasia': datos['proveedor_nombre'],
                        'giro': '',
                        'telefono': '',
                        'email_contacto': '',
                        'es_taller': True,
                        'es_arrendador': False,
                        'activo': True
                    }
                )
                
                if created_prov:
                    messages.info(request, f"Proveedor {proveedor.nombre_fantasia} creado.")

                # ========== BUSCAR VEHÍCULO EN BASE DE DATOS ==========
                vehiculo_asociado = None

                # Función para normalizar patente para búsqueda
                def normalizar_patente_busqueda(patente):
                    """Normaliza una patente para búsqueda (elimina todo excepto letras y números)"""
                    if not patente:
                        return ""
                    return re.sub(r'[^A-Z0-9]', '', patente.upper())

                # Función para formatear patente como en la BD
                def formatear_patente_como_bd(patente):
                    """Intenta formatear una patente como en la base de datos"""
                    patente_limpia = normalizar_patente_busqueda(patente)
                    
                    # Si es formato de 6 caracteres (4 letras + 2 números)
                    if len(patente_limpia) == 6 and patente_limpia[:4].isalpha() and patente_limpia[4:].isdigit():
                        return f"{patente_limpia[:2]}.{patente_limpia[2:4]}-{patente_limpia[4:]}"
                    # Si es formato de 7 caracteres (4 letras + 3 números)
                    elif len(patente_limpia) == 7 and patente_limpia[:4].isalpha() and patente_limpia[4:].isdigit():
                        return f"{patente_limpia[:2]}.{patente_limpia[2:4]}-{patente_limpia[4:]}"
                    return patente

                # Usar patentes_posibles que vienen de utils.py
                if datos.get('patentes_posibles'):
                    print(f"Buscando vehículos para patentes: {datos['patentes_posibles']}")
                    
                    # Primero, intentar búsqueda exacta
                    for patente_buscada in datos['patentes_posibles']:
                        vehiculo = Vehiculo.objects.filter(patente__iexact=patente_buscada).first()
                        if vehiculo:
                            vehiculo_asociado = vehiculo
                            print(f"Encontrado por búsqueda exacta: {vehiculo.patente}")
                            break
                    
                    # Si no se encontró, intentar con normalización
                    if not vehiculo_asociado:
                        for patente_buscada in datos['patentes_posibles']:
                            # Normalizar la patente buscada
                            patente_buscada_norm = normalizar_patente_busqueda(patente_buscada)
                            
                            # Buscar en todos los vehículos comparando patentes normalizadas
                            for vehiculo in Vehiculo.objects.all():
                                patente_vehiculo_norm = normalizar_patente_busqueda(vehiculo.patente)
                                if patente_vehiculo_norm == patente_buscada_norm:
                                    vehiculo_asociado = vehiculo
                                    print(f"Encontrado por normalización: {vehiculo.patente} (buscado: {patente_buscada})")
                                    break
                            
                            if vehiculo_asociado:
                                break
                    
                    # Si aún no se encontró, intentar formatear y buscar
                    if not vehiculo_asociado:
                        for patente_buscada in datos['patentes_posibles']:
                            patente_formateada = formatear_patente_como_bd(patente_buscada)
                            if patente_formateada != patente_buscada:  # Solo si se pudo formatear
                                vehiculo = Vehiculo.objects.filter(patente__iexact=patente_formateada).first()
                                if vehiculo:
                                    vehiculo_asociado = vehiculo
                                    print(f"Encontrado después de formatear: {vehiculo.patente}")
                                    break

                # Debug: mostrar qué patentes están en la BD
                print("Patentes en base de datos:", list(Vehiculo.objects.values_list('patente', flat=True)))

                # ========== BUSCAR CUENTA PRESUPUESTARIA EN BASE DE DATOS ==========
                cuenta_presupuestaria = None
                
                # Usar codigo_presupuestario que viene de utils.py
                if datos.get('codigo_presupuestario'):
                    try:
                        cuenta_presupuestaria = CuentaPresupuestaria.objects.get(
                            codigo=datos['codigo_presupuestario']
                        )
                    except CuentaPresupuestaria.DoesNotExist:
                        # Si no existe, NO la creamos automáticamente
                        pass  # Simplemente no asignamos cuenta

                # ========== CREAR/ACTUALIZAR ORDEN DE COMPRA ==========
                oc, created_oc = OrdenCompra.objects.update_or_create(
                    nro_oc=datos['codigo'],
                    defaults={
                        'descripcion': datos['descripcion'][:500],
                        'vehiculo': vehiculo_asociado,  # Se asigna si se encontró
                        'fecha_emision': datos['fecha_emision'],
                        'monto_neto': datos.get('monto_neto', 0),
                        'monto_total': datos.get('monto_total', 0),
                        'impuesto': datos.get('impuestos', 0),
                        'id_licitacion': datos.get('id_licitacion', ''),
                        'folio_sigfe': '',  # Dejamos vacío o elimina el campo
                        'estado': datos['estado'],
                        'proveedor': proveedor,
                        'tipo_adquisicion': 'Licitación Pública',
                        'cuenta_presupuestaria': cuenta_presupuestaria,  # Se asigna si se encontró
                        'presupuesto': None,
                        'archivo_adjunto': None,
                    }
                )

                # ========== MENSAJES INFORMATIVOS CLAROS ==========
                if created_oc:
                    messages.success(request, f"OC {oc.nro_oc} importada exitosamente.")
                else:
                    messages.success(request, f"OC {oc.nro_oc} actualizada.")
                
                if vehiculo_asociado:
                    messages.info(request, f"Se asoció al vehículo: {vehiculo_asociado.patente}")
                else:
                    messages.warning(request, "No se pudo asociar a ningún vehículo. Verifica que la patente exista en el sistema.")
                
                if cuenta_presupuestaria:
                    messages.info(request, f"Se asignó la cuenta: {cuenta_presupuestaria.codigo}")
                else:
                    messages.warning(request, "No se pudo asignar cuenta presupuestaria. Verifica que el código exista en el sistema.")

                return redirect('detalle_orden_compra', id=oc.id)

            except Exception as e:
                messages.error(request, f"Error: {str(e)}")

        return redirect('importar_oc')

    return render(request, 'flota/importar_oc.html')

    
# RF_29: Registrar orden de compra
@login_required
@user_passes_test(es_administrador)
def registrar_orden_compra(request):
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST, request.FILES)
        if form.is_valid():
            orden_compra = form.save()
            messages.success(request, f'Orden de Compra {orden_compra.nro_oc} registrada exitosamente.')
            return redirect('listar_ordenes_compra')
    else:
        form = OrdenCompraForm()
    
    return render(request, 'flota/registrar_orden_compra.html', {'form': form})


# RF_30: Listar órdenes de compra
@login_required
def listar_ordenes_compra(request):
    ordenes = OrdenCompra.objects.all().order_by('-fecha_emision', 'nro_oc')
    
    # Filtros
    estado_filter = request.GET.get('estado')
    proveedor_filter = request.GET.get('proveedor')
    
    if estado_filter:
        ordenes = ordenes.filter(estado=estado_filter)
    if proveedor_filter:
        ordenes = ordenes.filter(proveedor__id=proveedor_filter)
    
    proveedores = Proveedor.objects.all()
    
    return render(request, 'flota/listar_ordenes_compra.html', {
        'ordenes': ordenes,
        'proveedores': proveedores,
        'estado_filter': estado_filter,
        'proveedor_filter': proveedor_filter,
    })


# RF_31: Modificar orden de compra
@login_required
@user_passes_test(es_administrador)
def modificar_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    if request.method == 'POST':
        form = OrdenCompraForm(request.POST, request.FILES, instance=orden)
        if form.is_valid():
            orden = form.save()
            messages.success(request, f'Orden de Compra {orden.nro_oc} modificada exitosamente.')
            return redirect('listar_ordenes_compra')
    else:
        form = OrdenCompraForm(instance=orden)
    
    return render(request, 'flota/modificar_orden_compra.html', {'form': form, 'orden': orden})


# RF_32: Eliminar orden de compra
@login_required
@user_passes_test(es_administrador)
def eliminar_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    if request.method == 'POST':
        nro_oc = orden.nro_oc
        orden.delete()
        messages.success(request, f'Orden de Compra {nro_oc} eliminada exitosamente.')
        return redirect('listar_ordenes_compra')
    
    return render(request, 'flota/eliminar_orden_compra.html', {'orden': orden})


# RF_33: Detalle de orden de compra
@login_required
def detalle_orden_compra(request, id):
    orden = get_object_or_404(OrdenCompra, id=id)
    return render(request, 'flota/detalle_orden_compra.html', {'orden': orden})


# Registrar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def registrar_orden_trabajo(request):
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST)
        if form.is_valid():
            orden_trabajo = form.save()
            messages.success(request, f'Orden de Trabajo {orden_trabajo.nro_ot} registrada exitosamente.')
            return redirect('listar_ordenes_trabajo')
    else:
        form = OrdenTrabajoForm()
    
    return render(request, 'flota/registrar_orden_trabajo.html', {'form': form})


# Listar Órdenes de Trabajo
@login_required
def listar_ordenes_trabajo(request):
    ordenes = OrdenTrabajo.objects.all().order_by('-fecha_solicitud', 'nro_ot')
    
    # Filtros
    vehiculo_filter = request.GET.get('vehiculo')
    proveedor_filter = request.GET.get('proveedor')
    
    if vehiculo_filter:
        ordenes = ordenes.filter(vehiculo__patente=vehiculo_filter)
    if proveedor_filter:
        ordenes = ordenes.filter(proveedor__id=proveedor_filter)
    
    # Datos para filtros
    vehiculos = Vehiculo.objects.all().order_by('patente')
    proveedores = Proveedor.objects.filter(es_taller=True, activo=True).order_by('nombre_fantasia')
    
    return render(request, 'flota/listar_ordenes_trabajo.html', {
        'ordenes': ordenes,
        'vehiculos': vehiculos,
        'proveedores': proveedores,
        'vehiculo_filter': vehiculo_filter,
        'proveedor_filter': proveedor_filter,
    })


# Detalle de Orden de Trabajo
@login_required
def detalle_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    mantenimientos = Mantenimiento.objects.filter(orden_trabajo=orden)
    
    return render(request, 'flota/detalle_orden_trabajo.html', {
        'orden': orden,
        'mantenimientos': mantenimientos,
    })


# Modificar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def modificar_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    if request.method == 'POST':
        form = OrdenTrabajoForm(request.POST, instance=orden)
        if form.is_valid():
            orden = form.save()
            messages.success(request, f'Orden de Trabajo {orden.nro_ot} modificada exitosamente.')
            return redirect('listar_ordenes_trabajo')
    else:
        form = OrdenTrabajoForm(instance=orden)
    
    return render(request, 'flota/modificar_orden_trabajo.html', {'form': form, 'orden': orden})


# Eliminar Orden de Trabajo
@login_required
@user_passes_test(es_administrador)
def eliminar_orden_trabajo(request, id):
    orden = get_object_or_404(OrdenTrabajo, id=id)
    if request.method == 'POST':
        nro_ot = orden.nro_ot
        orden.delete()
        messages.success(request, f'Orden de Trabajo {nro_ot} eliminada exitosamente.')
        return redirect('listar_ordenes_trabajo')
    
    return render(request, 'flota/eliminar_orden_trabajo.html', {'orden': orden})


