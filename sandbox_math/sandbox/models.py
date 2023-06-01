from django.db import models

# from django.apps import apps


# Create your models here.
class Sandbox(models.Model):
    PREALGEBRA = "Prealgebra"
    ALGEBRA = "Algebra"
    GRAPHS = "Graphs"
    SHAPES = "Shapes"
    SANDBOX_TYPES = [
        (PREALGEBRA, "Pre-algebra"),
        (ALGEBRA, "Algebra"),
        (GRAPHS, "Graphs"),
        (SHAPES, "Shapes"),
    ]

    @classmethod
    def is_problem_solved(cls):
        pass


# MyModel = apps.get_model('app_label', 'MyModel')
