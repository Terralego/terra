# Generated by Django 2.2.6 on 2019-10-07 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0029_auto_20190926_0803'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='layer',
            options={'ordering': ['id'], 'permissions': (('can_manage_layers', 'Has all permissions on layers'), ('can_export_layers', 'Is able to export layers'), ('can_import_layers', 'Is able to import layers'))},
        ),
    ]
