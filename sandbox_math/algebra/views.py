from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic.base import TemplateView, View

from sandbox_math.algebra.models import Problem, Step
from sandbox_math.sandbox.models import Sandbox
from sandbox_math.users.models import HelpClick, Mistake

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


class UpdateStepTypeView(View):
    @classmethod
    def post(cls, request):
        response = None
        step = Step.objects.get(id=int(request.POST["step-id"]))
        if "Define" in request.POST["step-type"]:
            step.step_type = Step.DEFINE
        elif "Rewrite" in request.POST["step-type"]:
            step.step_type = Step.REWRITE
        elif "Arithmetic" in request.POST["step-type"]:
            step.step_type = Step.ARITHMETIC
        elif "Delete" in request.POST["step-type"]:
            step.step_type = Step.DELETE
        else:
            response = JsonResponse({"error": "there was an error updating the step type"})

        if not response:
            step.save()

            feedback = {
                "mistakes": Problem.get_all_steps_mistakes(step.problem),
            }

            response = JsonResponse(feedback)

        return response


class UpdateHelpClickView(View):
    @classmethod
    def post(cls, request):
        response = None
        step = Step.objects.get(id=int(request.POST["step-id"]))
        mistake_titles = Step.get_mistakes(step)

        help_obj = HelpClick.objects.none()
        mistake_index = 0
        if "left" in request.POST["side"]:
            help_obj = HelpClick(
                sandbox=Sandbox.ALGEBRA, object_type=HelpClick.EXPRESSION, object_id=step.left_expr.id
            )
            help_obj.save()
            mistake_index = 0
        elif "right" in request.POST["side"]:
            help_obj = HelpClick(
                sandbox=Sandbox.ALGEBRA, object_type=HelpClick.EXPRESSION, object_id=step.right_expr.id
            )
            help_obj.save()
            mistake_index = 1
        else:
            response = JsonResponse({"error": "there was an error updating the help clicks"})

        if not response:
            Mistake.save_new(help_obj, mistake_titles[mistake_index])
            # remind them how often they check for help or something?
            response = JsonResponse({})

        return response
