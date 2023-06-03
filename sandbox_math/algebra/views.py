from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic.base import TemplateView, View

from sandbox_math.algebra.models import Problem, Step

# from sandbox_math.calculator.models import UserMessage


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

        context["step_prompts"] = BaseView.step_prompts
        context["body_bg"] = "bg-secondary"
        context["variable_options"] = []
        context["is_new_problem"] = True
        context["problem"] = Problem.objects.none()
        context["steps"] = Step.objects.none()

        try:
            saved_problem_id = self.kwargs["problem_id"]
        except KeyError:
            saved_problem_id = None

        if saved_problem_id:
            problem = Problem.objects.get(id=saved_problem_id)
            problem.last_viewed = timezone.now()
            problem.save()
            context["is_new_problem"] = False
            context["problem"] = Problem.objects.get(id=saved_problem_id)
            context["steps"] = Step.objects.filter(problem__id=saved_problem_id).order_by("created")

        return context


class StartNewView(TemplateView):
    template_name = "algebra/new_step.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["step_prompts"] = BaseView.step_prompts
        context["step_num"] = 1
        context["is_new_problem"] = True

        return context


class SaveNewView(View):
    @staticmethod
    def get(request):
        new_saved_problem = Problem.save_new(request.user.id)
        new_saved_problem.last_view = timezone.now()
        new_saved_problem.save()

        first_step = Step.save_new(new_saved_problem)

        return JsonResponse({"unique-problem-id": new_saved_problem.id, "unique-step-id": first_step.id})
