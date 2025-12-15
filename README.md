# Sistema de Gestión de Flota - Hospital Río Negro

Sistema web desarrollado en Django para la gestión integral de la flota de vehículos del Hospital de Río Negro

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

5. Realizar migraciones:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. Crear un superusuario:
```bash
python manage.py createsuperuser
```

7. Ejecutar el servidor de desarrollo:
```bash
python manage.py runserver
```

8. Acceder al sistema en: http://127.0.0.1:8000/

## Estructura del Proyecto

```
proyecto/
├── gestion_flota/          # Configuración del proyecto Django
├── flota/                  # Aplicación principal
│   ├── models.py          # Modelos de base de datos (14 tablas)
│   ├── views.py           # Vistas y lógica de negocio
│   ├── forms.py           # Formularios
│   ├── urls.py            # URLs de la aplicación
│   └── admin.py           # Configuración del admin Django
├── templates/             # Plantillas HTML
│   └── flota/            # Templates de la aplicación
├── static/               # Archivos estáticos (CSS, JS, imágenes)
├── manage.py             # Script de gestión Django
└── requirements.txt       # Dependencias del proyecto
```

## Base de Datos

El sistema utiliza PostgreSQL. La base de datos incluye las siguientes tablas:

1. Usuario
2. Proveedor
3. Vehiculo
4. OrdenCompra
5. OrdenTrabajo
6. Presupuesto
7. Arriendo
8. DisponibilidadVehiculo
9. HojaRuta
10. Viaje
11. CargaCombustible
12. Mantenimiento
13. AlertaMantencion
14. FallaReportada

## Roles de Usuario

- **Administrador**: Acceso completo al sistema, puede gestionar usuarios, vehículos, mantenimientos, presupuestos y arriendos
- **Conductor**: Puede registrar bitácoras, cargas de combustible e incidentes
- **Visualizador**: Solo lectura, puede ver información pero no modificar

