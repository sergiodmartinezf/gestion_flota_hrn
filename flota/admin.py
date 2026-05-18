# flota/admin.py
from django.contrib import admin
from .models import *

class ViajePacienteInline(admin.TabularInline):
    model = PacienteTraslado
    extra = 1

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre', 'apellido', 'rol', 'activo')
    search_fields = ('rut', 'nombre', 'apellido', 'email')

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'tipo_carroceria', 'estado', 'kilometraje_actual')
    list_filter = ('tipo_carroceria', 'estado', 'criticidad')
    search_fields = ('patente', 'marca', 'modelo')

@admin.register(HojaRuta)
class HojaRutaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'conductor', 'fecha', 'turno', 'km_inicio')
    list_filter = ('fecha', 'turno', 'vehiculo')
    date_hierarchy = 'fecha'

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('id', 'hoja_ruta', 'hora_salida')
    list_filter = ('hoja_ruta__fecha',)
    inlines = [ViajePacienteInline]

@admin.register(PacienteViaje)
class PacienteViajeAdmin(admin.ModelAdmin):
    list_display = ('rut', 'creado_en')
    search_fields = ('rut',)
    ordering = ('rut',)


@admin.register(PacienteTraslado)
class PacienteTrasladoAdmin(admin.ModelAdmin):
    list_display = ('viaje', 'rut', 'categoria_traslado', 'sentido', 'destino_tipo', 'paciente_viaje')
    list_filter = ('destino_tipo', 'categoria_traslado', 'sentido')
    search_fields = ('rut',)

@admin.register(CargaCombustible)
class CargaCombustibleAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'patente_vehiculo', 'litros', 'costo_total')
    list_filter = ('fecha', 'patente_vehiculo')
    date_hierarchy = 'fecha'

@admin.register(FallaReportada)
class FallaReportadaAdmin(admin.ModelAdmin):
    list_display = ('fecha_reporte', 'vehiculo', 'nivel_urgencia')
    list_filter = ('nivel_urgencia', 'vehiculo')
    date_hierarchy = 'fecha_reporte'

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'descripcion', 'valor_umbral', 'vigente', 'generado_en')
    list_filter = ('vigente', 'vehiculo')
    date_hierarchy = 'generado_en'

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'tipo_mantencion', 'fecha_ingreso', 'estado', 'costo_total_real')
    list_filter = ('tipo_mantencion', 'estado', 'vehiculo')
    date_hierarchy = 'fecha_ingreso'

@admin.register(Arriendo)
class ArriendoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo_arrendado', 'vehiculo_reemplazado', 'fecha_inicio', 'fecha_fin', 'estado')
    list_filter = ('estado', 'proveedor')
    date_hierarchy = 'fecha_inicio'

@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('nro_oc', 'fecha_emision', 'proveedor', 'monto_total', 'estado')
    list_filter = ('estado', 'proveedor', 'fecha_emision')
    search_fields = ('nro_oc', 'id_licitacion', 'folio_sigfe')
    date_hierarchy = 'fecha_emision'

@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nro_ot', 'fecha_solicitud', 'vehiculo', 'proveedor')
    list_filter = ('fecha_solicitud', 'vehiculo', 'proveedor')
    search_fields = ('nro_ot', 'descripcion')
    date_hierarchy = 'fecha_solicitud'

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_fantasia', 'rut_empresa', 'es_taller', 'es_arrendador', 'activo')
    list_filter = ('es_taller', 'es_arrendador', 'es_proveedor_base', 'activo')
    search_fields = ('nombre_fantasia', 'rut_empresa')

@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'cuenta', 'monto_asignado', 'monto_ejecutado', 'disponible', 'activo')
    list_filter = ('anio', 'activo', 'cuenta')
    search_fields = ('cuenta__codigo', 'cuenta__nombre')

@admin.register(CuentaPresupuestaria)
class CuentaPresupuestariaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('codigo', 'nombre')
    