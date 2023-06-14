from django.apps import apps
from django.db import models
from sympy import latex, simplify

from sandbox_math.sandbox.models import Sandbox
from sandbox_math.users.models import Mistake


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
        content_type = Content.LATEX
        hidden_messages = ["start-check-rewrite", "stop-check-rewrite", "start-check-solution", "stop-check-solution"]
        if any(msg in message_latex for msg in hidden_messages):
            content_type = Content.HIDDEN
        message_content = Content(user_message=new_message, content_type=content_type, content=message_latex)
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
    def get_context_of_last_response(cls, new_user_message_obj):
        last_response = Response.objects.filter(
            user_message__sandbox=new_user_message_obj.sandbox,
            user_message__problem_id=new_user_message_obj.problem_id,
        ).order_by("-timestamp")
        if not last_response:
            return Response.NO_CONTEXT
        else:
            return last_response.first().context

    @classmethod
    def with_no_context(cls, user_message_obj):
        expression_model = apps.get_model("algebra", "Expression")
        is_numeric = True
        responses = []
        user_message_latex = Content.objects.get(user_message=user_message_obj).content
        if expression_model.get_variables_in_latex_expression(user_message_latex):
            is_numeric = False
        else:
            sympy_user_message = expression_model.get_sympy_expression_from_latex(user_message_latex)
            if sympy_user_message not in list(zip(*Mistake.MISTAKE_TYPES))[0]:
                response = simplify(sympy_user_message)
                responses.append(f"`/{latex(response)}`")
            else:
                is_numeric = False

        if not is_numeric:
            if user_message_latex == "stop":
                responses.append("There's nothing to stop...")
            else:
                responses.append(f"I don't know how to calculate `/{user_message_latex}`.")
            responses.append("Try something else.")

        for r in responses:
            Response.save_new(user_message_obj, r, Response.NO_CONTEXT)


class Content(models.Model):
    LATEX = "latex"
    TEXT = "text"
    HIDDEN = "hidden"
    CONTENT_TYPES = [(LATEX, "LaTex"), (TEXT, "Text"), (HIDDEN, "Hidden")]

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
    content_type = models.CharField(max_length=6, choices=CONTENT_TYPES, default=TEXT)
    content = models.CharField(max_length=250, null=True, blank=True)
