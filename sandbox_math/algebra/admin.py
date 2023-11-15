from django.contrib import admin

from sandbox_math.algebra.models import CheckRewrite, CheckSolution, Expression, Problem, Step


# Register your models here.
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ["id", "student_id", "variable", "last_viewed"]
    search_fields = ["id"]


@admin.register(Expression)
class ExpressionAdmin(admin.ModelAdmin):
    list_display = ["id", "latex"]
    search_fields = ["id"]


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = ["id", "problem_id", "created", "step_type", "left_expr_id", "right_expr_id"]
    search_fields = ["id", "problem__id", "left_expr__id", "right_expr__id"]


@admin.register(CheckRewrite)
class CheckRewriteAdmin(admin.ModelAdmin):
    list_display = ["id", "problem_id", "start_time", "expr1_id", "expr2_id", "are_equivalent", "end_time"]
    search_fields = ["id"]


@admin.register(CheckSolution)
class CheckSolutionAdmin(admin.ModelAdmin):
    list_display = ["id", "problem_id", "start_time", "expr1_id", "expr2_id", "end_time", "attempt", "problem_solved"]
    search_fields = ["id", "problem__id", "expr1__id", "expr2__id"]
