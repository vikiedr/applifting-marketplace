# Generated by Django 4.2.7 on 2023-11-15 06:21

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('product_catalogue', '0004_alter_offercredentials_access_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='offer',
            name='closed_at',
            field=models.DateTimeField(default=None, null=True),
        ),
        migrations.AddField(
            model_name='offer',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
