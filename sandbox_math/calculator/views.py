from django.utils import timezone
from django.views.generic.base import TemplateView

from sandbox_math.algebra.models import CheckRewrite, CheckSolution, Step
from sandbox_math.calculator.models import Response, UserMessage
from sandbox_math.sandbox.models import Sandbox


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
        print(current_context)
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
                    # The user is trying to start a different check rewrite than the one they currently have going
                    Response.save_new(
                        user_message_obj,
                        "Canceling the current check rewrite process and starting a new one.",
                        Response.NO_CONTEXT,
                    )
                    step = Step.objects.get(id=step_id)
                    currently_active_check = None
                    try:
                        currently_active_check = CheckRewrite.objects.get(problem=step.problem, end_time__isnull=True)
                    except CheckRewrite.DoesNotExist:
                        CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, "error")

                    if currently_active_check:
                        currently_active_check.end_time = timezone.now()
                        currently_active_check.save()
                    CheckRewrite.create_start_response(step_id, side, user_message_obj)
        elif caller in ["StepTypeChanged", "ExpressionChanged", "DeleteStep"]:
            CheckRewrite.create_stop_response("CheckRewrite", user_message_obj, caller)
        elif caller == "CheckSolutionClick":
            # The user is trying to check a solution but they are in the middle of checking a rewrite
            if current_context != Response.NO_CONTEXT:
                print("here!")
            # The user is trying to check a solution but they are in the middle of checking the same solution
            # The user is trying to check a solution but they are in the middle of checking a different solution
            # The user is trying to check a solution
            else:
                CheckSolution.create_start_response(user_message_obj)

        context["responses"] = Response.objects.filter(user_message=user_message_obj).order_by("id")

        return context
