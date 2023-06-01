from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic.base import TemplateView


# Create your views here.
class BaseView(UserPassesTestMixin, TemplateView):
    template_name = "algebra/base.html"
    step_prompts = {
        1: "What do you need to do before you start?",
        2: "What is your first step going to be?",
        3: "What are you going to do next?",
    }

    def test_func(self):
        return self.request.user.is_authenticated

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["body_bg"] = "bg-secondary"

        return context
