# Generated by Django 3.2.13 on 2022-07-13 16:04

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0026_teacher_remove_join_request'),
    ]

    operations = [
        migrations.AddField(
            model_name='class',
            name='created_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_classes', to='codeforlife.teacher'),
        ),
    ]
