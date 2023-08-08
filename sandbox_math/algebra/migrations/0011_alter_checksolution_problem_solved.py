# Generated by Django 4.1.9 on 2023-08-03 09:46

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("algebra", "0010_checksolution_problem_solved"),
    ]

    operations = [
        migrations.AlterField(
            model_name="checksolution",
            name="problem_solved",
            field=models.CharField(
                choices=[
                    ("solved", "The problem has one answer."),
                    ("inf many", "The problem has infinitely many answers."),
                    ("no solution", "The problem does not have an answer."),
                    ("unsolved", "The problem is not solved yet."),
                ],
                default="unsolved",
                max_length=11,
            ),
        ),
    ]