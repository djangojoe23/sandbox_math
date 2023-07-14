from django import template
from guest_user.functions import is_guest_user

register = template.Library()


@register.filter(name="custom_is_guest_user")
def custom_is_guest_user(user_obj):
    if not user_obj:
        return False
    else:
        return is_guest_user(user_obj)
