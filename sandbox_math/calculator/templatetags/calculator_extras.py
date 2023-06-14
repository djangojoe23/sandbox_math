from django import template

from sandbox_math.calculator.models import Content

register = template.Library()


@register.filter(name="get_message_content")
def get_message_content(message_obj):
    return Content.objects.filter(user_message=message_obj).order_by("id")


@register.filter(name="get_response_content")
def get_response_content(message_obj):
    return Content.objects.filter(response_message=message_obj).order_by("id")
