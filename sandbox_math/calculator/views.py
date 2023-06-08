from urllib.parse import unquote

from django.views.generic.base import TemplateView

from sandbox_math.calculator.models import Response, UserMessage
from sandbox_math.sandbox.models import Sandbox


# Create your views here.
class GetResponseView(TemplateView):
    template_name = "calculator/response.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_message = unquote(self.request.GET.get("message"))
        problem_id = self.request.GET.get("problem_id")
        sandbox = unquote(self.request.GET.get("sandbox"))
        caller = unquote(self.request.GET.get("caller"))

        user_message_obj = UserMessage.objects.none()
        for s in Sandbox.SANDBOX_TYPES:
            if s[0] == sandbox:
                user_message_obj = UserMessage.save_new(s[0], problem_id, user_message)

        Response.save_new(user_message_obj, caller, Response.NO_CONTEXT)

        context["responses"] = Response.objects.filter(user_message=user_message_obj).order_by("id")

        return context
