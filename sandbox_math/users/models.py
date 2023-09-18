from allauth.account.signals import user_signed_up
from django.apps import apps
from django.contrib.auth import logout
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField
from django.dispatch import receiver
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from sandbox_math.sandbox.models import Sandbox


@receiver(user_signed_up)
def user_signed_up(request, user, **kwargs):
    logout(request)


class User(AbstractUser):
    """
    Default custom user model for Sandbox Math.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore
    last_name = None  # type: ignore

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @classmethod
    def get_activity_overview(cls, student_id, days_prior):
        problem_model = apps.get_model("algebra", "Problem")
        step_model = apps.get_model("algebra", "Step")
        checkrewrite_model = apps.get_model("algebra", "CheckRewrite")
        checksolution_model = apps.get_model("algebra", "CheckSolution")

        new_problems = problem_model.get_recent_new_by_date(student_id, days_prior)
        activity_context = {}
        activity_score = 0
        activity_max = 12
        if len(new_problems) < days_prior - 2:
            if sum(new_problems.values()) / 7 >= 1:
                activity_context[
                    "new_problems_message"
                ] = "Consistency is more important than intensity. Try to start at least 1 new problem each day."
                activity_score += 1
            else:
                activity_context[
                    "new_problems_message"
                ] = "Consistency is key! Try to start at least 1 new problem each day."
        else:
            if sum(new_problems.values()) / 7 >= 1:
                activity_context[
                    "new_problems_message"
                ] = "You started at least 1 new problem every day! Keep up the strong consistency!"
                activity_score += 3
            else:
                activity_context[
                    "new_problems_message"
                ] = "You started at least 5 new problems last week. Don't let up!"
                activity_score += 2

        new_steps = step_model.get_recent_new_by_date(student_id, days_prior)
        days_with_enough_new_steps = len([s for s in new_steps.values() if s >= 3])
        if days_with_enough_new_steps < days_prior - 2:
            if sum(new_steps.values()) / 7 >= 3:
                activity_context[
                    "new_steps_message"
                ] = "Consistency is more important than intensity. Try to add at least 3 new algebra steps each day."
                activity_score += 1
            else:
                activity_context[
                    "new_steps_message"
                ] = "Consistency is key! Try to add at least 3 new algebra steps each day."
        else:
            if sum(new_steps.values()) / 7 >= 3:
                activity_context[
                    "new_steps_message"
                ] = "You added at least 3 new algebra steps every day! Keep up the strong consistency!"
                activity_score += 3
            else:
                activity_context[
                    "new_steps_message"
                ] = "You added at least 15 new algebra steps last week. Don't let up!"
                activity_score += 2

        new_checkrewrites = checkrewrite_model.get_recent_by_date("CheckRewrite", student_id, days_prior)
        if len(new_checkrewrites) < days_prior - 2:
            if sum(new_checkrewrites.values()) / 7 >= 1:
                activity_context[
                    "new_checkrewrites_message"
                ] = "Consistency is more important than intensity. Try to check at least 1 rewrite step each day."
                activity_score += 1
            else:
                activity_context[
                    "new_checkrewrites_message"
                ] = "Consistency is key! Try to check at least 1 rewrite step each day."
        else:
            if sum(new_checkrewrites.values()) / 7 >= 1:
                activity_context[
                    "new_checkrewrites_message"
                ] = "You checked at least 1 rewrite step each day! Keep up the strong consistency!"
                activity_score += 3
            else:
                activity_context[
                    "new_checkrewrites_message"
                ] = "You checked at least 5 rewrite steps last week. Don't let up!"
                activity_score += 2

        new_checksolutions = checksolution_model.get_recent_by_date("CheckSolution", student_id, days_prior)
        if len(new_checksolutions) < days_prior - 2:
            if sum(new_checksolutions.values()) / 7 >= 1:
                activity_context[
                    "new_checksolutions_message"
                ] = "Consistency is more important than intensity. Try to check at least 1 solution each day."
                activity_score += 1
            else:
                activity_context[
                    "new_checksolutions_message"
                ] = "Consistency is key! Try to check at least 1 solution each day."
        else:
            if sum(new_checksolutions.values()) / 7 >= 1:
                activity_context[
                    "new_checksolutions_message"
                ] = "You checked at least 1 solution each day! Keep up the strong consistency!"
                activity_score += 3
            else:
                activity_context[
                    "new_checksolutions_message"
                ] = "You checked at least 5 solutions last week. Don't let up!"
                activity_score += 2

        activity_context["activity_score"] = activity_score / activity_max

        return activity_context


class HelpClick(models.Model):
    EXPRESSION = "expression"
    OBJECT_TYPES = [
        (EXPRESSION, "User clicked on an expression to see if it had any mistakes"),
    ]

    sandbox = models.CharField(max_length=10, choices=Sandbox.SANDBOX_TYPES, default=None)
    object_id = models.PositiveIntegerField()
    object_type = models.CharField(max_length=10, choices=OBJECT_TYPES, default=None)
    click_time = models.DateTimeField(auto_now_add=True)


class Proceed(models.Model):
    ADD_STEP = "add step"
    CHECK_SOLUTION = "check solution"
    PROCEED_TYPES = [
        (ADD_STEP, "User attempted to add new step to the problem"),
    ]

    sandbox = models.CharField(max_length=10, choices=Sandbox.SANDBOX_TYPES, default=None)
    problem_id = models.PositiveIntegerField()
    proceed_type = models.CharField(max_length=15, choices=PROCEED_TYPES, default=None)
    proceed_time = models.DateTimeField(auto_now_add=True)


class Mistake(models.Model):
    # Event Types
    HELP_CLICK = "HelpClick"
    PROCEED = "Proceed"
    CHECK_REWRITE = "CheckRewrite"
    CHECK_SOLUTION = "CheckSolution"

    # HELP_CLICK mistakes can be fixed when Step.get_mistakes is called
    # PROCEED -> ADD_STEP mistakes can be fixed when Problem.get_all_steps_mistakes is called
    # CHECK_SOLUTION mistakes can be fixed when a problem is solved
    # CHECK_REWRITE mistakes can be fixed after expression 1 or expression 2 is correctly substituted for
    MISTAKE_EVENT_TYPES = [
        (HELP_CLICK, "User clicked on help that showed a mistake"),
        (PROCEED, "User went to the next step when there was a mistake in a previous step"),
        (CHECK_REWRITE, "User made a mistake during the check rewrite process"),
        (CHECK_SOLUTION, "User made a mistake during the check solution process"),
    ]

    # Algebra mistakes types
    NO_EQUATION = "Define the Equation"
    NONLINEAR = "Linear Equations Only"
    NO_VAR = "Need a Variable"
    NO_VAR_SELECTED = "Select a Variable"
    NO_STEP_TYPE = "Select a Step Type"
    VAR_NOT_IN_EQUATION = "Select a Variable in Equation"
    BLANK_EXPR = "No Blank Expressions"
    REWRITE = "Incorrect Rewrite"
    UNEQUAL_ARITHMETIC = "Unequal Arithmetic"
    NO_ARITHMETIC = "Do Arithmetic"
    MISSING_PREV_EXPR = "Copy Previous Step"
    MISSING_PARENS = "Use Parentheses"
    NON_MATH = "Non-Algebraic Expression"
    GREY_BOX = "Missing Something"
    UNKNOWN_SYM = "Unknown Symbol"
    ALREADY_DEFINED = "Change Step Type"
    CANNOT_REWRITE = "Check Previous Expression"
    NONE = "No Mistake Here"

    # Check rewrite and check solution mistakes
    ALREADY_INCORRECT = "Already checked - incorrect"
    INVALID_EXPR = "Expression needs fixed"
    CHOOSE_VALUE = "Choosing a value"
    SUB_EXPR1 = "Substitution expression 1"
    SUB_EXPR2 = "Substitution expression 2"

    # These are the content of the help popovers
    MISTAKE_TYPES = [
        (NO_EQUATION, "Use the dropdown in the first step to define an equation."),
        (
            NONLINEAR,
            "Please make sure the equation you defined in the first step is linear.",
        ),
        (
            NO_VAR,
            "Please provide a variable to solve in the equation in the first step.",
        ),
        (
            NO_VAR_SELECTED,
            "Use the dropdown menu to select which variable to solve for.",
        ),
        (
            NO_STEP_TYPE,
            "Use the dropdown above this step to select which step type you want here.",
        ),
        (
            VAR_NOT_IN_EQUATION,
            "Use the dropdown menu to select a variable to solve for that is in your equation.",
        ),
        (BLANK_EXPR, "You need to type something in to each input box for each step."),
        (REWRITE, "This expression is not equivalent to the previous step."),
        (
            UNEQUAL_ARITHMETIC,
            "The arithmetic is not the same on both sides of the equation.",
        ),
        (NO_ARITHMETIC, "Do some arithmetic to this expression."),
        (
            MISSING_PREV_EXPR,
            "Please copy the previous step's expression and then do arithmetic to it.",
        ),
        (
            MISSING_PARENS,
            "Please use parentheses to do arithmetic to the entire expression.",
        ),
        (NON_MATH, "This isn't an expression that makes sense in this context."),
        (
            GREY_BOX,
            "Please remove the grey box from the expression or enter something in it.",
        ),
        (ALREADY_DEFINED, "The equation was already defined in the first step."),
        (
            UNKNOWN_SYM,
            "Please remove the symbol in this expression that has no meaning in this context.",
        ),
        (
            CANNOT_REWRITE,
            "Fix the expression in the previous step so it makes sense, then try to rewrite it.",
        ),
        (NONE, "This expression is correct at this step."),
        (ALREADY_INCORRECT, "Trying to check rewrite or answer already proven to be wrong."),
        (INVALID_EXPR, "Trying to check expression that isn't valid."),
        (CHOOSE_VALUE, "Mistake made while choosing a value to substitute in for a variable."),
        (SUB_EXPR1, "Mistake made while substituting into the first expression"),
        (SUB_EXPR2, "Mistake made while substituting into the second expression"),
    ]

    mistake_type = models.CharField(max_length=30, choices=MISTAKE_TYPES, default=None)
    mistake_event_type = models.CharField(max_length=14, choices=MISTAKE_EVENT_TYPES, default=None)
    event_id = models.PositiveIntegerField()
    mistake_time = models.DateTimeField(auto_now_add=True)
    is_fixed = models.BooleanField(default=False)

    @classmethod
    def save_new(cls, mistake_event_instance, mistake_type):
        new_mistake = Mistake.objects.none()
        for mistake_event_type in Mistake.MISTAKE_EVENT_TYPES:
            if mistake_event_type[0] == mistake_event_instance.__class__.__name__:
                new_mistake = Mistake(
                    mistake_type=mistake_type,
                    mistake_event_type=mistake_event_type[0],
                    event_id=mistake_event_instance.id,
                )
                new_mistake.save()

        return new_mistake
