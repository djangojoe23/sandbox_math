from django.utils import timezone
from django.views.generic.base import TemplateView

from sandbox_math.algebra.models import CheckRewrite, Step
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
                    currently_active_check = CheckRewrite.objects.filter(
                        problem=step.problem, end_time__isnull=True
                    ).first()
                    if currently_active_check:
                        currently_active_check.end_time = timezone.now()
                        currently_active_check.save()
                    CheckRewrite.create_start_response(step_id, side, user_message_obj)
        elif caller == "StepTypeChanged":
            # User must be stopping a check rewrite
            pass

        context["responses"] = Response.objects.filter(user_message=user_message_obj).order_by("id")

        # change badge count or color here if a check rewrite process ended successfully

        return context
