from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Usuario, Proveedor, OrdenCompra, Vehiculo, OrdenTrabajo,
    Presupuesto, Arriendo, DisponibilidadVehiculo, HojaRuta,
    Viaje, CargaCombustible, Mantenimiento, AlertaMantencion,
    FallaReportada
)


@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    list_display = ('rut', 'nombre', 'apellido', 'email', 'rol', 'activo', 'creado_en')
    list_filter = ('rol', 'activo')
    search_fields = ('rut', 'nombre', 'apellido', 'email')
    ordering = ('apellido', 'nombre')
    filter_horizontal = ()  # Eliminar filter_horizontal de grupos y permisos que no existen
    fieldsets = (
        (None, {'fields': ('rut', 'password')}),
        ('Información Personal', {'fields': ('nombre', 'apellido', 'email')}),
        ('Permisos', {'fields': ('rol', 'activo')}),
        ('Fechas', {'fields': ('creado_en',)}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('rut', 'nombre', 'apellido', 'email', 'rol', 'password1', 'password2'),
        }),
    )


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_fantasia', 'rut_empresa', 'giro', 'telefono', 'email_contacto')
    search_fields = ('nombre_fantasia', 'rut_empresa')


@admin.register(OrdenCompra)
class OrdenCompraAdmin(admin.ModelAdmin):
    list_display = ('nro_oc', 'proveedor', 'fecha_emision', 'monto_total')
    list_filter = ('fecha_emision', 'proveedor')
    search_fields = ('nro_oc', 'proveedor__nombre_fantasia')


@admin.register(Vehiculo)
class VehiculoAdmin(admin.ModelAdmin):
    list_display = ('patente', 'marca', 'modelo', 'tipo_carroceria', 'estado', 'kilometraje_actual', 'criticidad')
    list_filter = ('estado', 'tipo_carroceria', 'criticidad', 'tipo_propiedad')
    search_fields = ('patente', 'marca', 'modelo')


@admin.register(OrdenTrabajo)
class OrdenTrabajoAdmin(admin.ModelAdmin):
    list_display = ('nro_ot', 'vehiculo', 'fecha_solicitud', 'fecha_programada', 'proveedor')
    list_filter = ('fecha_solicitud', 'proveedor')
    search_fields = ('nro_ot', 'vehiculo__patente')


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'anio', 'categoria', 'monto_asignado', 'monto_ejecutado')
    list_filter = ('anio', 'categoria')
    search_fields = ('vehiculo__patente',)


@admin.register(Arriendo)
class ArriendoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'proveedor', 'fecha_inicio', 'fecha_fin', 'costo_total', 'estado')
    list_filter = ('estado', 'fecha_inicio')
    search_fields = ('vehiculo__patente', 'proveedor__nombre_fantasia')


@admin.register(DisponibilidadVehiculo)
class DisponibilidadVehiculoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'fecha_inicio', 'fecha_fin', 'dias_no_operativo')
    list_filter = ('fecha_inicio',)
    search_fields = ('vehiculo__patente',)


@admin.register(HojaRuta)
class HojaRutaAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'conductor', 'fecha', 'turno', 'km_inicio', 'km_fin')
    list_filter = ('fecha', 'turno')
    search_fields = ('vehiculo__patente', 'conductor__nombre', 'conductor__apellido')


@admin.register(Viaje)
class ViajeAdmin(admin.ModelAdmin):
    list_display = ('hoja_ruta', 'destino', 'hora_salida', 'tipo_servicio')
    list_filter = ('tipo_servicio', 'hora_salida')
    search_fields = ('destino', 'rut_paciente')


@admin.register(CargaCombustible)
class CargaCombustibleAdmin(admin.ModelAdmin):
    list_display = ('patente_vehiculo', 'fecha', 'litros', 'kilometraje_al_cargar', 'costo_total')
    list_filter = ('fecha',)
    search_fields = ('patente_vehiculo__patente', 'nro_boleta')


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'tipo_mantencion', 'fecha_ingreso', 'fecha_salida', 'estado', 'costo_total')
    list_filter = ('tipo_mantencion', 'estado', 'fecha_ingreso')
    search_fields = ('vehiculo__patente',)


@admin.register(AlertaMantencion)
class AlertaMantencionAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'descripcion', 'generado_en', 'vigente')
    list_filter = ('vigente', 'generado_en')
    search_fields = ('vehiculo__patente',)


@admin.register(FallaReportada)
class FallaReportadaAdmin(admin.ModelAdmin):
    list_display = ('vehiculo', 'conductor', 'fecha_reporte', 'descripcion')
    list_filter = ('fecha_reporte',)
    search_fields = ('vehiculo__patente', 'conductor__nombre', 'conductor__apellido')

