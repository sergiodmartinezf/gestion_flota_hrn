from django.urls import path
from . import views

urlpatterns = [
    # Autenticación
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Gestión de usuarios (RF_01-RF_05)
    path('usuarios/registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('usuarios/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/<str:rut>/modificar/', views.modificar_usuario, name='modificar_usuario'),
    path('usuarios/<str:rut>/deshabilitar/', views.deshabilitar_usuario, name='deshabilitar_usuario'),
    
    # Gestión de vehículos (RF_06-RF_10)
    path('vehiculos/registrar/', views.registrar_vehiculo, name='registrar_vehiculo'),
    path('vehiculos/', views.listar_flota, name='listar_flota'),
    path('vehiculos/<str:patente>/', views.ficha_vehiculo, name='ficha_vehiculo'),
    path('vehiculos/<str:patente>/modificar/', views.modificar_vehiculo, name='modificar_vehiculo'),
    path('vehiculos/<str:patente>/actualizar-estado/', views.actualizar_estado_vehiculo, name='actualizar_estado_vehiculo'),
    
    # Visualizaciones y alertas (RF_11-RF_15)
    path('disponibilidad/', views.disponibilidad_flota, name='disponibilidad_flota'),
    path('costos-kilometro/', views.costo_por_kilometro, name='costo_por_kilometro'),
    path('gastos-mantenimientos/', views.gastos_mantenimientos, name='gastos_mantenimientos'),
    path('alertas-mantenimiento/', views.alertas_mantenimiento, name='alertas_mantenimiento'),
    
    # Bitácoras (RF_15)
    path('bitacoras/registrar/', views.registrar_bitacora, name='registrar_bitacora'),
    path('api/vehiculos-kilometraje/', views.api_vehiculos_kilometraje, name='api_vehiculos_kilometraje'),
    path('bitacoras/', views.listar_bitacoras, name='listar_bitacoras'),
    
    # Combustible (RF_16)
    path('combustible/registrar/', views.registrar_carga_combustible, name='registrar_carga_combustible'),
    path('combustible/', views.listar_cargas_combustible, name='listar_cargas_combustible'),
    
    # Incidentes (RF_17)
    path('incidentes/registrar/', views.registrar_incidente, name='registrar_incidente'),
    path('incidentes/', views.listar_incidentes, name='listar_incidentes'),
    
    # Mantenimientos (RF_18-RF_20)
    path('mantenimientos/programar/', views.programar_mantenimiento_preventivo, name='programar_mantenimiento_preventivo'),
    path('mantenimientos/registrar/', views.registrar_mantenimiento_ejecutado, name='registrar_mantenimiento_ejecutado'),
    path('mantenimientos/', views.listar_mantenimientos, name='listar_mantenimientos'),
    
    # Presupuestos (RF_21-RF_22)
    path('presupuestos/registrar/', views.registrar_presupuesto, name='registrar_presupuesto'),
    path('presupuestos/', views.listar_presupuestos, name='listar_presupuestos'),
    path('presupuestos/alertas/', views.alertas_presupuesto, name='alertas_presupuesto'),
    
    # Calendario (RF_23)
    path('calendario/', views.calendario_mantenciones, name='calendario_mantenciones'),
    
    # Reportes (RF_24-RF_25, RF_28)
    path('reportes/costos/', views.reporte_costos, name='reporte_costos'),
    path('reportes/disponibilidad/', views.reporte_disponibilidad, name='reporte_disponibilidad'),
    path('reportes/historial/<str:patente>/', views.reporte_historial_unidad, name='reporte_historial_unidad'),
    
    # Arriendos (RF_26)
    path('arriendos/registrar/', views.registrar_arriendo, name='registrar_arriendo'),
    path('arriendos/', views.listar_arriendos, name='listar_arriendos'),

    # Gestión de Proveedores
    path('proveedores/', views.listar_proveedores, name='listar_proveedores'),
    path('proveedores/registrar/', views.registrar_proveedor, name='registrar_proveedor'),
    path('proveedores/<int:id>/modificar/', views.modificar_proveedor, name='modificar_proveedor'),
    path('proveedores/<int:id>/eliminar/', views.eliminar_proveedor, name='eliminar_proveedor'),

    # Órdenes de Compra (RF_29-RF_33)
    path('ordenes-compra/registrar/', views.registrar_orden_compra, name='registrar_orden_compra'),
    path('ordenes-compra/', views.listar_ordenes_compra, name='listar_ordenes_compra'),
    path('ordenes-compra/<int:id>/', views.detalle_orden_compra, name='detalle_orden_compra'),
    path('ordenes-compra/<int:id>/modificar/', views.modificar_orden_compra, name='modificar_orden_compra'),
    path('ordenes-compra/<int:id>/eliminar/', views.eliminar_orden_compra, name='eliminar_orden_compra'),
]

