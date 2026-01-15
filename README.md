# Sistema de Gestión de Flota - Hospital Río Negro

Sistema web integral desarrollado en Django para la gestión completa de la flota vehicular del Hospital Río Negro. El sistema permite administrar desde la adquisición hasta el mantenimiento de vehículos, incluyendo control presupuestario, bitácoras de viaje, gestión de combustible, reportes de incidentes y seguimiento de mantenimientos preventivos y correctivos.

## Características Principales

### 🎯 Gestión de Flota
- **Registro de Vehículos**: Control completo de inventario con diferentes tipos de carrocería (ambulancias, sedanes, camionetas, etc.)
- **Estados de Vehículos**: Seguimiento de disponibilidad, mantenimiento, arriendos y baja de unidades
- **Clasificación por Criticidad**: Identificación de vehículos críticos vs no críticos para el servicio
- **Control de Kilometraje**: Seguimiento automático del kilometraje y alertas de mantenimiento

### 👥 Gestión de Usuarios
- **Sistema de Roles**: Administrador, Conductor y Visualizador con permisos diferenciados
- **Autenticación Segura**: Sistema basado en RUT chileno con validaciones específicas
- **Control de Acceso**: Permisos granulares según rol del usuario

### 🔧 Mantenimiento y Operaciones
- **Mantenimiento Preventivo**: Programación automática basada en kilometraje y tiempo
- **Mantenimiento Correctivo**: Registro de reparaciones por fallas reportadas
- **Calendario Interactivo**: Visualización de mantenimientos programados
- **Alertas Automáticas**: Notificaciones de mantenimientos pendientes

### 💰 Gestión Financiera
- **Control Presupuestario**: Seguimiento de presupuestos anuales por cuenta SIGFE
- **Órdenes de Compra**: Integración con sistema Mercado Público
- **Trazabilidad**: Vinculación completa desde presupuesto hasta ejecución
- **Reportes de Costos**: Análisis detallado de gastos por vehículo y período

### 🚗 Operativa Diaria
- **Bitácoras de Viaje**: Registro de turnos, destinos y kilometraje recorrido
- **Control de Combustible**: Seguimiento de cargas, rendimiento y costos
- **Reportes de Incidentes**: Sistema de fallas reportadas por conductores
- **Viajes por Servicio**: Clasificación por tipo (traslados, urgencias, rondas médicas)

### 🏢 Gestión de Proveedores
- **Proveedores Multi-tipo**: Talleres mecánicos y arrendadores de vehículos
- **Control de Activos**: Habilitación/deshabilitación de proveedores
- **Historial de Servicios**: Seguimiento de trabajos realizados por proveedor

### 📊 Reportes y Analytics
- **Dashboard Ejecutivo**: Visión general del estado de la flota
- **Reportes de Disponibilidad**: Análisis de uptime por vehículo
- **Costos por Kilómetro**: Métricas de eficiencia operativa
- **Historial por Unidad**: Reportes detallados de cada vehículo

### 🗓️ Sistema de Arriendos
- **Gestión de Reemplazos**: Arriendos temporales por mantenimiento o averías
- **Control de Costos**: Seguimiento de costos diarios y totales
- **Vinculación a Vehículos**: Asociación con unidades propias reemplazadas

## Tecnologías Utilizadas

- **Backend**: Django 5.0+
- **Base de Datos**: PostgreSQL
- **Frontend**: HTML5, CSS3, JavaScript
- **UI Framework**: Bootstrap 5
- **Librerías**: Pillow (manejo de imágenes), OpenPyXL (exportación Excel)
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

5. Configurar la base de datos:
   - Crear base de datos PostgreSQL: `flota_hrn_db`
   - Actualizar credenciales en `gestion_flota/settings.py` si es necesario

6. Realizar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

7. Crear datos iniciales (opcional):
```bash
python manage.py crear_datos_iniciales
```

8. Crear superusuario administrador:
```bash
python manage.py createsuperuser
```

9. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

8. Acceder al sistema en: http://127.0.0.1:8000/

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
│   ├── models.py                # Modelos de datos (15 entidades)
│   ├── views.py                 # Lógica de negocio (1611 líneas)
│   ├── urls.py                  # Definición de rutas (97 rutas)
│   ├── forms.py                 # Formularios del sistema (532 líneas)
│   ├── admin.py                 # Configuración Django Admin
│   ├── apps.py                  # Configuración de la aplicación
│   ├── signals.py               # Señales y lógica automática
│   ├── utils.py                 # Utilidades auxiliares
│   ├── management/              # Comandos de gestión
│   │   └── commands/
│   │       └── crear_datos_iniciales.py
│   ├── migrations/              # Migraciones de base de datos
│   │   └── 0001_initial.py
│   ├── static/flota/            # Archivos estáticos
│   │   ├── css/                # Estilos personalizados + Bootstrap
│   │   ├── js/                 # Scripts JavaScript (12 archivos)
│   │   └── images/             # Recursos gráficos
│   └── templates/flota/         # Plantillas HTML (54 templates)
├── media/                       # Archivos subidos por usuarios
│   └── ordenes_compra/          # PDFs de órdenes de compra
├── manage.py                    # Script de gestión Django
├── requirements.txt             # Dependencias Python
├── README.md                    # Esta documentación
├── THIRD_PARTY_LICENSES.md      # Licencias de terceros
└── .gitignore                   # Archivos ignorados por Git
```

## Base de Datos

El sistema utiliza PostgreSQL. La base de datos incluye las siguientes tablas:

## Requisitos del Sistema

### Software
- **Python**: 3.8+
- **Django**: 5.0+
- **PostgreSQL**: 12+
- **Pip**: Para gestión de dependencias

- **Administrador**: Acceso completo al sistema, puede gestionar usuarios, vehículos, mantenimientos, presupuestos y arriendos. Puede visualizar bitácoras, cargas de combustible e incidentes pero no registrar nuevos.
- **Conductor**: Puede registrar bitácoras, cargas de combustible e incidentes, además de visualizar los registros existentes.
- **Visualizador**: Solo lectura, puede ver información pero no modificar

