# Generated by Django 4.1.9 on 2023-09-11 08:32

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("algebra", "0014_remove_checkrewrite_other_var_value_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="checkrewrite",
            old_name="other_var_value_expr",
            new_name="other_var_latex_value",
        ),
        migrations.RenameField(
            model_name="checkrewrite",
            old_name="solving_for_value_expr",
            new_name="solving_for_latex_value",
        ),
        migrations.RenameField(
            model_name="checksolution",
            old_name="other_var_value_expr",
            new_name="other_var_latex_value",
        ),
        migrations.RenameField(
            model_name="checksolution",
            old_name="solving_for_value_expr",
            new_name="solving_for_latex_value",
        ),
    ]
