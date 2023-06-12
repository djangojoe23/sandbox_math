from django.apps import apps
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


# Create your models here.
class Sandbox(models.Model):
    PREALGEBRA = "Prealgebra"
    ALGEBRA = "Algebra"
    GRAPHS = "Graphs"
    SHAPES = "Shapes"
    SANDBOX_TYPES = [
        (PREALGEBRA, "Pre-algebra"),
        (ALGEBRA, "Algebra"),
        (GRAPHS, "Graphs"),
        (SHAPES, "Shapes"),
    ]

    @classmethod
    def is_problem_solved(cls):
        pass


# This is the base class for the CheckRewrite and CheckSolution models in algebra/models.py
# expr1 is the rewrite or the left side of the equation
# expr2 is the previous step or the right side of the equation
class CheckAlgebra(models.Model):
    problem = models.ForeignKey("algebra.Problem", related_name="%(class)s_problem", on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    expr1 = models.ForeignKey(
        "algebra.Expression", on_delete=models.SET_NULL, related_name="%(class)s_expr1", null=True
    )
    expr1_latex = models.CharField(max_length=100, blank=True, null=True)
    did_expr1_subst = models.BooleanField(default=False)
    expr2 = models.ForeignKey(
        "algebra.Expression", on_delete=models.SET_NULL, related_name="%(class)s_expr2", null=True
    )
    expr2_latex = models.CharField(max_length=100, blank=True, null=True)
    substitution_values = models.JSONField(null=True)
    solving_for = models.CharField(max_length=100, blank=True, null=True)
    end_time = models.DateTimeField(null=True)

    class Meta:
        abstract = True

    # This method saves a new check rewrite or check solution process
    # It needs the problem, a dictionary of variables in the problem along any values they will have while checking
    # the step of the expression being checked (the rewritten expression for checking a rewrite
    # or the left side of the equation for checking a solution
    # It also needs the side of the equation if it is a check rewrite ("left" or "right")
    @classmethod
    def save_new(cls, problem, variable_value_dict, expr1_step, side):
        step_model = apps.get_model("algebra", "Step")
        # Determine if this is a check rewrite or a check solution
        # based on whether step is the first step (check solution) or not (check rewrite)
        if step_model.is_first(expr1_step):
            model_name = "CheckSolution"
        else:
            model_name = "CheckRewrite"
        check_model = apps.get_model("algebra", model_name)
        # There can only be one active check at a time. To be sure, end all checks in the database
        unfinished_checks = check_model.objects.filter(problem=problem, end_time__isnull=True)
        for a in unfinished_checks:
            a.end_time = timezone.now()
            a.save()

        # Save the new check process
        new_check = check_model(problem=problem, solving_for=problem.variable)
        if model_name == "CheckRewrite":
            new_check.expr1 = getattr(expr1_step, f"{side}_expr")
            new_check.expr2 = getattr(step_model.get_prev(expr1_step), f"{side}_expr")
        else:
            equation_step = step_model.objects.filter(problem=problem).order_by("created").first()
            new_check.expr1 = equation_step.left_expr
            new_check.expr2 = equation_step.right_expr

        new_check.expr1_latex = new_check.expr1.latex
        new_check.expr2_latex = new_check.expr2.latex

        new_check.substitution_values = variable_value_dict

        new_check.save()

        return new_check

    # This method returns a querylist of all the same checks the user has already done within a problem
    # This does not also match the values used for variables during the check...just the expressions
    # To find matching solution checks, pass this a solution_check, but leave side and step null
    # To find matching rewrite checks, pass this a step and a side, but leave solution_check null
    @classmethod
    def get_matching_completed_checks(cls, solution_check_process, step, side):
        step_model = apps.get_model("algebra", "Step")
        check_rewrite_model = apps.get_model("algebra", "CheckRewrite")
        if step and side in ["left", "right"]:
            # Getting matching check rewrites
            if step_model.get_prev(step):
                matching_checks = check_rewrite_model.objects.filter(
                    problem=step.problem,
                    expr1_latex=getattr(step, f"{side}_expr").latex,
                    expr2_latex=getattr(step_model.get_prev(step), f"{side}_expr").latex,
                    end_time__isnull=False,
                )
            else:
                matching_checks = check_rewrite_model.objects.none()
        else:
            # Getting matching check solutions
            matching_checks = apps.get_model("algebra", "CheckSolution").objects.filter(
                problem=solution_check_process.problem,
                expr1_latex=solution_check_process.left_latex,
                expr2_latex=solution_check_process.right_latex,
                solving_for=solution_check_process.solving_for,
                answer=solution_check_process.answer,
                end_time__isnull=False,
            )

        return matching_checks

    # This method will return a list of the variables involved in a check process that still need to be given
    # a value by the user
    @classmethod
    def get_unassigned_variables(cls, check_process):
        unassigned_vars = []

        for variable in check_process.substitution_values:
            if not check_process.substitution_values[variable]:
                unassigned_vars.append(variable)

        unassigned_vars.sort()

        return unassigned_vars

    # This method will save the user's suggested substitution value for a variable if it makes sense
    # If the user's suggested value does not make sense, it will create a Response object
    # This method requires the check_process involved, the variable they are trying to assign a value to, and the value
    @classmethod
    def save_substitution_value(cls, check_process, variable, suggested_value_str):
        mistake_model = apps.get_model("users", "Mistake")
        responses = []
        check_model = apps.get_model("algebra", check_process.__class__.__name__)

        if not suggested_value_str.isnumeric():
            mistake_model.save_new(check_process, mistake_model.CHOOSE_VALUE)
            responses.append(f"Just looking for a simple number to put in for `/{variable}`...like `/3`.")
        else:
            try:
                # In case there are any validation errors within this transaction code below, no changes
                # to the models happen
                # The changes to any models will be rolled back and the exception code will run
                with transaction.atomic():
                    max_length = 5
                    if len(suggested_value_str.split(".")) > 1:
                        max_length += 1
                        if len(suggested_value_str.split(".")[1]) > 2:
                            mistake_model.save_new(check_process, mistake_model.CHOOSE_VALUE)
                            responses.append(
                                f"For `/{variable}`, try a simpler number without so many decimal places."
                            )
                    else:
                        max_length = 3

                    if not responses:
                        if len(suggested_value_str) > max_length:
                            mistake_model.save_new(check_process, mistake_model.CHOOSE_VALUE)
                            responses.append(f"Try a smaller and simpler number for `/{variable}`...like `/3`.")
                        else:
                            if check_model.is_checking_new_values(check_process):
                                check_process.substitution_values[variable] = suggested_value_str
                                check_process.save()
                                responses.append(f"Ok, `/{variable}={suggested_value_str}`")
                            else:
                                mistake_model.save_new(check_process, mistake_model.CHOOSE_VALUE)

                                if len(check_process.substitution_values) == 1:
                                    if check_process.__class__.__name__ == "CheckRewrite":
                                        responses.append(
                                            f"You've already checked `/{variable}={suggested_value_str}` in these "
                                            f"expressions."
                                        )
                                        responses.append("Try a different value.")
                                    else:
                                        responses.append(
                                            f"You've already checked `/{variable}={suggested_value_str}` in the "
                                            f"equation."
                                        )
                                        responses.append("Find and fix your mistakes then try again different answer.")
                                else:
                                    # This block of 14 lines of code prepares the substitution values and their
                                    # variables to be printed out in a response
                                    var_val_dict = {}
                                    for temp_var in check_process.substitution_values:
                                        if check_process.substitution_values[temp_var]:
                                            var_val_dict[temp_var] = check_process.substitution_values[temp_var]
                                        elif temp_var == variable:
                                            var_val_dict[temp_var] = suggested_value_str
                                    var_val_list_for_response = []
                                    for temp_var in check_process.substitution_values:
                                        if not check_process.substitution_values[temp_var]:
                                            var_val_list_for_response.append(f"{variable}={suggested_value_str}")
                                        else:
                                            var_val_list_for_response.append(
                                                f"{temp_var}={check_process.sub_values[temp_var]}"
                                            )

                                    if check_process.__class__.__name__ == "CheckRewrite":
                                        responses.append(
                                            "You've already checked these exact values before: `/{}`".format(
                                                ",\\ ".join(var_val_list_for_response)
                                            )
                                        )
                                        responses.append("Try assigning different values to these variables.")
                                    else:
                                        if len(var_val_list_for_response) == 1:
                                            responses.append(
                                                "You've already checked this exact same value with this "
                                                "exact same answer before: "
                                                "`/{}`".format(",\\ ".join(var_val_list_for_response))
                                            )
                                            responses.append("Try assigning a different value instead.")
                                        else:
                                            responses.append(
                                                "You've already checked these exact same values with this "
                                                "exact same answer before: "
                                                "`/{}`".format(",\\ ".join(var_val_list_for_response))
                                            )
                                            responses.append("Try assigning different values to these variables.")
            except ValidationError:
                mistake_model.save_new(check_process, mistake_model.CHOOSE_VALUE)
                responses.append(
                    f"You picked a value for `/{variable}`, but I don't recognize `/{suggested_value_str}` as "
                    f"a number. Please choose a number...like `/4`."
                )

        return responses

    @classmethod
    def create_stop_response(cls, check_process, user_message_obj, reason_for_stop):
        response_model = apps.get_model("calculator", "Response")
        check_process.end_time = timezone.now()
        check_process.save()

        response = "Stopping the check process."

        if reason_for_stop == "delete":
            response += " One of the expressions you were checking was deleted."
        elif reason_for_stop == "step":
            response += " The rewrite you were checking is no longer a rewrite step."
        elif reason_for_stop == "var":
            response += " The variable you are solving for has changed."
        elif reason_for_stop == "expr":
            response += " One of the expressions you are checking was changed."
        elif reason_for_stop == "answ":
            response += " You changed the answer you are checking."

        response_model.save_new(user_message_obj, response, response_model.NO_CONTEXT)
