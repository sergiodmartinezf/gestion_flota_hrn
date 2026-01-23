"""
Módulo principal de vistas
"""

# Importar utilidades primero
from .utilidades import es_administrador, es_conductor_o_admin, verificar_presupuesto_vehiculo

# Importar vistas de autenticación
from .autenticacion import login_view, logout_view

# Importar vistas de usuarios
from .usuarios import (
    registrar_usuario,
    listar_usuarios,
    modificar_usuario,
    deshabilitar_usuario
)

# Importar vistas de vehículos
from .vehiculos import (
    registrar_vehiculo,
    listar_flota,
    ficha_vehiculo,
    modificar_vehiculo,
    actualizar_estado_vehiculo,
    disponibilidad_flota,
    costo_por_kilometro,
    gastos_mantenimientos,
    alertas_mantenimiento
)

# Importar vistas de bitácoras y viajes
from .viajes import (
    registrar_bitacora,
    listar_bitacoras,
    modificar_bitacora,
    detalle_bitacora,
    registrar_carga_combustible,
    listar_cargas_combustible,
    registrar_incidente,
    listar_incidentes,
    exportar_consolidado_viajes,
    agregar_viaje
)

# Importar vistas de mantenimiento
from .mantenimiento import (
    programar_mantenimiento_preventivo,
    registrar_mantenimiento_correctivo,
    listar_mantenimientos,
    cambiar_estado_mantenimiento,
    editar_mantenimiento,
    finalizar_mantenimiento,
    eliminar_mantenimiento,
    calendario_mantenciones,
    api_mantenimientos
)

# Importar vistas de presupuesto
from .presupuesto import (
    registrar_presupuesto,
    modificar_presupuesto,
    deshabilitar_presupuesto,
    listar_presupuestos,
    alertas_presupuesto,
    reporte_variacion_presupuestaria
)

# Importar vistas de reportes
from .reportes import (
    reporte_costos,
    reporte_disponibilidad,
    reporte_historial_unidad
)

# Importar vistas de arriendo
from .arriendos import (
    registrar_arriendo,
    listar_arriendos,
    finalizar_arriendo
)

# Importar vistas de dashboard
from .dashboard import dashboard

# Importar vistas de proveedores
from .proveedores import (
    listar_proveedores,
    registrar_proveedor,
    modificar_proveedor,
    habilitar_proveedor,
    deshabilitar_proveedor
)

# Importar vistas de órdenes
from .ordenes import (
    importar_orden_compra,
    registrar_orden_compra,
    listar_ordenes_compra,
    modificar_orden_compra,
    eliminar_orden_compra,
    detalle_orden_compra,
    registrar_orden_trabajo,
    listar_ordenes_trabajo,
    detalle_orden_trabajo,
    modificar_orden_trabajo,
    eliminar_orden_trabajo
)

# Importar APIs
from .api import (
    api_vehiculos_kilometraje,
    api_alertas_count,
    api_verificar_presupuesto
)

# Exportación de vistas
__all__ = [
    # Utilidades
    'es_administrador',
    'es_conductor_o_admin',
    'verificar_presupuesto_vehiculo',
    
    # Autenticación
    'login_view',
    'logout_view',
    
    # Usuarios
    'registrar_usuario',
    'listar_usuarios',
    'modificar_usuario',
    'deshabilitar_usuario',
    
    # Vehículos
    'registrar_vehiculo',
    'listar_flota',
    'ficha_vehiculo',
    'modificar_vehiculo',
    'actualizar_estado_vehiculo',
    'disponibilidad_flota',
    'costo_por_kilometro',
    'gastos_mantenimientos',
    'alertas_mantenimiento',
    
    # Bitácoras y viajes
    'registrar_bitacora',
    'listar_bitacoras',
    'modificar_bitacora',
    'detalle_bitacora',
    'registrar_carga_combustible',
    'listar_cargas_combustible',
    'registrar_incidente',
    'listar_incidentes',
    'exportar_consolidado_viajes',
    
    # Mantenimiento
    'programar_mantenimiento_preventivo',
    'registrar_mantenimiento_correctivo',
    'listar_mantenimientos',
    'cambiar_estado_mantenimiento',
    'editar_mantenimiento',
    'finalizar_mantenimiento',
    'eliminar_mantenimiento',
    'calendario_mantenciones',
    'api_mantenimientos',
    
    # Presupuesto
    'registrar_presupuesto',
    'modificar_presupuesto',
    'deshabilitar_presupuesto',
    'listar_presupuestos',
    'alertas_presupuesto',
    'reporte_variacion_presupuestaria',
    
    # Reportes
    'reporte_costos',
    'reporte_disponibilidad',
    'reporte_historial_unidad',
    
    # Arriendo
    'registrar_arriendo',
    'listar_arriendos',
    'finalizar_arriendo',
    
    # Dashboard
    'dashboard',
    
    # Proveedores
    'listar_proveedores',
    'registrar_proveedor',
    'modificar_proveedor',
    'habilitar_proveedor',
    'deshabilitar_proveedor',
    
    # Órdenes
    'importar_orden_compra',
    'registrar_orden_compra',
    'listar_ordenes_compra',
    'modificar_orden_compra',
    'eliminar_orden_compra',
    'detalle_orden_compra',
    'registrar_orden_trabajo',
    'listar_ordenes_trabajo',
    'detalle_orden_trabajo',
    'modificar_orden_trabajo',
    'eliminar_orden_trabajo',
    
    # APIs
    'api_vehiculos_kilometraje',
    'api_alertas_count',
    'api_verificar_presupuesto',
]
