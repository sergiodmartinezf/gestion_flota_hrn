from django.db import models
from django.core.validators import MinValueValidator

class Proveedor(models.Model):
    id = models.AutoField(primary_key=True)
    rut_empresa = models.CharField(max_length=12, unique=True)
    nombre_fantasia = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email_contacto = models.EmailField(blank=True)
    es_taller = models.BooleanField(default=False, verbose_name="Es Taller Mecánico")
    es_arrendador = models.BooleanField(default=False, verbose_name="Es Arrendador de Vehículos")
    es_proveedor_base = models.BooleanField(default=False, verbose_name="Proveedor base (Kaufmann/Arriagada)")
    activo = models.BooleanField(default=True, verbose_name="Activo")
    
    class Meta:
        db_table = 'proveedor'
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
    
    def __str__(self):
        return self.nombre_fantasia


class CuentaPresupuestaria(models.Model):
    id = models.AutoField(primary_key=True)
    codigo = models.CharField(max_length=50, unique=True, help_text="Ej: 22.06.002.001")
    nombre = models.CharField(max_length=200, help_text="Ej: Mantenimiento y Reparación de Vehículos")
    descripcion = models.TextField(blank=True)

    class Meta:
        db_table = 'cuenta_presupuestaria'
        verbose_name = 'Cuenta Presupuestaria (SIGFE)'
        verbose_name_plural = 'Cuentas Presupuestarias'
        ordering = ['codigo']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

