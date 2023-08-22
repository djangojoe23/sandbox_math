from django import template

from sandbox_math.algebra.models import CheckSolution, Problem
from sandbox_math.users.models import Mistake

register = template.Library()


@register.filter(name="get_problem_count")
def get_problem_count(arg):
    if arg == "all":
        return Problem.objects.all().count()
    elif arg == "solved":
        solved_states = [CheckSolution.SOLVED, CheckSolution.INFINITELY_MANY, CheckSolution.NO_SOLUTION]
        return CheckSolution.objects.filter(problem_solved__in=solved_states).count()


@register.filter(name="get_mistake_count")
def get_mistake_count(arg):
    if arg == "all":
        return (
            Mistake.objects.filter(mistake_event_type__in=[Mistake.HELP_CLICK, Mistake.PROCEED])
            .exclude(mistake_type=Mistake.NONE)
            .count()
        )
    elif arg == "fixed":
        return (
            Mistake.objects.filter(mistake_event_type__in=[Mistake.HELP_CLICK, Mistake.PROCEED], is_fixed=True)
            .exclude(mistake_type=Mistake.NONE)
            .count()
        )
