# Generated by Django 4.1.9 on 2023-09-12 09:27

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0006_user_show_tooltips"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="user",
            name="show_tooltips",
        ),
    ]