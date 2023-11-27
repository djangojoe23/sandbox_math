from datetime import datetime, timedelta

from allauth.account.signals import user_signed_up
from django.apps import apps
from django.contrib.auth import logout
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import CharField, Count
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from config.settings.base import AUTH_USER_MODEL
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

        new_problems = problem_model.get_recent_by_date(student_id, days_prior)
        activity_context = {}
        activity_score = 0
        activity_max = 12
        if len(new_problems) < days_prior - 2:
            if sum(new_problems.values()) / days_prior >= 1:
                # they started a bunch of problems on one or two days but didn't do any on some days
                activity_score += 1
            activity_context["new_problems_message"] = "Start at least 1 new problem each day."
        else:
            if sum(new_problems.values()) / days_prior >= 1:
                # they started at least 1 problem each day but sometimes started more than 1
                activity_context["new_problems_message"] = "You started at least 1 new problem every day! Keep it up!"
                activity_score += 3
            else:
                # they started exactly 1 problem each day
                activity_context[
                    "new_problems_message"
                ] = f"You started at least {days_prior-2} new problems in the past {days_prior} days. Don't let up!"
                activity_score += 2

        new_steps = step_model.get_recent_by_date(student_id, days_prior)
        days_with_enough_new_steps = len([s for s in new_steps.values() if s >= 3])
        if days_with_enough_new_steps < days_prior - 2:
            if sum(new_steps.values()) / days_prior >= 3:
                activity_score += 1
            activity_context["new_steps_message"] = "Add at least 3 new algebra steps each day."
        else:
            if sum(new_steps.values()) / days_prior >= 3:
                activity_context["new_steps_message"] = "You added at least 3 new algebra steps every day! Keep it up!"
                activity_score += 3
            else:
                activity_context["new_steps_message"] = (
                    f"You added at least {(days_prior-2)*3} new algebra steps in the past {days_prior} days. "
                    f"Don't let up!"
                )
                activity_score += 2

        new_checkrewrites = checkrewrite_model.get_recent_by_date("CheckRewrite", student_id, days_prior)
        if len(new_checkrewrites) < days_prior - 2:
            if sum(new_checkrewrites.values()) / days_prior >= 1:
                activity_score += 1
            activity_context["new_checkrewrites_message"] = "Check at least 1 rewrite step each day."
        else:
            if sum(new_checkrewrites.values()) / days_prior >= 1:
                activity_context[
                    "new_checkrewrites_message"
                ] = "You checked at least 1 rewrite step each day! Keep it up!"
                activity_score += 3
            else:
                activity_context[
                    "new_checkrewrites_message"
                ] = f"You checked at least {days_prior-2} rewrite steps in the past {days_prior} days. Don't let up!"
                activity_score += 2

        new_checksolutions = checksolution_model.get_recent_by_date("CheckSolution", student_id, days_prior)
        if len(new_checksolutions) < days_prior - 2:
            if sum(new_checksolutions.values()) / days_prior >= 1:
                # they checked a bunch of solutions on one or two days but didn't do any on some days
                activity_score += 1
            activity_context["new_checksolutions_message"] = "Check at least 1 solution each day."
        else:
            if sum(new_checksolutions.values()) / days_prior >= 1:
                activity_context[
                    "new_checksolutions_message"
                ] = "You checked at least 1 solution each day! Keep it up!"
                activity_score += 3
            else:
                activity_context[
                    "new_checksolutions_message"
                ] = f"You checked at least {days_prior-2} solutions in the past {days_prior} days. Don't let up!"
                activity_score += 2

        activity_context["activity_score"] = activity_score / activity_max

        return activity_context

    @classmethod
    def get_mistakes_overview(cls, student_id, days_prior):
        check_rewrite_model = apps.get_model("algebra", "CheckRewrite")
        check_solution_model = apps.get_model("algebra", "CheckSolution")
        step_model = apps.get_model("algebra", "Step")

        start_date = timezone.make_aware(
            datetime.now() - timedelta(days=days_prior), timezone.get_current_timezone(), True
        )

        mistakes_context = {}
        # determine how many mistakes were made by this user last week and the most common
        all_recent_mistakes = Mistake.objects.filter(owner_id=student_id, mistake_time__gte=start_date).exclude(
            mistake_event_type=Mistake.HELP_CLICK, mistake_type=Mistake.NONE
        )
        mistakes_context["recent_made_count"] = all_recent_mistakes.count()
        mistakes_context["per_action"] = None
        mistakes_context["recent_most_common"] = None
        mistakes_context["find_rate"] = None
        mistakes_context["fixed_rate"] = None
        if mistakes_context["recent_made_count"]:
            mistakes_context["recent_most_common"] = (
                all_recent_mistakes.values("mistake_type")
                .annotate(type_count=Count("mistake_type"))
                .order_by("-type_count")
                .first()["mistake_type"]
            )

            # Determine rate of mistakes per action for all time, then find recent rate of mistakes per action
            all_check_rewrites = check_rewrite_model.objects.filter(
                problem__student__id=student_id, did_expr1_subst=True, are_equivalent__isnull=False
            )
            all_check_solutions = check_solution_model.objects.filter(
                problem__student__id=student_id, did_expr1_subst=True
            ).exclude(problem_solved=check_solution_model.INCOMPLETE)
            all_steps = step_model.objects.filter(problem__student__id=student_id)
            all_mistakes = Mistake.objects.filter(owner_id=student_id).exclude(
                mistake_event_type=Mistake.HELP_CLICK, mistake_type=Mistake.NONE
            )
            actions_count = all_check_rewrites.count() + all_check_solutions.count() + all_steps.count()
            mistakes_count = all_mistakes.count()
            mistakes_per_action = None
            if actions_count > 0:
                mistakes_per_action = mistakes_count / actions_count

            recent_actions_count = (
                all_check_rewrites.filter(start_time__gte=start_date, end_time__gte=start_date).count()
                + all_check_solutions.filter(start_time__gte=start_date, end_time__gte=start_date).count()
                + all_steps.filter(created__gte=start_date).count()
            )
            recent_mistakes_per_action = None
            if recent_actions_count > 0:
                recent_mistakes_per_action = (
                    all_mistakes.filter(mistake_time__gte=start_date).count() / recent_actions_count
                )

            # Determine rate of mistakes found per mistake all time, then find recent rate of mistakes found/mistake
            help_clicks = Mistake.objects.filter(owner_id=student_id, mistake_event_type=Mistake.HELP_CLICK)
            help_click_count = help_clicks.count()
            help_click_mistake_found_count = help_clicks.exclude(mistake_type=Mistake.NONE).count()
            recent_help_clicks = help_clicks.filter(mistake_time__gte=start_date)
            recent_help_click_count = recent_help_clicks.count()
            recent_help_click_mistake_found_count = recent_help_clicks.exclude(mistake_type=Mistake.NONE).count()

            check_rewrites = check_rewrite_model.objects.filter(
                problem__student_id=student_id, are_equivalent__isnull=False
            )
            check_rewrites_count = check_rewrites.count()
            check_rewrites_mistake_found = check_rewrites.filter(are_equivalent=False).count()
            recent_check_rewrites = check_rewrites.filter(end_time__gte=start_date)
            recent_check_rewrites_count = recent_check_rewrites.count()
            recent_check_rewrites_mistake_found = recent_check_rewrites.filter(are_equivalent=False).count()

            check_solutions = check_solution_model.objects.filter(problem__student_id=student_id).exclude(
                problem_solved=check_solution_model.INCOMPLETE
            )
            check_solutions_count = check_solutions.count()
            check_solutions_mistake_found = check_solutions.filter(
                problem_solved=check_solution_model.NOT_SOLVED
            ).count()
            recent_check_solutions = check_solutions.filter(end_time__gte=start_date)
            recent_check_solutions_count = recent_check_solutions.count()
            recent_check_solutions_mistake_found = recent_check_solutions.filter(
                problem_solved=check_solution_model.NOT_SOLVED
            ).count()

            find_rate = None
            if help_click_count + check_rewrites_count + check_solutions_count > 0:
                find_rate = (
                    check_solutions_mistake_found + check_rewrites_mistake_found + help_click_mistake_found_count
                ) / (help_click_count + check_rewrites_count + check_solutions_count)
            recent_find_rate = None
            if recent_help_click_count + recent_check_rewrites_count + recent_check_solutions_count > 0:
                recent_find_rate = (
                    recent_check_solutions_mistake_found
                    + recent_check_rewrites_mistake_found
                    + recent_help_click_mistake_found_count
                ) / (recent_help_click_count + recent_check_rewrites_count + recent_check_solutions_count)

            # Determine rate of mistake fixed per mistake all time, then find recent rate of mistake fixed per mistake
            fixed_rate = None
            if mistakes_count > 0:
                fixed_rate = all_mistakes.filter(is_fixed=True).count() / mistakes_count
            recent_fixed_rate = None
            recent_fixed_rate = (
                all_recent_mistakes.filter(is_fixed=True).count() / mistakes_context["recent_made_count"]
            )

            # Compare
            if mistakes_per_action is not None and recent_mistakes_per_action is not None:
                if mistakes_per_action > recent_mistakes_per_action:
                    mistakes_context["per_action"] = "worse"
                elif mistakes_per_action == recent_mistakes_per_action:
                    mistakes_context["per_action"] = "same"
                else:
                    mistakes_context["per_action"] = "better"

            # found_rate vs. recent_found_rate
            if find_rate is not None and recent_find_rate is not None:
                if find_rate > recent_find_rate:
                    mistakes_context["find_rate"] = "better"
                elif find_rate == recent_find_rate:
                    mistakes_context["find_rate"] = "same"
                else:
                    mistakes_context["find_rate"] = "worse"

            if fixed_rate is not None and recent_fixed_rate is not None:
                if fixed_rate > recent_fixed_rate:
                    mistakes_context["fixed_rate"] = "better"
                elif fixed_rate == recent_fixed_rate:
                    mistakes_context["fixed_rate"] = "same"
                else:
                    mistakes_context["fixed_rate"] = "worse"

        return mistakes_context

    @classmethod
    def get_solved_overview(cls, student_id, days_prior):
        problem_model = apps.get_model("algebra", "Problem")
        step_model = apps.get_model("algebra", "Step")
        checksolution_model = apps.get_model("algebra", "CheckSolution")

        start_date = timezone.make_aware(
            datetime.now() - timedelta(days=days_prior), timezone.get_current_timezone(), True
        )

        solved_context = {}
        all_problems_started = problem_model.objects.filter(student_id=student_id)
        solved_context["problems_started"] = all_problems_started.count()
        solved_context["solved_rate_status"] = "same"
        solved_context["problems_solved"] = 0
        solved_context["recently_started"] = 0
        solved_context["recently_solved"] = 0
        if solved_context["problems_started"]:
            all_problems_with_recent_steps = (
                all_problems_started.filter(step__created__gte=start_date).values("id").distinct()
            )

            all_problems_recently_started = []
            for p in all_problems_with_recent_steps:
                first_step = step_model.objects.filter(problem_id=p["id"]).order_by("created").first()
                if first_step.created >= start_date:
                    all_problems_recently_started.append(first_step.problem)

            all_problems_solved_count = (
                checksolution_model.objects.filter(problem__in=all_problems_started)
                .exclude(problem_solved__in=[checksolution_model.NOT_SOLVED, checksolution_model.INCOMPLETE])
                .count()
            )
            solved_rate = all_problems_solved_count / all_problems_started.count()

            all_problems_recently_solved_count = (
                checksolution_model.objects.filter(problem__in=all_problems_recently_started)
                .exclude(problem_solved__in=[checksolution_model.NOT_SOLVED, checksolution_model.INCOMPLETE])
                .count()
            )
            recently_solved_rate = all_problems_recently_solved_count / len(all_problems_recently_started)

            # If recently solved rate is higher than all time solved rate then message is good
            if recently_solved_rate > solved_rate:
                solved_context["solved_rate_status"] = "better"
            elif recently_solved_rate < solved_rate:
                solved_context["solved_rate_status"] = "worse"
            else:
                solved_context["solved_rate_status"] = "same"

            solved_context["problems_solved"] = all_problems_solved_count
            solved_context["recently_started"] = len(all_problems_recently_started)
            solved_context["recently_solved"] = all_problems_recently_solved_count

        return solved_context


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
    TOO_LONG = "Expression Too Long"
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
            "Make sure the equation you defined in the first step is linear.",
        ),
        (
            NO_VAR,
            "Provide a variable to solve in the equation in the first step.",
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
            "Copy the expression from the previous step and then do arithmetic to it.",
        ),
        (
            MISSING_PARENS,
            "Use parentheses to do arithmetic to the entire expression.",
        ),
        (NON_MATH, "This isn't an expression that makes sense in this context."),
        (
            GREY_BOX,
            "Remove the grey box from the expression or enter something in it.",
        ),
        (ALREADY_DEFINED, "The equation was already defined in the first step."),
        (
            UNKNOWN_SYM,
            "Remove the symbol in this expression that has no meaning in this context.",
        ),
        (
            CANNOT_REWRITE,
            "Fix the expression in the previous step so it makes sense then try to rewrite it.",
        ),
        (TOO_LONG, "This expression has too many characters in it and cannot be saved. Shorten it!"),
        (NONE, "This expression is correct at this step."),
        (ALREADY_INCORRECT, "Trying to check rewrite or answer already proven to be wrong."),
        (INVALID_EXPR, "Trying to check expression that is not valid."),
        (CHOOSE_VALUE, "Mistake made while choosing a value to substitute in for a variable."),
        (SUB_EXPR1, "Mistake made while substituting a value in for a variable."),
        (SUB_EXPR2, "Mistake made while substituting a value in for a variable."),
    ]

    owner = models.ForeignKey(AUTH_USER_MODEL, related_name="owner", on_delete=models.CASCADE)
    mistake_type = models.CharField(max_length=30, choices=MISTAKE_TYPES, default=None)
    mistake_event_type = models.CharField(max_length=14, choices=MISTAKE_EVENT_TYPES, default=None)
    event_id = models.PositiveIntegerField()
    mistake_time = models.DateTimeField(auto_now_add=True)
    is_fixed = models.BooleanField(default=False)

    @classmethod
    def save_new(cls, problem_id, mistake_event_instance, mistake_type):
        problem_model = apps.get_model("algebra", "Problem")

        problem_obj = problem_model.objects.get(id=problem_id)

        new_mistake = Mistake.objects.none()
        for mistake_event_type in Mistake.MISTAKE_EVENT_TYPES:
            if mistake_event_type[0] == mistake_event_instance.__class__.__name__:
                new_mistake = Mistake(
                    owner=problem_obj.student,
                    mistake_type=mistake_type,
                    mistake_event_type=mistake_event_type[0],
                    event_id=mistake_event_instance.id,
                )
                new_mistake.save()

        return new_mistake

    @classmethod
    def get_mistake_message(cls, mistake_type):
        for m in Mistake.MISTAKE_TYPES:
            if m[0] == mistake_type:
                return m[1]
        return None

    @classmethod
    def get_recent_by_date(cls, student_id, day_range):
        # mistake status in ['Mistakes Made', 'Mistakes Found', 'Mistakes Fixed']
        start_date = timezone.make_aware(
            datetime.now() - timedelta(days=day_range), timezone.get_current_timezone(), True
        )

        all_mistakes = (
            Mistake.objects.filter(owner_id=student_id, mistake_time__gte=start_date)
            .exclude(mistake_event_type=Mistake.HELP_CLICK, mistake_type=Mistake.NONE)
            .order_by("mistake_time")
        )

        mistakes_per_date = {}
        mistake_dict = {"Mistakes Made": 0, "Mistakes Found": 0, "Mistakes Fixed": 0}
        for m in all_mistakes:
            date_string = m.mistake_time.strftime('"%b %-d, %Y"')
            if date_string in mistakes_per_date:
                mistakes_per_date[date_string]["Mistakes Made"] += 1
            else:
                mistakes_per_date[date_string] = mistake_dict.copy()
                mistakes_per_date[date_string]["Mistakes Made"] = 1

        # need to get mistakes found
        all_help_clicks = (
            Mistake.objects.filter(owner_id=student_id, mistake_event_type=Mistake.HELP_CLICK)
            .exclude(mistake_type=Mistake.NONE)
            .order_by("mistake_time")
        )
        for m in all_help_clicks:
            date_string = m.mistake_time.strftime('"%b %-d, %Y"')
            if date_string in mistakes_per_date:
                mistakes_per_date[date_string]["Mistakes Found"] += 1
            else:
                mistakes_per_date[date_string] = mistake_dict.copy()
                mistakes_per_date[date_string]["Mistakes Found"] = 1

        check_rewrite_model = apps.get_model("algebra", "CheckRewrite")
        all_check_rewrites = check_rewrite_model.objects.filter(
            problem__student_id=student_id, are_equivalent=False
        ).order_by("end_time")
        for m in all_check_rewrites:
            date_string = m.end_time.strftime('"%b %-d, %Y"')
            if date_string in mistakes_per_date:
                mistakes_per_date[date_string]["Mistakes Found"] += 1
            else:
                mistakes_per_date[date_string] = mistake_dict.copy()
                mistakes_per_date[date_string]["Mistakes Found"] = 1

        check_solution_model = apps.get_model("algebra", "CheckSolution")
        all_check_solutions = check_solution_model.objects.filter(
            problem__student_id=student_id, problem_solved=check_solution_model.NOT_SOLVED
        ).order_by("end_time")
        for m in all_check_solutions:
            date_string = m.end_time.strftime('"%b %-d, %Y"')
            if date_string in mistakes_per_date:
                mistakes_per_date[date_string]["Mistakes Found"] += 1
            else:
                mistakes_per_date[date_string] = mistake_dict.copy()
                mistakes_per_date[date_string]["Mistakes Found"] = 1

        all_mistakes_fixed = all_mistakes.filter(is_fixed=True).order_by("mistake_time")
        for m in all_mistakes_fixed:
            date_string = m.mistake_time.strftime('"%b %-d, %Y"')
            if date_string in mistakes_per_date:
                mistakes_per_date[date_string]["Mistakes Fixed"] += 1
            else:
                mistakes_per_date[date_string] = mistake_dict.copy()
                mistakes_per_date[date_string]["Mistakes Fixed"] = 1

        return mistakes_per_date
