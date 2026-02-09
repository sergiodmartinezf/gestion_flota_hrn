import os
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps

class Command(BaseCommand):
    help = 'Lee el archivo .txt de SQL e inserta los datos sincronizando secuencias.'

    def handle(self, *args, **options):
        # 1. Configurar ruta (busca el .txt en la misma carpeta que este script)
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_sql = os.path.join(directorio_actual, 'datos_base.txt')
        
        if not os.path.exists(ruta_sql):
            self.stdout.write(self.style.ERROR(f'No se encontró el archivo: {ruta_sql}'))
            return

        # 2. Leer el contenido del SQL
        with open(ruta_sql, 'r', encoding='utf-8') as f:
            sql_completo = f.read()

        # 3. Ejecutar la inserción
        try:
            with connection.cursor() as cursor:
                self.stdout.write(self.style.WARNING(' -> Insertando registros...'))
                cursor.execute(sql_completo)
            self.stdout.write(self.style.SUCCESS('✅ ¡Datos insertados correctamente!'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error al insertar: {e}'))
            return

        # 4. SINCRONIZACIÓN AUTOMÁTICA (La clave del éxito)
        self.stdout.write(self.style.WARNING(' -> Sincronizando contadores de ID (Secuencias)...'))
        
        with connection.cursor() as cursor:
            # Obtenemos los modelos de tu app 'flota'
            app_models = apps.get_app_config('flota').get_models()
            
            for model in app_models:
                # Si el modelo tiene un ID autoincremental
                if model._meta.pk and model._meta.pk.get_internal_type() in ('AutoField', 'BigAutoField'):
                    tabla = model._meta.db_table
                    columna = model._meta.pk.column
                    
                    # SQL para poner el contador en el máximo actual + 1
                    sql_reseteo = f"""
                        SELECT setval(
                            pg_get_serial_sequence('"{tabla}"', '{columna}'), 
                            coalesce(max("{columna}"), 1), 
                            max("{columna}") IS NOT null
                        ) FROM "{tabla}";
                    """
                    cursor.execute(sql_reseteo)
                    self.stdout.write(f'    OK: {tabla}')

        self.stdout.write(self.style.SUCCESS('🚀 ¡Proceso terminado! Ya puedes usar la web sin errores.'))
        