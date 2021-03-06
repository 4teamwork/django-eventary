# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-09-07 12:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventary', '0016_add_configuration_field_for_anonymous_contributions'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='eventhost',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='eventrecurrence',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='eventtimedate',
            name='updated',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='calendar',
            name='allow_anonymous_event_proposals',
            field=models.BooleanField(default=False, verbose_name='visitor is allowed to propose events'),
        ),
    ]
