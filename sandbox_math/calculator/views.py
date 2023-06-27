from django.utils import timezone
from django.views.generic.base import TemplateView

from sandbox_math.algebra.models import CheckRewrite, CheckSolution, Problem, Step
from sandbox_math.calculator.models import Response, UserMessage
from sandbox_math.sandbox.models import Sandbox
from sandbox_math.users.models import Mistake


# Create your views here.
class GetResponseView(TemplateView):
    template_name = "calculator/response.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_message = self.request.GET.get("message")
        problem_id = self.request.GET.get("problem_id")
        sandbox = self.request.GET.get("sandbox")
        caller = self.request.GET.get("caller")

        user_message_obj = UserMessage.objects.none()
        for s in Sandbox.SANDBOX_TYPES:
            if s[0] == sandbox:
                user_message_obj = UserMessage.save_new(s[0], problem_id, user_message)

        current_context = Response.get_context_of_last_response(user_message_obj)
        print(caller, current_context)
        if caller == "SubmitUserMessage":
            if current_context == Response.NO_CONTEXT:
                # User is submitting a message with no context (looking for an arithmetic response)
                Response.with_no_context(user_message_obj)
            elif current_context == Response.CHOOSE_REWRITE_VALUES:
                if user_message == "stop":
                    CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, None)
                else:
                    # User is submitting a message to continue a check rewrite
                    CheckRewrite.create_assign_value_response(user_message_obj)
            elif current_context == Response.CHECK_REWRITE:
                if user_message == "stop":
                    CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, None)
                else:
                    CheckRewrite.create_substitute_values_response(user_message_obj)

                    # change badge count or color here if a check rewrite process ended successfully
                    if Response.get_context_of_last_response(user_message_obj) == Response.NO_CONTEXT:
                        just_finished_check = (
                            CheckRewrite.objects.filter(problem_id=problem_id, end_time__isnull=False)
                            .order_by("-end_time")
                            .first()
                        )
                        if hasattr(just_finished_check.expr1, "left_side_step"):
                            side = "left"
                        else:
                            side = "right"

                        other_matching_finished_processes = CheckRewrite.get_matching_completed_checks(
                            "CheckRewrite", getattr(just_finished_check.expr1, f"{side}_side_step"), side
                        )
                        context["badge_step_id"] = getattr(just_finished_check.expr1, f"{side}_side_step").id
                        context["new_badge_count"] = other_matching_finished_processes.count()
                        context["new_badge_color"] = "info"
                        for p in other_matching_finished_processes:
                            if not p.are_equivalent:
                                context["new_badge_color"] = "danger"
                        context["new_badge_count_side"] = side
            elif current_context == Response.CHOOSE_SOLUTION_VALUES:
                if user_message == "stop":
                    CheckSolution.create_stop_response("CheckSolution", user_message_obj, None)
                else:
                    # User is submitting a message to continue a check rewrite
                    CheckSolution.create_assign_value_response(user_message_obj)
            elif current_context == Response.CHECK_SOLUTION:
                if user_message == "stop":
                    CheckSolution.create_stop_response("CheckSolution", user_message_obj, None)
                else:
                    CheckSolution.create_substitute_values_response(user_message_obj)
                    if Response.get_context_of_last_response(user_message_obj) == Response.NO_CONTEXT:
                        just_finished_check = (
                            CheckSolution.objects.filter(
                                problem_id=problem_id, end_time__isnull=False, problem_solved=True
                            )
                            .order_by("-end_time")
                            .first()
                        )
                        problem = Problem.objects.get(id=problem_id)
                        if just_finished_check:
                            context["problem_solved"] = "problem-solved"
                            for step_mistakes in Problem.get_all_steps_mistakes(problem).items():
                                if (
                                    step_mistakes[1][0]["title"] != Mistake.NONE
                                    and step_mistakes[1][1]["title"] != Mistake.NONE
                                ):
                                    context["problem_finished"] = "problem-not-finished"
                        else:
                            context["problem_finished"] = "problem-not-finished"

        elif caller == "InitializeNewStep":
            # User must be starting a new check rewrite
            step_id = int(user_message.split("-")[0][4:])
            side = user_message.split("-")[4]
            if current_context == Response.NO_CONTEXT:
                CheckRewrite.create_start_response(step_id, side, user_message_obj)
            else:  # There is already a check rewrite process going
                if CheckRewrite.is_currently_checking(step_id, side):
                    # The user is trying to start the same check rewrite they currently have going
                    Response.save_new(
                        user_message_obj,
                        "You're already checking this rewrite! Respond to the last message to continue.",
                        current_context,
                    )
                else:
                    step = Step.objects.get(id=step_id)
                    currently_active_check = None
                    if current_context in [Response.CHOOSE_REWRITE_VALUES, Response.CHECK_REWRITE]:
                        # The user is trying to start a different check rewrite than the one they currently have going
                        Response.save_new(
                            user_message_obj,
                            "Canceling the current check rewrite process and starting a new one.",
                            Response.NO_CONTEXT,
                        )
                        try:
                            currently_active_check = CheckRewrite.objects.get(
                                problem=step.problem, end_time__isnull=True
                            )
                        except CheckRewrite.DoesNotExist:
                            CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, "error")
                    elif current_context in [Response.CHOOSE_SOLUTION_VALUES, Response.CHECK_SOLUTION]:
                        Response.save_new(
                            user_message_obj,
                            "Canceling the current check solution and starting a check rewrite.",
                            Response.NO_CONTEXT,
                        )
                        try:
                            currently_active_check = CheckSolution.objects.get(
                                problem=step.problem, end_time__isnull=True
                            )
                        except CheckSolution.DoesNotExist:
                            CheckSolution.create_stop_response("CheckSolution", user_message_obj, "error")

                    if currently_active_check:
                        currently_active_check.end_time = timezone.now()
                        currently_active_check.save()
                    CheckRewrite.create_start_response(step_id, side, user_message_obj)
        elif caller in ["StepTypeChanged", "ExpressionChanged", "DeleteStep"]:
            if current_context in [Response.CHOOSE_REWRITE_VALUES, Response.CHECK_REWRITE]:
                CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, caller)
            elif current_context in [Response.CHOOSE_SOLUTION_VALUES, Response.CHECK_SOLUTION]:
                CheckRewrite.create_stop_response("CheckSolution", user_message_obj, caller)
            else:
                if CheckRewrite.objects.filter(problem_id=problem_id, end_time__isnull=True):
                    CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, caller)
                if CheckSolution.objects.filter(problem_id=problem_id, end_time__isnull=True):
                    CheckSolution.create_stop_response("CheckSolution", user_message_obj, caller)
        elif caller == "CheckSolutionClick":
            if current_context != Response.NO_CONTEXT:
                if current_context == Response.CHOOSE_REWRITE_VALUES:
                    # The user is trying to check a rewrite but they are in the middle of checking a solution
                    Response.save_new(
                        user_message_obj,
                        "Canceling the current check rewrite process and starting a solution check.",
                        Response.NO_CONTEXT,
                    )
                    currently_active_check = None
                    try:
                        currently_active_check = CheckRewrite.objects.get(problem_id=problem_id, end_time__isnull=True)
                        currently_active_check.end_time = timezone.now()
                        currently_active_check.save()
                    except CheckRewrite.DoesNotExist:
                        CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, "error")

                    CheckSolution.create_start_response(user_message_obj)
                else:
                    # The user is trying to check a solution but they are in the middle of checking a solution!
                    Response.save_new(
                        user_message_obj,
                        "You're already checking this solution! Respond to the last message to continue.",
                        current_context,
                    )
            else:
                CheckSolution.create_start_response(user_message_obj)
                just_finished_check = (
                    CheckSolution.objects.filter(problem_id=problem_id, end_time__isnull=False, problem_solved=True)
                    .order_by("-end_time")
                    .first()
                )
                problem = Problem.objects.get(id=problem_id)
                if just_finished_check:
                    context["problem_solved"] = "problem-solved"
                    for step_mistakes in Problem.get_all_steps_mistakes(problem).items():
                        if (
                            step_mistakes[1][0]["title"] != Mistake.NONE
                            and step_mistakes[1][1]["title"] != Mistake.NONE
                        ):
                            context["problem_finished"] = "problem-not-finished"
                else:
                    context["problem_finished"] = "problem-not-finished"

        context["responses"] = Response.objects.filter(user_message=user_message_obj).order_by("id")

        return context
