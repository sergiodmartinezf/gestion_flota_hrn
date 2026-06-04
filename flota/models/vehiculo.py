from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

class Vehiculo(models.Model):
    ESTADOS = [
        ('Disponible', 'Disponible'),
        ('En uso', 'En uso'),
        ('En mantenimiento', 'En mantenimiento'),
        ('Fuera de servicio', 'Fuera de servicio'),
        ('Baja', 'Dado de Baja'),
    ]
    
    TIPOS_PROPIEDAD = [
        ('Propio', 'Propio'),
        ('Arrendado', 'Arrendado (Reemplazo)'),
    ]
    
    TIPOS_CARROCERIA = [
        ('Ambulancia', 'Ambulancia'),
        ('Sedán', 'Sedán'),
        ('Station Vagon', 'Station Vagon'),
        ('Camioneta', 'Camioneta'),
        ('Minibús', 'Minibús'),
        ('Furgón', 'Furgón'),
        ('Camión', 'Camión'),
        ('Carro de Arrastre', 'Carro de Arrastre'),
    ]
    
    CRITICIDAD = [
        ('Crítico', 'Crítico'),
        ('No crítico', 'No crítico'),
    ]
    
    id = models.AutoField(primary_key=True)
    patente = models.CharField(max_length=10, unique=True)
    marca = models.CharField(max_length=50)
    modelo = models.CharField(max_length=50)
    vin = models.CharField(max_length=17, blank=True)
    nro_motor = models.CharField(max_length=50, blank=True)
    anio_adquisicion = models.IntegerField()
    
    vida_util = models.IntegerField(default=10, help_text="Años de vida útil estimada")
    kilometraje_actual = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    
    # Mantenimiento
    umbral_mantencion = models.IntegerField(default=10000, help_text="Kms entre mantenciones preventivas")
    
    # Clasificación
    tipo_carroceria = models.CharField(max_length=20, choices=TIPOS_CARROCERIA)
    CLASES_AMBULANCIA = [
        ('URBANA (4X2)', 'URBANA (4X2)'),
        ('TODO TERRENO (4X4)', 'TODO TERRENO (4X4)'),
        ('MARÍTIMO (LANCHA)', 'MARÍTIMO (LANCHA)'),
    ]
    
    clase_ambulancia = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        choices=CLASES_AMBULANCIA,
        verbose_name="Clase Ambulancia"
    )
    es_samu = models.BooleanField(default=False, verbose_name="Pertenece a SAMU")
    establecimiento = models.CharField(max_length=200, default='Hospital Río Negro')
    criticidad = models.CharField(max_length=20, choices=CRITICIDAD, default='No crítico')
    es_backup = models.BooleanField(
        default=False, 
        verbose_name="¿Es vehículo de backup?"
    )
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Disponible')
    tipo_propiedad = models.CharField(max_length=30, choices=TIPOS_PROPIEDAD, default='Propio')
    
    creado_en = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'vehiculo'
        verbose_name = 'Vehículo'
        verbose_name_plural = 'Vehículos'
    
    def __str__(self):
        return f"{self.patente} - {self.marca} {self.modelo}"

    @property
    def kilometraje_para_mantencion(self):
        """Calcula cuántos kilómetros faltan para el próximo mantenimiento"""
        if self.umbral_mantencion > 0:
            resto = self.kilometraje_actual % self.umbral_mantencion
            return max(0, self.umbral_mantencion - resto)
        return 0

    @classmethod
    def objetos_operativos(cls):
        from django.db.models import OuterRef, Subquery, F, Value, IntegerField, Case, When
        from .mantenimiento import Mantenimiento

        last_maint = Mantenimiento.objects.filter(
            vehiculo=OuterRef('pk'),
            tipo_mantencion='Preventivo',
            estado='Finalizado'
        ).order_by('-fecha_salida').values('km_al_ingreso')[:1]

        qs = cls.objects.filter(estado__in=['Disponible', 'En uso']).annotate(
            ultimo_km=Subquery(last_maint, output_field=IntegerField())
        ).annotate(
            recorrido=Case(
                When(ultimo_km__isnull=True, then=Value(0)), 
                default=F('kilometraje_actual') - F('ultimo_km'),
                output_field=IntegerField()
            )
        ).filter(recorrido__lt=12000)
        return qs

    @classmethod
    def queryset_para_hoja_ruta(cls, incluir_pk=None):
        """Operativos más vehículos con hoja abierta (aunque otro conductor los use)."""
        from .operativa import HojaRuta

        qs = cls.objetos_operativos()
        ids_en_hoja_abierta = set(
            HojaRuta.objects.filter(abierta=True).values_list('vehiculo_id', flat=True)
        )
        if incluir_pk:
            ids_en_hoja_abierta.add(incluir_pk)
        if ids_en_hoja_abierta:
            qs = (qs | cls.objects.filter(pk__in=ids_en_hoja_abierta)).distinct()
        return qs.order_by('patente')

    def save(self, *args, **kwargs):
        from .operativa import Alerta

        # Guardar primero para tener el ID
        super().save(*args, **kwargs)

        # Obtener el último mantenimiento preventivo finalizado
        ultimo_mant = self.mantenimientos.filter(
            tipo_mantencion='Preventivo',
            estado='Finalizado'
        ).order_by('-fecha_salida').first()

        # Si no hay mantenimiento preventivo, no se generan alertas de kilometraje
        if not ultimo_mant:
            # Eliminar posibles alertas previas de kilometraje (por si acaso)
            Alerta.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[8000, 12000]
            ).update(vigente=False, resuelta_en=timezone.now())
            return

        km_base = ultimo_mant.km_al_ingreso
        recorrido = self.kilometraje_actual - km_base

        UMBRAL_PREVENTIVO = 8000
        UMBRAL_CRITICO = 12000

        if recorrido >= UMBRAL_CRITICO:
            nuevo_umbral = UMBRAL_CRITICO
            descripcion = (
                f'ALERTA CRÍTICA: {recorrido} km desde última mantención '
                f'(supera los {UMBRAL_CRITICO} km). Vehículo bloqueado para operación.'
            )
            if self.estado not in ['Fuera de servicio', 'Baja']:
                self.estado = 'Fuera de servicio'
                # Guardamos el cambio de estado (evitamos recursión usando update_fields)
                Vehiculo.objects.filter(pk=self.pk).update(estado=self.estado)

        elif recorrido >= UMBRAL_PREVENTIVO:
            nuevo_umbral = UMBRAL_PREVENTIVO
            descripcion = (
                f'Alerta por kilometraje: {recorrido} km desde última mantención '
                f'(umbral {UMBRAL_PREVENTIVO} km). Programar mantenimiento.'
            )
        else:
            # Si el recorrido es menor a 8000, no debe haber alerta de kilometraje vigente.
            Alerta.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[UMBRAL_PREVENTIVO, UMBRAL_CRITICO]
            ).update(vigente=False, resuelta_en=timezone.now())
            return

        # Manejo de alertas existentes
        alerta_existente = Alerta.objects.filter(
            vehiculo=self,
            vigente=True,
            valor_umbral=nuevo_umbral
        ).first()

        if alerta_existente:
            alerta_existente.descripcion = descripcion
            alerta_existente.save()
        else:
            # Desactivar la otra alerta si existe
            Alerta.objects.filter(
                vehiculo=self,
                vigente=True,
                valor_umbral__in=[UMBRAL_PREVENTIVO, UMBRAL_CRITICO]
            ).exclude(valor_umbral=nuevo_umbral).update(vigente=False, resuelta_en=timezone.now())

            Alerta.objects.create(
                vehiculo=self,
                descripcion=descripcion,
                valor_umbral=nuevo_umbral
            )
