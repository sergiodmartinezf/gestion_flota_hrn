from django.db import migrations
from django.db.models import Sum


CUENTA_COMBUSTIBLE = '22.03.001'
CUENTA_ARRIENDO = '22.09.003'


def agregar_cuentas_y_reasignar_gastos(apps, schema_editor):
    db = schema_editor.connection.alias
    Cuenta = apps.get_model('flota', 'CuentaPresupuestaria')
    Presupuesto = apps.get_model('flota', 'Presupuesto')
    CargaCombustible = apps.get_model('flota', 'CargaCombustible')
    Arriendo = apps.get_model('flota', 'Arriendo')
    Mantenimiento = apps.get_model('flota', 'Mantenimiento')
    OrdenCompra = apps.get_model('flota', 'OrdenCompra')

    combustible, _ = Cuenta.objects.using(db).get_or_create(
        codigo=CUENTA_COMBUSTIBLE,
        defaults={
            'nombre': 'Combustible y lubricantes para vehículos',
            'descripcion': '',
        },
    )
    arriendo, _ = Cuenta.objects.using(db).get_or_create(
        codigo=CUENTA_ARRIENDO,
        defaults={'nombre': 'Arriendo', 'descripcion': ''},
    )

    # Normaliza registros existentes, incluidos los que quedaron con una cuenta
    # de mantención por el selector oculto del formulario de combustible.
    CargaCombustible.objects.using(db).all().update(
        cuenta_presupuestaria_id=combustible.pk,
    )
    Arriendo.objects.using(db).all().update(
        cuenta_presupuestaria_id=arriendo.pk,
    )

    # Recalcula los montos guardados para todas las cuentas/años existentes.
    for presupuesto in Presupuesto.objects.using(db).all().iterator():
        cuenta_id = presupuesto.cuenta_id
        anio = presupuesto.anio
        total = 0

        mantenciones = Mantenimiento.objects.using(db).filter(
            cuenta_presupuestaria_id=cuenta_id,
            fecha_ingreso__year=anio,
            estado='Finalizado',
        )
        total += mantenciones.aggregate(total=Sum('costo_total_real'))['total'] or 0
        total += CargaCombustible.objects.using(db).filter(
            cuenta_presupuestaria_id=cuenta_id,
            fecha__year=anio,
        ).aggregate(total=Sum('costo_total'))['total'] or 0
        total += Arriendo.objects.using(db).filter(
            cuenta_presupuestaria_id=cuenta_id,
            fecha_inicio__year=anio,
            estado='Activo',
            activo=True,
        ).aggregate(total=Sum('costo_total'))['total'] or 0

        oc_ids_en_mantenciones = mantenciones.filter(
            orden_compra_id__isnull=False,
        ).values_list('orden_compra_id', flat=True)
        ordenes = OrdenCompra.objects.using(db).filter(
            cuenta_presupuestaria_id=cuenta_id,
            fecha_emision__year=anio,
        ).exclude(estado='Anulada').exclude(id__in=oc_ids_en_mantenciones)
        total += ordenes.aggregate(total=Sum('monto_total'))['total'] or 0

        presupuesto.monto_ejecutado = total
        if presupuesto.monto_asignado > 0 and total >= presupuesto.monto_asignado:
            presupuesto.activo = False
        presupuesto.save(using=db, update_fields=['monto_ejecutado', 'activo'])


class Migration(migrations.Migration):
    dependencies = [
        ('flota', '0009_alter_mantenimiento_descripcion_trabajo'),
    ]

    operations = [
        migrations.RunPython(
            agregar_cuentas_y_reasignar_gastos,
            migrations.RunPython.noop,
        ),
    ]
