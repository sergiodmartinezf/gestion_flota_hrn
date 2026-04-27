# Sistema de Gestión de Flota - Hospital Río Negro

Sistema web integral desarrollado en Django para la gestión completa de la flota vehicular del Hospital Río Negro. El sistema permite administrar desde la adquisición hasta el mantenimiento de vehículos, incluyendo control presupuestario, hojas de ruta con registro de personal médico, bitácoras de viaje, gestión de combustible, reportes de incidentes y seguimiento de mantenimientos preventivos y correctivos.

## Características Principales

### Gestión de Flota
- **Registro de Vehículos**: Control completo de inventario con diferentes tipos de carrocería (ambulancias, sedanes, camionetas, etc.)
- **Estados de Vehículos**: Seguimiento de disponibilidad, mantenimiento, arriendos y baja de unidades
- **Clasificación por Criticidad**: Identificación de vehículos críticos vs no críticos para el servicio
- **Control de Kilometraje**: Seguimiento automático del kilometraje y alertas de mantenimiento

### Gestión de Usuarios
- **Sistema de Roles**: Administrador, Conductor y Visualizador con permisos diferenciados
- **Autenticación Segura**: Sistema basado en RUT chileno con validaciones específicas
- **Control de Acceso**: Permisos granulares según rol del usuario

### Mantenimiento y Operaciones
- **Mantenimiento Preventivo**: Programación automática basada en kilometraje y tiempo
- **Mantenimiento Correctivo**: Registro de reparaciones por fallas reportadas
- **Calendario Interactivo**: Visualización de mantenimientos programados
- **Alertas Automáticas**: Notificaciones de mantenimientos pendientes

### Gestión Financiera
- **Control Presupuestario**: Seguimiento de presupuestos anuales por cuenta SIGFE
- **Órdenes de Compra**: Integración con sistema Mercado Público y registro manual
- **Órdenes de Trabajo**: Gestión de órdenes de trabajo vinculadas a mantenimientos
- **Trazabilidad**: Vinculación completa desde presupuesto hasta ejecución
- **Reportes de Costos**: Análisis detallado de gastos por vehículo y período

### Operativa Diaria
- **Hojas de Ruta**: Registro completo de turnos con personal médico (médico, enfermero, TENS, camillero), kilometraje de inicio y fin
- **Bitácoras de Viaje**: Registro detallado de viajes asociados a cada hoja de ruta con destinos, pacientes y tipo de servicio
- **Control de Combustible**: Seguimiento de cargas, rendimiento y costos
- **Reportes de Incidentes**: Sistema de fallas reportadas por conductores
- **Viajes por Servicio**: Clasificación por tipo (traslados, urgencias, rondas médicas, administrativos)
- **Exportación de Datos**: Exportación consolidada de viajes a formato Excel para análisis externos

### Gestión de Proveedores
- **Proveedores Multi-tipo**: Talleres mecánicos y arrendadores de vehículos
- **Control de Activos**: Habilitación/deshabilitación de proveedores
- **Historial de Servicios**: Seguimiento de trabajos realizados por proveedor

### Reportes y Analytics
- **Dashboard Ejecutivo**: Visión general del estado de la flota
- **Reportes de Disponibilidad**: Análisis de uptime por vehículo
- **Costos por Kilómetro**: Métricas de eficiencia operativa
- **Historial por Unidad**: Reportes detallados de cada vehículo

### Sistema de Arriendos
- **Gestión de Reemplazos**: Arriendos temporales por mantenimiento o averías
- **Control de Costos**: Seguimiento de costos diarios y totales
- **Vinculación a Vehículos**: Asociación con unidades propias reemplazadas

## Tecnologías Utilizadas

- **Backend**: Django 5.0+
- **Base de Datos**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Librerías**: 
  - Pillow (manejo de imágenes)
  - openpyxl (exportación Excel moderna)
  - xlwt (exportación Excel legacy)
  - python-dotenv (gestión de variables de entorno)
  - requests (peticiones HTTP para integraciones)
- **Autenticación**: Sistema personalizado con RUT chileno

## Instalación

1. Clonar el repositorio o descargar los archivos

2. Crear un entorno virtual (recomendado):
```bash
python -m venv venv
```

3. Activar el entorno virtual:
- Windows:
```bash
venv\Scripts\activate
```
- Linux/Mac:
```bash
source venv/bin/activate
```

4. Instalar dependencias:
```bash
pip install -r requirements.txt
```

5. Configurar variables de entorno:
   - Crear un archivo `.env` en la raíz del proyecto
   - Agregar las siguientes variables (ajustar según tu configuración):
   ```env
   MERCADO_PUBLICO_TICKET=tu_ticket_aqui
   ```
   - Nota: El archivo `.env` no debe subirse al repositorio (ya está en `.gitignore`)

6. Configurar la base de datos:
   - Crear base de datos PostgreSQL: `flota_hrn_db`
   - Actualizar credenciales en `gestion_flota/settings.py` si es necesario

7. Realizar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

8. Crear datos iniciales (opcional):
```bash
python manage.py crear_datos_iniciales
```

9. Crear superusuario administrador:
```bash
python manage.py createsuperuser
```

10. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

11. Acceder al sistema en: http://127.0.0.1:8000/

## Estructura del Proyecto

```
proyecto/
├── gestion_flota/                # Configuración del proyecto Django
│   ├── __init__.py
│   ├── settings.py              # Configuración principal
│   ├── urls.py                  # URLs raíz del proyecto
│   ├── asgi.py                  # Configuración ASGI
│   └── wsgi.py                  # Configuración WSGI
├── flota/                       # Aplicación principal
│   ├── models.py                # Modelos de datos (13 entidades)
│   ├── views/                   # Lógica de negocio organizada modularmente
│   │   ├── __init__.py         # Exportación centralizada de vistas
│   │   ├── autenticacion.py    # Vistas de login/logout
│   │   ├── usuarios.py         # Gestión de usuarios
│   │   ├── vehiculos.py        # Gestión de vehículos
│   │   ├── viajes.py           # Hojas de ruta, viajes, combustible e incidentes
│   │   ├── mantenimiento.py    # Mantenimientos preventivos y correctivos
│   │   ├── presupuesto.py      # Gestión presupuestaria
│   │   ├── reportes.py         # Reportes y análisis
│   │   ├── arriendos.py        # Gestión de arriendos
│   │   ├── proveedores.py      # Gestión de proveedores
│   │   ├── ordenes.py          # Órdenes de compra y trabajo
│   │   ├── dashboard.py        # Dashboard ejecutivo
│   │   ├── api.py              # Endpoints API REST
│   │   └── utilidades.py       # Funciones auxiliares
│   ├── urls.py                  # Definición de rutas
│   ├── forms.py                 # Formularios del sistema
│   ├── admin.py                 # Configuración Django Admin
│   ├── apps.py                  # Configuración de la aplicación
│   ├── signals.py               # Señales y lógica automática
│   ├── utils.py                 # Utilidades auxiliares
│   ├── management/              # Comandos de gestión
│   │   └── commands/
│   │       └── crear_datos_iniciales.py
│   ├── migrations/              # Migraciones de base de datos
│   ├── static/                  # Archivos estáticos
│   │   ├── css/                # Estilos personalizados + Bootstrap
│   │   ├── js/                 # Scripts JavaScript
│   │   └── images/             # Recursos gráficos
│   └── templates/flota/         # Plantillas HTML
├── media/                       # Archivos subidos por usuarios
│   └── ordenes_compra/          # PDFs de órdenes de compra
├── manage.py                    # Script de gestión Django
├── requirements.txt             # Dependencias Python
├── README.md                    # Esta documentación
├── THIRD_PARTY_LICENSES.md      # Licencias de terceros
└── .gitignore                   # Archivos ignorados por Git
```

## Base de Datos

El sistema utiliza PostgreSQL. La base de datos incluye las siguientes entidades principales:

- **Usuario**: Gestión de usuarios del sistema con autenticación por RUT
- **Proveedor**: Proveedores de servicios (talleres mecánicos y arrendadores)
- **CuentaPresupuestaria**: Cuentas SIGFE para clasificación presupuestaria
- **Vehiculo**: Información completa de cada vehículo de la flota
- **Presupuesto**: Presupuestos anuales por cuenta SIGFE
- **OrdenCompra**: Órdenes de compra vinculadas a presupuestos
- **OrdenTrabajo**: Órdenes de trabajo para mantenimientos
- **Mantenimiento**: Mantenimientos preventivos y correctivos
- **Arriendo**: Arriendos temporales de vehículos
- **HojaRuta**: Hojas de ruta diarias con personal y kilometraje
- **Viaje**: Viajes individuales asociados a hojas de ruta
- **CargaCombustible**: Registro de cargas de combustible
- **FallaReportada**: Incidentes y fallas reportadas por conductores
- **Alerta**: Alertas automáticas de mantenimiento

## Requisitos del Sistema

### Software
- **Python**: 3.8+
- **Django**: 5.0+
- **PostgreSQL**: 12+
- **Pip**: Para gestión de dependencias

### Roles y Permisos

- **Administrador**: Acceso completo al sistema, puede gestionar usuarios, vehículos, mantenimientos, presupuestos, arriendos y proveedores. Puede modificar hojas de ruta registradas por conductores y exportar datos consolidados.
- **Conductor**: Puede registrar hojas de ruta, viajes, cargas de combustible e incidentes. Puede visualizar sus propios registros y la información general de la flota.
- **Visualizador**: Solo lectura, puede ver información pero no modificar ni registrar datos.

