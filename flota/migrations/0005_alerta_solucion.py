from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flota', '0004_viaje_no_aplica_defaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='alerta',
            name='se_realizo_accion',
            field=models.BooleanField(default=False, verbose_name='Se realizó una acción'),
        ),
        migrations.AddField(
            model_name='alerta',
            name='solucion',
            field=models.TextField(blank=True, default='', verbose_name='Solución / acción realizada'),
        ),
    ]
