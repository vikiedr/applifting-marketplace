# Generated by Django 4.2.7 on 2023-11-12 16:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('product_catalogue', '0003_alter_offercredentials_access_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='offercredentials',
            name='access_token',
            field=models.CharField(default='', max_length=255),
            preserve_default=False,
        ),
    ]