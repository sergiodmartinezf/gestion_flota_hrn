from django.urls import path
from . import views  # Importa a partir de flota/views/__init__.py

urlpatterns = [
    # Autenticación
    path('', views.login_view, name='login'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Usuarios (RF_01-05)
    path('usuarios/registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('usuarios/listar/', views.listar_usuarios, name='listar_usuarios'),
    path('usuarios/modificar/<str:rut>/', views.modificar_usuario, name='modificar_usuario'),
    path('usuarios/deshabilitar/<str:rut>/', views.deshabilitar_usuario, name='deshabilitar_usuario'),
    
    # Vehículos (RF_06-14)
    path('vehiculos/registrar/', views.registrar_vehiculo, name='registrar_vehiculo'),
    path('vehiculos/listar/', views.listar_flota, name='listar_flota'),
    path('vehiculos/disponibilidad/', views.disponibilidad_flota, name='disponibilidad_flota'),
    path('vehiculos/costo-km/', views.costo_por_kilometro, name='costo_por_kilometro'),
    path('vehiculos/gastos-mantenimientos/', views.gastos_mantenimientos, name='gastos_mantenimientos'),
    path('vehiculos/alertas-mantenimiento/', views.alertas_mantenimiento, name='alertas_mantenimiento'),
    # Con parámetros
    path('vehiculos/<str:patente>/', views.ficha_vehiculo, name='ficha_vehiculo'),
    path('vehiculos/modificar/<str:patente>/', views.modificar_vehiculo, name='modificar_vehiculo'),
    path('vehiculos/estado/<str:patente>/', views.actualizar_estado_vehiculo, name='actualizar_estado_vehiculo'),
    
    # Bitácoras y viajes (RF_15-17)
    path('bitacoras/registrar/', views.registrar_bitacora, name='registrar_bitacora'),
    path('bitacoras/listar/', views.listar_bitacoras, name='listar_bitacoras'),
    path('bitacoras/modificar/<int:id>/', views.modificar_bitacora, name='modificar_bitacora'),
    path('bitacoras/detalle/<int:id>/', views.detalle_bitacora, name='detalle_bitacora'),
    path('combustible/registrar/', views.registrar_carga_combustible, name='registrar_carga_combustible'),
    path('combustible/listar/', views.listar_cargas_combustible, name='listar_cargas_combustible'),
    path('incidentes/registrar/', views.registrar_incidente, name='registrar_incidente'),
    path('incidentes/listar/', views.listar_incidentes, name='listar_incidentes'),
    
    # Mantenimiento (RF_18-23)
    path('mantenimientos/preventivo/', views.programar_mantenimiento_preventivo, name='programar_mantenimiento_preventivo'),
    path('mantenimientos/correctivo/', views.registrar_mantenimiento_correctivo, name='registrar_mantenimiento_correctivo'),
    path('mantenimientos/listar/', views.listar_mantenimientos, name='listar_mantenimientos'),
    path('mantenimientos/calendario/', views.calendario_mantenciones, name='calendario_mantenciones'),
    # Con parámetros
    path('mantenimientos/editar/<int:id>/', views.editar_mantenimiento, name='editar_mantenimiento'),
    path('mantenimientos/finalizar/<int:id>/', views.finalizar_mantenimiento, name='finalizar_mantenimiento'),
    path('mantenimientos/eliminar/<int:id>/', views.eliminar_mantenimiento, name='eliminar_mantenimiento'),
    path('mantenimientos/estado/<int:id>/', views.cambiar_estado_mantenimiento, name='cambiar_estado_mantenimiento'),
    
    # Presupuesto (RF_21-22)
    path('presupuestos/registrar/', views.registrar_presupuesto, name='registrar_presupuesto'),
    path('presupuestos/listar/', views.listar_presupuestos, name='listar_presupuestos'),
    path('presupuestos/alertas/', views.alertas_presupuesto, name='alertas_presupuesto'),
    #path('presupuestos/variacion/', views.reporte_variacion_presupuestaria, name='reporte_variacion_presupuestaria'),
    # Con parámetro
    path('presupuestos/modificar/<int:id>/', views.modificar_presupuesto, name='modificar_presupuesto'),
    path('presupuestos/deshabilitar/<int:id>/', views.deshabilitar_presupuesto, name='deshabilitar_presupuesto'),
    
    # Reportes (RF_24-25, 28)
    path('reportes/costos/', views.reporte_costos, name='reporte_costos'),
    path('reportes/disponibilidad/', views.reporte_disponibilidad, name='reporte_disponibilidad'),
    path('reportes/historial/<str:patente>/', views.reporte_historial_unidad, name='reporte_historial_unidad'),
    
    # Arriendo (RF_26)
    path('arriendos/registrar/', views.registrar_arriendo, name='registrar_arriendo'),
    path('arriendos/listar/', views.listar_arriendos, name='listar_arriendos'),
    path('arriendos/finalizar/<int:id>/', views.finalizar_arriendo, name='finalizar_arriendo'),
    
    # Proveedores
    path('proveedores/listar/', views.listar_proveedores, name='listar_proveedores'),
    path('proveedores/registrar/', views.registrar_proveedor, name='registrar_proveedor'),
    # Con parámetros
    path('proveedores/modificar/<int:id>/', views.modificar_proveedor, name='modificar_proveedor'),
    path('proveedores/habilitar/<int:id>/', views.habilitar_proveedor, name='habilitar_proveedor'),
    path('proveedores/deshabilitar/<int:id>/', views.deshabilitar_proveedor, name='deshabilitar_proveedor'),
    
    # Órdenes de compra (RF_29-33)
    path('ordenes-compra/importar/', views.importar_orden_compra, name='importar_oc'),
    path('ordenes-compra/registrar/', views.registrar_orden_compra, name='registrar_orden_compra'),
    path('ordenes-compra/listar/', views.listar_ordenes_compra, name='listar_ordenes_compra'),
    # Con parámetros
    path('ordenes-compra/modificar/<int:id>/', views.modificar_orden_compra, name='modificar_orden_compra'),
    path('ordenes-compra/eliminar/<int:id>/', views.eliminar_orden_compra, name='eliminar_orden_compra'),
    path('ordenes-compra/detalle/<int:id>/', views.detalle_orden_compra, name='detalle_orden_compra'),
    
    # Órdenes de trabajo
    path('ordenes-trabajo/registrar/', views.registrar_orden_trabajo, name='registrar_orden_trabajo'),
    path('ordenes-trabajo/listar/', views.listar_ordenes_trabajo, name='listar_ordenes_trabajo'),
    # Con parámetros
    path('ordenes-trabajo/modificar/<int:id>/', views.modificar_orden_trabajo, name='modificar_orden_trabajo'),
    path('ordenes-trabajo/eliminar/<int:id>/', views.eliminar_orden_trabajo, name='eliminar_orden_trabajo'),
    path('ordenes-trabajo/detalle/<int:id>/', views.detalle_orden_trabajo, name='detalle_orden_trabajo'),
    
    # Exportaciones
    path('exportar/viajes/', views.exportar_consolidado_viajes, name='exportar_viajes'),
    
    # APIs
    path('api/vehiculos-kilometraje/', views.api_vehiculos_kilometraje, name='api_vehiculos_kilometraje'),
    path('api/alertas-count/', views.api_alertas_count, name='api_alertas_count'),
    path('api/verificar-presupuesto/', views.api_verificar_presupuesto, name='api_verificar_presupuesto'),
    path('api/mantenimientos/', views.api_mantenimientos, name='api_mantenimientos'),
]
