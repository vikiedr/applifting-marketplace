# Generated by Django 4.1.7 on 2023-11-12 15:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_catalogue', '0002_offercredentials'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offercredentials',
            name='access_token',
            field=models.UUIDField(blank=True, editable=False, null=True),
        ),
    ]