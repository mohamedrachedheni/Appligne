# Generated by Django 5.0 on 2024-01-03 14:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0034_experience_cathegorie_alter_experience_options_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experience',
            name='fin',
            field=models.DateField(blank=True, null=True),
        ),
    ]
