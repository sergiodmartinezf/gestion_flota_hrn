import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flota', '0010_cuentas_combustible_arriendo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='cargacombustible',
            name='nro_boleta',
        ),
        migrations.AlterField(
            model_name='cargacombustible',
            name='costo_total',
            field=models.IntegerField(validators=[
                django.core.validators.MinValueValidator(1),
                django.core.validators.MaxValueValidator(200000),
            ]),
        ),
        migrations.AlterField(
            model_name='cargacombustible',
            name='kilometraje_al_cargar',
            field=models.IntegerField(validators=[
                django.core.validators.MinValueValidator(0),
                django.core.validators.MaxValueValidator(9999999),
            ]),
        ),
    ]
