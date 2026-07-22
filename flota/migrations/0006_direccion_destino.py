from django.db import migrations, models
import django.db.models.deletion


def seed_direcciones(apps, schema_editor):
    DireccionDestino = apps.get_model('flota', 'DireccionDestino')
    PacienteTraslado = apps.get_model('flota', 'PacienteTraslado')

    vistos = set()
    for texto in (
        PacienteTraslado.objects
        .exclude(direccion_especifica='')
        .exclude(direccion_especifica__isnull=True)
        .values_list('direccion_especifica', flat=True)
    ):
        limpio = (texto or '').strip()[:200]
        if not limpio:
            continue
        clave = limpio.casefold()
        if clave in vistos:
            continue
        vistos.add(clave)
        existente = DireccionDestino.objects.filter(texto__iexact=limpio).first()
        if not existente:
            DireccionDestino.objects.create(texto=limpio)

    for traslado in PacienteTraslado.objects.exclude(direccion_especifica=''):
        limpio = (traslado.direccion_especifica or '').strip()
        if not limpio:
            continue
        dd = DireccionDestino.objects.filter(texto__iexact=limpio).first()
        if dd:
            traslado.direccion_destino_id = dd.id
            traslado.save(update_fields=['direccion_destino'])


class Migration(migrations.Migration):

    dependencies = [
        ('flota', '0005_alerta_solucion'),
    ]

    operations = [
        migrations.CreateModel(
            name='DireccionDestino',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('texto', models.CharField(db_index=True, max_length=200, unique=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Dirección de destino',
                'verbose_name_plural': 'Direcciones de destino',
                'db_table': 'direccion_destino',
                'ordering': ['texto'],
            },
        ),
        migrations.AddField(
            model_name='pacientetraslado',
            name='direccion_destino',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='traslados',
                to='flota.direcciondestino',
                verbose_name='Dirección (de listado anterior)',
            ),
        ),
        migrations.RunPython(seed_direcciones, migrations.RunPython.noop),
    ]
