# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-22 16:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bug_reports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bugreport',
            name='description',
            field=models.TextField(verbose_name='Provide information about the problem to help us improve our service:'),
        ),
        migrations.AlterField(
            model_name='bugreport',
            name='email',
            field=models.CharField(blank=True, max_length=100, verbose_name='(Optional) Email address:'),
        ),
    ]
