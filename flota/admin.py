from django.contrib import admin
from .models import (
    Usuario, 
    Proveedor, 
    CuentaPresupuestaria, 
    OrdenCompra,
    Vehiculo, 
    Presupuesto, 
    OrdenTrabajo, 
    Mantenimiento,
    Arriendo, 
    HojaRuta, 
    Viaje, 
    CargaCombustible,
    FallaReportada, 
    AlertaMantencion
)

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('rut', 'nombre_completo', 'rol', 'activo', 'email')
    search_fields = ('rut', 'nombre', 'apellido')
    list_filter = ('rol', 'activo')

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('rut_empresa', 'nombre_fantasia', 'es_taller', 'es_arrendador', 'telefono')
    search_fields = ('nombre_fantasia', 'rut_empresa')
    list_filter = ('es_taller', 'es_arrendador')

@admin.register(CuentaPresupuestaria)
class CuentaPresupuestariaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre')
    search_fields = ('codigo', 'nombre')
    ordering = ('codigo',)

@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('nro_oc', 'proveedor', 'vehiculo', 'fecha_emision', 'monto_total', 'estado', 'folio_sigfe')
    list_filter = ('estado', 'fecha_emision')
    search_fields = ('nro_oc', 'proveedor__nombre_fantasia', 'vehiculo__patente', 'id_licitacion')
    date_hierarchy = 'fecha_emision'

@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'tipo_carroceria', 'estado', 'criticidad', 'kilometraje_actual')
    list_filter = ('estado', 'tipo_carroceria', 'criticidad', 'es_samu', 'tipo_propiedad')
    search_fields = ('patente', 'marca', 'modelo')

@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'cuenta', 'vehiculo_o_general', 'monto_asignado', 'porcentaje_ejecutado')
    list_filter = ('anio', 'cuenta')
    
    def vehiculo_o_general(self, obj):
        return obj.vehiculo if obj.vehiculo else "Flota General"
    vehiculo_o_general.short_description = "Asignación"

@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nro_ot', 'vehiculo', 'proveedor', 'fecha_solicitud')
    search_fields = ('nro_ot', 'vehiculo__patente')

@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'tipo_mantencion', 'fecha_ingreso', 'estado', 'costo_total_real')
    list_filter = ('estado', 'tipo_mantencion')
    search_fields = ('vehiculo__patente', 'descripcion_trabajo')
    date_hierarchy = 'fecha_ingreso'

@admin.register(Arriendo)
class ArriendoAdmin(admin.ModelAdmin):
    list_display = ('proveedor', 'vehiculo_reemplazado', 'fecha_inicio', 'fecha_fin', 'estado', 'costo_diario')
    list_filter = ('estado',)
    search_fields = ('proveedor__nombre_fantasia', 'vehiculo_reemplazado__patente')

@admin.register(HojaRuta)
class HojaRutaAdmin(admin.ModelAdmin):
    list_display = ('id', 'vehiculo', 'fecha', 'conductor', 'turno', 'medico', 'km_recorridos')
    list_filter = ('fecha', 'turno')
    search_fields = ('vehiculo__patente', 'conductor__nombre', 'conductor__apellido', 'medico')

@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('hoja_ruta', 'hora_salida', 'destino', 'tipo_servicio', 'rut_paciente')
    list_filter = ('tipo_servicio',)
    search_fields = ('destino', 'rut_paciente')

@admin.register(CargaCombustible)
class CargaCombustibleAdmin(admin.ModelAdmin):
    list_display = ('patente_vehiculo', 'fecha', 'litros', 'costo_total', 'nro_boleta')
    list_filter = ('fecha',)
    search_fields = ('patente_vehiculo__patente', 'nro_boleta')

@admin.register(FallaReportada)
class FallaReportadaAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'fecha_reporte', 'nivel_urgencia', 'conductor')
    list_filter = ('nivel_urgencia', 'fecha_reporte')

@admin.register(AlertaMantencion)
class AlertaMantencionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'descripcion', 'generado_en', 'vigente')
    list_filter = ('vigente',)
    