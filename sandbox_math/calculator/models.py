from django.db import models
from sympy import SympifyError, latex, sympify

from sandbox_math.algebra.models import Expression  # Problem, Step
from sandbox_math.sandbox.models import Sandbox


# Create your models here.
class UserMessage(models.Model):
    sandbox = models.CharField(max_length=10, choices=Sandbox.SANDBOX_TYPES, default=Sandbox.ALGEBRA)
    problem_id = models.PositiveIntegerField(null=False, blank=False)
    timestamp = models.DateTimeField(auto_now_add=True)

    @classmethod
    def save_new(cls, problem_model, problem_id, message_latex):
        new_message = UserMessage(sandbox=problem_model, problem_id=problem_id)
        new_message.save()

        # Messages from users are always assumed to be in latex
        message_content = Content(user_message=new_message, content_type=Content.LATEX, content=message_latex)
        message_content.save()

        return new_message

    @classmethod
    def get_all_previous_for_problem(cls, problem_model, problem_id):
        sorted_prev_user_messages = UserMessage.objects.filter(sandbox=problem_model, problem_id=problem_id).order_by(
            "timestamp"
        )

        return sorted_prev_user_messages


class Response(models.Model):
    CHOOSE_REWRITE_VALUES = "choose-rewrite-values"
    CHOOSE_SOLUTION_VALUES = "choose-solution-values"
    CHECK_REWRITE = "check-rewrite"
    CHECK_SOLUTION = "check-solution"
    NO_CONTEXT = "no-context"
    CONTEXT_TYPES = [
        (CHOOSE_REWRITE_VALUES, "Choosing rewrite values"),
        (
            CHOOSE_SOLUTION_VALUES,
            "Choosing solution values (when solving for one variable in terms of another",
        ),
        (CHECK_REWRITE, "Checking rewrite"),
        (CHECK_SOLUTION, "Checking solution"),
        (NO_CONTEXT, "No context"),
    ]

    user_message = models.ForeignKey(UserMessage, related_name="message", on_delete=models.CASCADE)
    context = models.CharField(max_length=25, choices=CONTEXT_TYPES, default=NO_CONTEXT)
    timestamp = models.DateTimeField(auto_now_add=True)

    @classmethod
    def save_new(cls, user_message, content, context):
        r = Response(user_message=user_message, context=context)
        r.save()

        for content_part in content.split("`"):
            if content_part:
                if content_part[0] == "/":
                    type_of_content = Content.LATEX
                    content_part = content_part[1:]
                else:
                    type_of_content = Content.TEXT
                new_content = Content(
                    response_message=r,
                    content_type=type_of_content,
                    content=content_part,
                )
                new_content.save()

        return r

    @classmethod
    def get_context_of_last_response(cls, problem_id):
        last_response = (
            Response.objects.filter(message__calculator__problem_id=problem_id).order_by("-timestamp").first()
        )

        return last_response.context

    @classmethod
    def create_no_context_response(cls, user_message_obj):
        user_message_latex = Content.objects.get(user_message=user_message_obj).content
        sympy_readable_user_message = Expression.parse_latex(user_message_latex)
        responses = []

        try:
            if user_message_latex == "stop":
                responses.append("There's nothing to stop...")
            else:
                response = sympify(sympy_readable_user_message)
                responses.append(f"`/{latex(response)}`")
        except (SympifyError, TypeError):
            responses.append(f"I don't know how to calculate `/{sympy_readable_user_message}`.")
            responses.append("Try something else.")

        for r in responses:
            Response.save_new(user_message_obj, r, Response.NO_CONTEXT)


class Content(models.Model):
    LATEX = "latex"
    TEXT = "text"
    CONTENT_TYPES = [
        (LATEX, "LaTex"),
        (TEXT, "Text"),
    ]

    response_message = models.ForeignKey(
        Response,
        related_name="response_message",
        on_delete=models.CASCADE,
        default=None,
        null=True,
    )
    user_message = models.ForeignKey(
        UserMessage,
        related_name="user_message",
        on_delete=models.CASCADE,
        default=None,
        null=True,
    )
    content_type = models.CharField(max_length=5, choices=CONTENT_TYPES, default=TEXT)
    content = models.CharField(max_length=250, null=True, blank=True)
