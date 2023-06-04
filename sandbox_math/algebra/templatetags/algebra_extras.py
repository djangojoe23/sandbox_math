from django import template

from sandbox_math.algebra.models import Step
from sandbox_math.users.models import Mistake

register = template.Library()


@register.filter(name="get_step_mistakes")
def get_step_mistakes(step):
    mistakes = Step.get_mistakes(step)

    mistakes_dict = [
        {"side": "left", "title": mistakes[0], "content": ""},
        {"side": "right", "title": mistakes[1], "content": ""},
    ]
    for m in Mistake.MISTAKE_TYPES:
        if m[0] == mistakes[0]:
            mistakes_dict[0]["content"] = m[1]
        if m[0] == mistakes[1]:
            mistakes_dict[1]["content"] = m[1]

    return mistakes_dict


# @register.filter(name="get_check_count")
# def get_check_count(step, side):
#     if step:
#         completed_checks = CheckRewrite.get_matching_completed_checks(step, side)
#     else:
#         completed_checks = CheckRewrite.objects.none()
#
#     return completed_checks.count()
#
#
# @register.filter(name="get_badge_color")
# def get_badge_color(step, side):
#     if step:
#         completed_checks = CheckRewrite.get_matching_completed_checks(step, side)
#         for c in completed_checks:
#             if not c.are_equivalent:
#                 return "danger"
#
#     return "info"
