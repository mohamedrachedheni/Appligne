# Generated by Django 5.0 on 2024-04-20 08:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eleves', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eleve',
            name='adresse',
            field=models.CharField(max_length=255, null=True),
        ),
    ]
