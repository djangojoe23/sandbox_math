# Generated by Django 4.1.9 on 2023-06-16 08:44

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("algebra", "0004_alter_checkrewrite_are_equivalent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="step",
            name="left_expr",
            field=models.OneToOneField(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="left_side_step",
                to="algebra.expression",
            ),
        ),
        migrations.AlterField(
            model_name="step",
            name="right_expr",
            field=models.OneToOneField(
                default=None,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="right_side_step",
                to="algebra.expression",
            ),
        ),
    ]