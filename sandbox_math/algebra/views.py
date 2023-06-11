from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.utils import timezone
from django.views.generic.base import TemplateView, View
from django.views.generic.list import ListView

from sandbox_math.algebra.models import Expression, Problem, Step
from sandbox_math.calculator.models import UserMessage
from sandbox_math.sandbox.models import Sandbox
from sandbox_math.users.models import HelpClick, Mistake, Proceed


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
        context["previous_user_messages"] = UserMessage.objects.none()

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
            context["previous_user_messages"] = UserMessage.get_all_previous_for_problem(
                Sandbox.ALGEBRA, saved_problem_id
            )

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


class UpdateExpressionView(View):
    @classmethod
    def post(cls, request):
        response = None
        step = Step.objects.get(id=int(request.POST["step-id"]))

        if "left" in request.POST["side"]:
            step.left_expr.latex = request.POST["expression"]
            step.left_expr.save()
        elif "right" in request.POST["side"]:
            step.right_expr.latex = request.POST["expression"]
            step.right_expr.save()
        else:
            response = JsonResponse({"error": "there was an error updating the expression"})

        if not response:
            first_step = Step.objects.filter(problem=step.problem).order_by("created").first()

            left_var_options = Expression.get_variables_in_latex_expression(first_step.left_expr.latex)
            right_var_options = Expression.get_variables_in_latex_expression(first_step.right_expr.latex)
            variable_options = set(left_var_options + right_var_options)

            feedback = {
                "variable_options": sorted(list(variable_options)),
                "mistakes": Problem.get_all_steps_mistakes(step.problem),
            }

            response = JsonResponse(feedback)

        return response


class UpdateVariableView(View):
    @classmethod
    def post(cls, request):
        problem = Problem.objects.get(id=request.POST["problem-id"])
        problem.variable = request.POST["variable"]
        problem.save()

        feedback = {
            "mistakes": Problem.get_all_steps_mistakes(problem),
        }

        return JsonResponse(feedback)


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


class AttemptNewStepView(View):
    @classmethod
    def post(cls, request):
        problem = Problem.objects.get(id=request.POST["problem-id"])

        proceed_obj = Proceed(sandbox=Sandbox.ALGEBRA, problem_id=problem.id, proceed_type=Proceed.ADD_STEP)
        proceed_obj.save()

        next_action = "append"
        for step in Step.objects.filter(problem=problem).order_by("created"):
            mistake_titles = Step.get_mistakes(step)
            if mistake_titles[0] != Mistake.NONE or mistake_titles[1] != Mistake.NONE:
                if mistake_titles[0] != Mistake.NONE:
                    mistake_obj = Mistake(
                        mistake_type=mistake_titles[0], mistake_event_type=Mistake.PROCEED, event_id=proceed_obj.id
                    )
                    mistake_obj.save()
                if mistake_titles[1] != Mistake.NONE:
                    mistake_obj = Mistake(
                        mistake_type=mistake_titles[1], mistake_event_type=Mistake.PROCEED, event_id=proceed_obj.id
                    )
                    mistake_obj.save()

            if not step.left_expr.latex or len(step.left_expr.latex) == 0:
                next_action = "alert"
            elif not step.right_expr.latex or len(step.right_expr.latex) == 0:
                next_action = "alert"

        if next_action == "append":
            new_step = Step.save_new(problem)

            return JsonResponse({"next_action": next_action, "new_step_id": new_step.id})
        else:
            return JsonResponse({"next_action": next_action})


class NewStepView(TemplateView):
    template_name = "algebra/new_step.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query_string = self.request.META["QUERY_STRING"]

        problem_id = None
        for param in query_string.split("&"):
            param_value_split = param.split("=")
            if param_value_split[0] == "problem-id":
                problem_id = int(param_value_split[1])

        context["step_prompts"] = BaseView.step_prompts
        context["step_num"] = len(Step.objects.filter(problem__id=problem_id))
        context["is_new_problem"] = False

        return context


class DeleteStepView(View):
    @classmethod
    def post(cls, request):
        step = Step.objects.get(id=request.POST["step-id"])

        step.left_expr.delete()
        step.right_expr.delete()
        step.delete()

        feedback = {
            "mistakes": Problem.get_all_steps_mistakes(step.problem),
        }

        return JsonResponse(feedback)


# Create your views here.
class RecentTableView(ListView):
    model = Problem
    context_object_name = "recent_problems"
    paginate_by = 10

    def get_template_names(self):
        template = "algebra/recent_table/base.html"
        if self.request.GET.get("update_body"):
            template = "student/recent_table/body.html"
        elif self.request.GET.get("update_pagination"):
            template = "student/recent_table/pagination.html"

        return template

    def get_paginate_by(self, queryset):
        try:
            paginate_by = int(self.request.GET.get("paginate_by", self.paginate_by))
        except ValueError:
            paginate_by = 0
        if paginate_by % 10 != 0:
            recent_qs = self.get_queryset()
            if recent_qs.count() <= 50:
                paginate_by = recent_qs.count()
            else:
                paginate_by = 50
        return paginate_by

    def get_queryset(self):
        recent_filter = {
            "status": self.request.GET.get("status"),
            "order_by": self.request.GET.get("order_by"),
            "equation": self.request.GET.get("equation"),
        }
        recent_qs = Problem.populate_recent_table(self.request.user.id, recent_filter)
        return recent_qs
