from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.generic.base import TemplateView, View
from django.views.generic.list import ListView
from guest_user.mixins import AllowGuestUserMixin
from guest_user.models import is_guest_user

from sandbox_math.algebra.models import CheckRewrite, CheckSolution, Expression, Problem, Step
from sandbox_math.calculator.models import UserMessage
from sandbox_math.sandbox.models import Sandbox
from sandbox_math.users.models import HelpClick, Mistake, Proceed, User


# Create your views here.
class BaseView(AllowGuestUserMixin, TemplateView):
    template_name = "algebra/base.html"
    step_prompts = {
        1: "What do you need to do before you start?",
        2: "What is your first step going to be?",
        3: "What are you going to do next?",
    }

    def get(self, request, *args, **kwargs):
        try:
            saved_problem_id = self.kwargs["problem_id"]
        except KeyError:
            saved_problem_id = None

        if not saved_problem_id:
            # user is just browsing to algebra base view without any problem id
            context = self.get_context_data()
            return self.render_to_response(context)
        else:
            try:
                Problem.objects.get(student_id=self.request.user.id, id=saved_problem_id)
                context = self.get_context_data()
                return self.render_to_response(context)
            except Problem.DoesNotExist:
                # the problem that is trying to be accessed is not associated with the account trying to access it
                try:
                    problem = Problem.objects.get(id=saved_problem_id)
                    requester = User.objects.get(id=self.request.user.id)
                    if is_guest_user(requester):
                        # create a new problem like this one
                        new_saved_problem = Problem.save_new(request.user.id)
                        new_saved_problem.last_view = timezone.now()
                        new_saved_problem.variable = problem.variable
                        new_saved_problem.save()

                        step_one = Step.save_new(new_saved_problem)
                        Step.copy_step(
                            Step.objects.filter(problem_id=problem.id).order_by("created").first(), step_one
                        )

                        return redirect(f"/algebra/{new_saved_problem.id}")
                    else:
                        try:
                            guest_id = self.request.GET.get("guest-id")
                        except KeyError:
                            guest_id = None

                        if guest_id and is_guest_user(User.objects.get(id=guest_id)):
                            problem.student = requester
                            problem.save()
                            return redirect(f"/algebra/{saved_problem_id}")
                        else:
                            # create a new problem like this one
                            new_saved_problem = Problem.save_new(request.user.id)
                            new_saved_problem.last_view = timezone.now()
                            new_saved_problem.variable = problem.variable
                            new_saved_problem.save()

                            step_one = Step.save_new(new_saved_problem)
                            Step.copy_step(
                                Step.objects.filter(problem_id=problem.id).order_by("created").first(), step_one
                            )

                            return redirect(f"/algebra/{new_saved_problem.id}")
                except Problem.DoesNotExist:
                    # there was a problem id on the URL but it not a known problem
                    return redirect("/algebra/")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["step_prompts"] = BaseView.step_prompts
        context["variable_options"] = []
        context["is_new_problem"] = True
        context["problem"] = Problem.objects.none()
        context["steps"] = Step.objects.none()
        context["previous_user_messages"] = UserMessage.objects.none()
        context["problem_finished"] = "unfinished"

        try:
            saved_problem_id = self.kwargs["problem_id"]
        except KeyError:
            saved_problem_id = None

        if saved_problem_id:
            try:
                problem = Problem.objects.get(student_id=self.request.user.id, id=saved_problem_id)
                problem.last_viewed = timezone.now()
                problem.save()
                context["is_new_problem"] = False
                context["problem"] = problem
                context["steps"] = Step.objects.filter(problem_id=saved_problem_id).order_by("created")
                context["previous_user_messages"] = UserMessage.get_all_previous_for_problem(
                    Sandbox.ALGEBRA, saved_problem_id
                )
                solved_states = [CheckSolution.SOLVED, CheckSolution.INFINITELY_MANY, CheckSolution.NO_SOLUTION]
                if CheckSolution.objects.filter(problem=context["problem"], problem_solved__in=solved_states):
                    context["problem_finished"] = "finished"
                    for step_mistakes in Problem.get_all_steps_mistakes(context["problem"]).items():
                        if (
                            step_mistakes[1][0]["title"] != Mistake.NONE
                            or step_mistakes[1][1]["title"] != Mistake.NONE
                        ):
                            context["problem_finished"] = "unfinished"
            except Problem.DoesNotExist:
                # the problem that is trying to be accessed is not associated with the account trying to access it
                # This must be an invalid problem and I am not sure how we would have gotten here
                pass

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
    @classmethod
    def get(cls, request):
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

        stop_check_rewrite = False

        active_processes = CheckRewrite.objects.filter(problem=step.problem, end_time__isnull=True)
        # check if there is an active check process
        if active_processes.count() == 1:
            active_process = active_processes.first()
            if active_process.expr1 in [step.left_expr, step.right_expr]:
                # the step type was changed for the step that rewrite button that was clicked
                # need to cancel the rewrite process
                stop_check_rewrite = True

        stop_check_solution = False
        if CheckSolution.objects.filter(problem=step.problem, end_time__isnull=True):
            stop_check_solution = True

        if not response:
            step.save()

            feedback = {
                "mistakes": Problem.get_all_steps_mistakes(step.problem),
                "stop_check_rewrite": stop_check_rewrite,
                "stop_check_solution": stop_check_solution,
                "variable_isolated": Problem.variable_isolated_side(step.problem),
            }

            response = JsonResponse(feedback)

        return response


class UpdateExpressionView(View):
    @classmethod
    def post(cls, request):
        response = None
        step = Step.objects.get(id=int(request.POST["step-id"]))

        side = None
        if "left" in request.POST["side"]:
            side = "left"
            step.left_expr.latex = request.POST["expression"]
            step.left_expr.save()
        elif "right" in request.POST["side"]:
            side = "right"
            step.right_expr.latex = request.POST["expression"]
            step.right_expr.save()
        else:
            response = JsonResponse({"error": "there was an error updating the expression"})

        stop_check = None  # could be stopping a check rewrite or a check solution
        if not response:
            all_steps = Step.objects.filter(problem=step.problem).order_by("created")

            left_var_options = Expression.get_variables_in_latex_expression(all_steps.first().left_expr.latex)
            right_var_options = Expression.get_variables_in_latex_expression(all_steps.first().right_expr.latex)
            variable_options = set(left_var_options + right_var_options)

            if CheckRewrite.is_currently_checking(step.id, side):
                active_process = CheckRewrite.objects.get(problem=step.problem, end_time__isnull=True)
                if active_process.expr1 == getattr(step, f"{side}_expr"):
                    # step with expression changed is the rewrite step
                    if active_process.expr1_latex != getattr(step, f"{side}_expr").latex:
                        stop_check = "rewrite"
                else:
                    # step with the expression changed is the previous step
                    if active_process.expr2_latex != getattr(step, f"{side}_expr").latex:
                        stop_check = "rewrite"
            elif CheckSolution.objects.filter(problem=step.problem, end_time__isnull=True).count():
                stop_check = "solution"

            # Editing an expression could have an effect on it's badge count, the previous step's badge count, or the
            # next one's
            badge_updates = {}
            for e in range(0, 3):
                step_to_match = step
                if e == 0:
                    step_to_match = Step.get_prev(step)
                elif e == 1:
                    step_to_match = Step.get_next(step)

                if step_to_match:
                    completed_checks = CheckRewrite.get_matching_completed_checks("CheckRewrite", step_to_match, side)
                    badge_updates[step_to_match.id] = {
                        "count": completed_checks.count(),
                        "color": "info",
                    }
                    for p in completed_checks:
                        if not p.are_equivalent:
                            badge_updates[step_to_match.id]["color"] = "danger"
            feedback = {
                "variable_options": sorted(list(variable_options)),
                "mistakes": Problem.get_all_steps_mistakes(step.problem),
                "stop_check": stop_check,
                "badge_updates": badge_updates,
                "variable_isolated": Problem.variable_isolated_side(step.problem),
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
            "variable_isolated": Problem.variable_isolated_side(problem),
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
        context["step_num"] = len(Step.objects.filter(problem_id=problem_id))
        context["is_new_problem"] = False

        return context


class DeleteStepView(View):
    @classmethod
    def post(cls, request):
        step = Step.objects.get(id=request.POST["step-id"])

        stop_check = None
        if CheckRewrite.is_currently_checking(step.id, "left") or CheckRewrite.is_currently_checking(step.id, "right"):
            stop_check = "rewrite"

        step.left_expr.delete()
        step.right_expr.delete()
        step.delete()

        feedback = {"mistakes": Problem.get_all_steps_mistakes(step.problem), "stop_check": stop_check}

        return JsonResponse(feedback)


# Create your views here.
class RecentTableView(ListView):
    model = Problem
    context_object_name = "recent_problems"
    paginate_by = 10

    def get_template_names(self):
        template = "algebra/recent_table/base.html"
        if self.request.GET.get("update_body"):
            template = "algebra/recent_table/body.html"
        elif self.request.GET.get("update_pagination"):
            template = "algebra/recent_table/pagination.html"

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
