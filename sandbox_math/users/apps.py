from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "sandbox_math.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import sandbox_math.users.signals  # noqa: F401
        except ImportError:
            pass
