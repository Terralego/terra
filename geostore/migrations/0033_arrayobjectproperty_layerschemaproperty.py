# Generated by Django 2.2.6 on 2019-11-04 16:49

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0032_auto_20191016_0844'),
    ]

    operations = [
        migrations.CreateModel(
            name='LayerSchemaProperty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField()),
                ('title', models.CharField(max_length=250)),
                ('prop_type', models.CharField(max_length=50)),
                ('options', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Define extra options to json schema property')),
                ('layer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schema_properties', to='geostore.Layer')),
            ],
            options={
                'verbose_name': 'Schema property',
                'verbose_name_plural': 'Schema properties',
            },
        ),
        migrations.CreateModel(
            name='ArrayObjectProperty',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('slug', models.SlugField()),
                ('title', models.CharField(max_length=250)),
                ('prop_type', models.CharField(max_length=50)),
                ('options', django.contrib.postgres.fields.jsonb.JSONField(default=dict, help_text='Define extra options to json schema property')),
                ('array_property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='array_properties', to='geostore.LayerSchemaProperty')),
            ],
            options={
                'verbose_name': 'Array object schema property',
                'verbose_name_plural': 'Array object schema properties',
            },
        ),
    ]