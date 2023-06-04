# from decimal import Decimal
from django.db import models

# from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, OuterRef, Q, Subquery
from django.utils import timezone
from sympy import simplify  # , UnevaluatedExpr, latex
from sympy.core import symbol
from sympy.parsing.sympy_parser import implicit_multiplication_application, parse_expr, standard_transformations

from config.settings.base import AUTH_USER_MODEL
from sandbox_math.users.models import Mistake, User


# Create your models here.
class Problem(models.Model):
    student = models.ForeignKey(AUTH_USER_MODEL, related_name="student", on_delete=models.CASCADE)
    variable = models.CharField(max_length=100, blank=True, null=True)
    last_viewed = models.DateTimeField()

    @classmethod
    def save_new(cls, student_id):
        student = User.objects.get(id=student_id)
        problem = Problem(student=student)
        problem.last_viewed = timezone.now()
        problem.save()

        return problem

    @classmethod
    def update_variable(cls, problem, selected_variable):
        if selected_variable and selected_variable.isalpha():
            problem.variable = selected_variable
            problem.save()
        else:
            problem.variable = None
            problem.save()

    """
    This method is called by the RecentProblemsListView in algebra/views
    It returns a queryset with columns:
    link, start date, last viewed, equation, step count, solved/unsolved status
    """

    @classmethod
    def populate_recent_table(cls, student_id, table_filter):
        step_qs = Step.objects.filter(problem=OuterRef("pk")).order_by("created")

        and_filter = Q()
        """
        TODO:
        if table_filter["status"]:
            if table_filter["status"] == "solved":
                and_filter.add(Q(solved__isnull=False), Q.AND)
            elif table_filter["status"] == "unsolved":
                and_filter.add(Q(solved__isnull=True), Q.AND)
            else:
                pass
        """
        order_by = "-created"
        if table_filter["order_by"]:
            if table_filter["order_by"].startswith("step"):
                if table_filter["order_by"].endswith("down"):
                    order_by = "-step_count"
                else:
                    order_by = "step_count"
            elif table_filter["order_by"].startswith("last"):
                if table_filter["order_by"].endswith("down"):
                    order_by = "-last_viewed"
                else:
                    order_by = "last_viewed"
            elif table_filter["order_by"].startswith("start"):
                if table_filter["order_by"].endswith("down"):
                    order_by = "-created"
                else:
                    order_by = "created"

        equation_filter = Q()
        if table_filter["equation"]:
            if "undefined".startswith(table_filter["equation"].lower()):
                equation_filter.add(Q(left__isnull=True), Q.AND)
                equation_filter.add(Q(right__isnull=True), Q.AND)
            else:
                equation_filter.add(Q(left__contains=table_filter["equation"]), Q.OR)
                equation_filter.add(Q(right__contains=table_filter["equation"]), Q.OR)

        recent = (
            Problem.objects.filter(student=student_id)
            .filter(and_filter)
            .annotate(step_count=Count("step_problem"))
            .annotate(created=Subquery(step_qs.values("created")[:1]))
            .annotate(left=Subquery(step_qs.values("expr1__latex")[:1]))
            .annotate(right=Subquery(step_qs.values("expr2__latex")[:1]))
            .filter(equation_filter)
            .order_by(order_by)
        )
        return recent

    """
    This method returns a two item list where the first item is the left side's mistakes and the second item is the
    right side's mistakes
    """

    @classmethod
    def get_define_equation_mistakes(cls, this_step):
        mistakes = [Mistake.NONE, Mistake.NONE]
        has_variables = [False, False]

        for s in range(0, 2):
            this_latex = this_step.left_expr.latex
            if s == 1:
                this_latex = this_step.right_expr.latex
            if this_latex:
                sympy_expr = Expression.get_sympy_expression_from_latex(this_latex)

                if sympy_expr not in Mistake.MISTAKE_TYPES:
                    if Expression.get_variables_in_latex_expression(this_latex):
                        has_variables[s] = True
                else:
                    mistakes[s] = sympy_expr
            else:
                mistakes[s] = Mistake.BLANK_EXPR

        if mistakes[0] == mistakes[1] == Mistake.NONE:
            if not has_variables[0] and not has_variables[1]:
                mistakes[0] = Mistake.NO_VAR
                mistakes[1] = Mistake.NO_VAR
            elif has_variables[0] or has_variables[1]:
                if this_step.problem.variable:
                    if this_step.problem.variable not in Expression.get_variables_in_latex_expression(
                        this_step.expr1.latex
                    ) and this_step.problem.variable not in Expression.get_variables_in_latex_expression(
                        this_step.expr2.latex
                    ):
                        mistakes[0] = Mistake.VAR_NOT_IN_EQUATION  # fmt: skip
                        mistakes[1] = Mistake.VAR_NOT_IN_EQUATION  # fmt: skip

        return mistakes

    # This method returns a two item list where the first item is the left side's mistakes and the second item is the
    # right side's mistakes
    @classmethod
    def get_arithmetic_mistakes(cls, this_step):
        prev_step = Step.get_prev(this_step)
        mistakes = [Mistake.NONE, Mistake.NONE]
        prev_latex_index = [-1, -1]

        # STEP 1: Is the new expression on each side a recognizable math expression?
        for s in range(0, 2):
            this_latex = getattr(this_step, f"expr{s+1}").latex
            if this_latex:
                prev_latex_index[s] = this_latex.find(getattr(prev_step, f"expr{s+1}"))
                sympy_expr = Expression.get_sympy_expression_from_latex(this_latex)
                if sympy_expr in Mistake.MISTAKE_TYPES:
                    mistakes[s] = sympy_expr
            else:
                mistakes[s] = Mistake.BLANK_EXPR

        # STEP 2: Is the previous expression on each side in the current expression on the same side?
        if mistakes[0] == mistakes[1] == Mistake.NONE:
            for s in range(0, 2):
                this_latex = getattr(this_step, f"expr{s + 1}").latex
                prev_latex = getattr(prev_step, f"expr{s + 1}").latex
                includes_prev_expression = True
                if prev_latex_index[s] < 0:
                    includes_prev_expression = False
                else:
                    if prev_latex_index[s] > 0:
                        try:
                            if this_latex[prev_latex_index[s] - 1].isnumeric():
                                includes_prev_expression = False
                        except IndexError:
                            pass
                    elif this_latex == prev_latex and mistakes[s] == Mistake.NONE:
                        mistakes[s] = Mistake.NO_ARITHMETIC
                    try:
                        # You follow an expression that ends in a number with another number
                        if (
                            this_latex[prev_latex_index[s] + len(prev_latex)].isnumeric()
                            and this_latex[prev_latex_index[s] + len(prev_latex) - 1].isnumeric()
                        ):
                            includes_prev_expression = False
                    except IndexError:
                        pass

                if not includes_prev_expression and mistakes[s] == Mistake.NONE:
                    mistakes[s] = Mistake.MISSING_PREV_EXPR
                else:
                    # Put parentheses around the new expression and see if it changes the value of it
                    latex_this_with_parens_around_prev = (
                        f"{this_latex[:prev_latex_index[s]]}"
                        f"\\left{prev_latex}\\right"
                        f"{this_latex[(prev_latex_index[s] + len(prev_latex)):]}"
                    )
                    sympy_this_with_parens_around_prev = Expression.get_sympy_expression_from_latex(
                        latex_this_with_parens_around_prev
                    )
                    if sympy_this_with_parens_around_prev not in Mistake.MISTAKE_TYPES:
                        this_sympy = Expression.get_sympy_expression_from_latex(this_latex)
                        if simplify(this_sympy - sympy_this_with_parens_around_prev) != 0:
                            mistakes[s] = Mistake.MISSING_PARENS
                    else:
                        mistakes[s] = sympy_this_with_parens_around_prev

        # STEP 3: Is each side’s previous expression substituted in each side’s current expression the same?
        # Example: 12x - 4 = 32 -> 12x - 4 + 4 = 32 + 16/4 (adding 4 to both sides)
        # To see if this is the same, we would check if 12x - 4 + 4 == 12x - 4 + 16/4 AND if 32 + 16/4 == 32 + 4
        if mistakes[0] == mistakes[1] == Mistake.NONE:
            for s in range(0, 2):
                this_latex = getattr(this_step, f"expr{s + 1}").latex
                prev_latex = getattr(prev_step, f"expr{s + 1}").latex
                other_side_latex = getattr(this_step, f"expr{(s % 2) + 1}").latex
                other_side_prev_latex = getattr(prev_step, f"expr{(s % 2) + 1}").latex
                latex_this_in_other_side = (
                    f"{other_side_latex[:prev_latex_index[(s+1)%2]]}"
                    f"\\left{prev_latex}\\right"
                    f"{other_side_latex[prev_latex_index[(s+1)%2]] + len(other_side_prev_latex):]}"
                )
                sympy_this_in_other_side = Expression.get_sympy_expression_from_latex(latex_this_in_other_side)
                if sympy_this_in_other_side not in Mistake.MISTAKE_TYPES:
                    this_sympy = Expression.get_sympy_expression_from_latex(this_latex)
                    if simplify(this_sympy - sympy_this_in_other_side) != 0:
                        mistakes[s] = Mistake.UNEQUAL_ARITHMETIC
                else:
                    print("should I do something here in check_arithmetic?")
                    # side_dict["feedback"] = feedback

        return mistakes

    # This method returns a two item list where the first item is the left side's mistakes and the second item is the
    # right side's mistakes
    @classmethod
    def get_rewrite_mistakes(cls, this_step):
        prev_step = Step.get_prev(this_step)
        mistakes = [Mistake.NONE, Mistake.NONE]

        for s in range(0, 2):
            this_latex = getattr(this_step, f"expr{s + 1}").latex
            prev_latex = getattr(prev_step, f"expr{s + 1}").latex
            if not prev_latex:
                mistakes[s] = Mistake.CANNOT_REWRITE
            elif this_latex:
                sympy_prev = Expression.get_sympy_expression_from_latex(prev_latex)
                sympy_this = Expression.get_sympy_expression_from_latex(this_latex)

                if sympy_prev not in Mistake.MISTAKE_TYPES and sympy_this not in Mistake.MISTAKE_TYPES:
                    if simplify(sympy_this - sympy_prev) == 0:
                        mistakes[s] = Mistake.NONE
                    else:
                        mistakes[s] = Mistake.REWRITE
                else:
                    if sympy_prev in Mistake.MISTAKE_TYPES:
                        mistakes[s] = Mistake.CANNOT_REWRITE
                    elif sympy_this in Mistake.MISTAKE_TYPES:
                        mistakes[s] = sympy_this
            else:
                mistakes[s] = Mistake.BLANK_EXPR

        return mistakes

    @classmethod
    def get_all_steps_mistakes(cls, problem):
        mistakes = {}
        for step in Step.objects.filter(problem=problem):
            mistakes[step.id] = [{"title": "", "content": ""}, {"title": "", "content": ""}]
            mistake_titles = Step.get_mistakes(step)
            mistakes[step.id][0]["title"] = mistake_titles[0]
            mistakes[step.id][1]["title"] = mistake_titles[1]
            for m in Mistake.MISTAKE_TYPES:
                if m[0] == mistake_titles[0]:
                    mistakes[step.id][0]["content"] = m[1]
                if m[0] == mistake_titles[1]:
                    mistakes[step.id][1]["content"] = m[1]

        return mistakes

    @classmethod
    def variable_isolated_side(cls, problem):
        last_step = Step.objects.filter(problem=problem).order_by("created").last()
        if last_step.expr1.latex == problem.variable:
            if last_step.expr1.latex not in Expression.get_variables_in_latex_expression(last_step.expr2.latex):
                return "right"
        elif last_step.expr2.latex == problem.variable:
            if last_step.expr2.latex not in Expression.get_variables_in_latex_expression(last_step.expr1.latex):
                return "left"

        return None


# Expressions can only have single letter variables
# Expressions can have at most 2 different variables
# Expressions cannot have underscores
# Expressions cannot have functions other than arithmetic and exponents (no sqrt or trig)
class Expression(models.Model):
    latex = models.CharField(max_length=100, blank=True, null=False, default="")

    """
    This method takes a latex expression and converts it into a human-readable string that SymPy can use
    Only called by the get_sympy_expression_from_latex
    """

    @classmethod
    def parse_latex(cls, latex_expression):
        if not latex_expression:
            return ""

        parsable_expression = latex_expression
        latex_word_dict = {
            "\\ ": "",
            "\\cdot": "*",
            "\\backslash": "\\",
            "\\left(": "(",
            "\\left\\{": "{",
            "\\left[": "[",
            "\\left|": "|",
            "\\right)": ")",
            "\\right\\}": "}",
            "\\right]": "]",
            "\\right|": "|",
            "\\%": "%",
            "\\sim": "~",
            "^": "**",
        }
        for latex_word in latex_word_dict:
            i = parsable_expression.find(latex_word)
            while i > -1:
                adder = 0  # If there is a variable directly after a latex word, there is a space added in
                try:
                    if parsable_expression[i + len(latex_word)] == " ":
                        adder = 1
                except IndexError:
                    pass

                parsable_expression = (
                    f"{parsable_expression[:i]}{latex_word_dict[latex_word]}"
                    f"{parsable_expression[i + len(latex_word) + adder:]}"
                )
                i = parsable_expression.find(latex_word)

        # Parse \frac
        numerator_open = parsable_expression.find("\\frac{")
        while numerator_open > -1:
            frac, frac_end = Expression.parse_frac(parsable_expression, numerator_open + 5)
            parsable_expression = f"{parsable_expression[:numerator_open]}{frac}{parsable_expression[frac_end:]}"
            numerator_open = parsable_expression.find("\\frac{")

        # Parse underscores _{ } to get rid of the brackets
        # Parsing underscores is tricky because you don't know how to interpret xy_f
        # is it x(y_f) or is it (xy_f)? Until i can figure this out...no underscores are allowed
        # i need to wrap these underscores in parentheses because subscripts with only 1 character do not get brackets
        # so i need x_1y_1 to be (x_1)(y_1) so sympy interprets properly. But if i can't tell how long the base is...
        # i don't know where to put the starting parentheses
        sub_open = parsable_expression.find("_{")
        sub_close = 0
        while sub_open > -1:
            open_count = 1
            for c in range(sub_open + 2, len(parsable_expression)):
                if parsable_expression[c] == "}":
                    open_count -= 1
                elif parsable_expression[c] == "{":
                    open_count += 1

                if open_count == 0:
                    sub_close = c
                    break
            parsable_expression = (
                f"{parsable_expression[:sub_open + 1]}{parsable_expression[sub_open + 2:sub_close]}"
                f"{parsable_expression[sub_close + 1:]}"
            )
            sub_open = parsable_expression.find("_{")

        return parsable_expression

    # Only called by parse_latex method
    @classmethod
    def parse_frac(cls, frac_str, expression_start):
        fraction = {"numerator": "", "denominator": ""}
        for expression in fraction:
            expression_end = frac_str.find("}", expression_start)
            open_count = 1
            for c in range(expression_start + 1, len(frac_str)):
                if frac_str[c] == "}":
                    open_count -= 1
                elif frac_str[c] == "{":
                    open_count += 1

                if open_count == 0:
                    expression_end = c
                    break

            fraction[expression] = frac_str[expression_start + 1: expression_end]  # fmt: skip
            expression_start = expression_end + 1

        return f"(({fraction['numerator']})/({fraction['denominator']}))", expression_start  # fmt: skip

    """
    This method converts a latex expression into it's equivalent SymPy expression
    If it is not a valid math expression, then it will return a mistake from users/models.py Mistake
    """

    @classmethod
    def get_sympy_expression_from_latex(cls, latex_expr):
        sympy_friendly_str = Expression.parse_latex(latex_expr)

        feedback = Mistake.NONE
        try:
            sympy_expr = parse_expr(
                sympy_friendly_str,
                None,
                transformations=standard_transformations + (implicit_multiplication_application,),
                evaluate=False,
            )
        except (SyntaxError, TypeError, NameError, IndexError):
            sympy_expr = None

        if not sympy_expr:
            feedback = Mistake.NON_MATH
        else:
            for i in range(0, len(sympy_friendly_str)):
                if sympy_friendly_str[i].isalpha():
                    pass
                elif sympy_friendly_str[i].isnumeric() or sympy_friendly_str[i] in "[]{}()-+*/. ":
                    close_index = -1
                    if sympy_friendly_str[i] == "[":
                        close_index = sympy_friendly_str.find("]", i)
                    elif sympy_friendly_str[i] == "{":
                        close_index = sympy_friendly_str.find("}", i)
                    elif sympy_friendly_str[i] == "(":
                        close_index = sympy_friendly_str.find(")", i)

                    if close_index > -1 and feedback == Mistake.NONE:
                        if len(sympy_friendly_str[i + 1 : close_index].strip()) == 0:  # NOQA
                            feedback = Mistake.GREY_BOX
                elif feedback == Mistake.NONE:
                    feedback = Mistake.UNKNOWN_SYM

        if feedback == Mistake.NONE:
            return sympy_expr
        else:
            return feedback

    """
    This is only used by the method get_variables_in_latex_expression
    This is a recursive function that returns a list of variables in expr
    If symbols are next to each other, multiplication is assumed: ie "xyz" -> [x, y, z]
    If a symbol appears more than once, it will be listed more than once
    """

    @classmethod
    def get_variables_in_sympy_expression(cls, sympy_expr):
        symbol_list = []
        if sympy_expr and sympy_expr.func == symbol.Symbol:
            symbol_list.append(str(sympy_expr))
        for arg in sympy_expr.args:
            temp_list = Expression.get_variables_in_sympy_expression(arg)
            if temp_list:
                symbol_list.extend(temp_list)

        return symbol_list

    """
    This calls the method get_variables_in_sympy expression
    Takes the results and returns a sorted set of variables in an expression
    """

    @classmethod
    def get_variables_in_latex_expression(cls, latex_expr):
        if latex_expr:
            sympy_expr = Expression.get_sympy_expression_from_latex(latex_expr)

            if sympy_expr not in Mistake.MISTAKE_TYPES:
                symbols_list = Expression.get_variables_in_sympy_expression(sympy_expr)
                symbols_list.sort()
                return list(set(symbols_list))

        return []


class Step(models.Model):
    DEFINE = "define"
    REWRITE = "rewrite"
    ARITHMETIC = "arithmetic"
    DELETE = "delete"
    NONE = "none"
    STEP_TYPES = [
        (DEFINE, "Define Equation"),
        (REWRITE, "Rewrite"),
        (ARITHMETIC, "Arithmetic"),
        (DELETE, "Delete"),
        (NONE, "None"),
    ]

    problem = models.ForeignKey(Problem, related_name="step_problem", on_delete=models.CASCADE, default=None)
    created = models.DateTimeField(auto_now_add=True)
    step_type = models.CharField(max_length=10, choices=STEP_TYPES, default=NONE)
    test_count = models.PositiveSmallIntegerField(default=0)
    left_expr = models.OneToOneField(Expression, on_delete=models.CASCADE, related_name="left_side", default=None)
    right_expr = models.OneToOneField(Expression, on_delete=models.CASCADE, related_name="right_side", default=None)

    @classmethod
    def save_new(cls, problem):
        step = Step(problem=problem)
        step.left_expr = Expression()
        step.left_expr.save()
        step.right_expr = Expression()
        step.right_expr.save()
        step.save()

        return step

    @classmethod
    def is_first(cls, this_step):
        first_step = (Step.objects.filter(problem=this_step.problem).order_by("created").first())  # fmt: skip
        if first_step == this_step:
            return True
        else:
            return False

    @classmethod
    def is_last(cls, this_step):
        last_step = (Step.objects.filter(problem=this_step.problem).order_by("created").last())  # fmt: skip
        if last_step == this_step:
            return True
        else:
            return False

    @classmethod
    def get_number(cls, this_step):
        all_steps = Step.objects.filter(problem=this_step.problem).order_by("created")
        for step_num in range(0, len(all_steps)):
            if all_steps[step_num] == this_step:
                return step_num + 1

        return 0

    @classmethod
    def get_prev(cls, this_step):
        if Step.is_first(this_step):
            return None
        else:
            all_steps = Step.objects.filter(problem=this_step.problem).order_by("created")  # fmt: skip
            for step_num in range(0, len(all_steps)):
                if all_steps[step_num] == this_step:
                    return all_steps[step_num - 1]

        return None

    @classmethod
    def get_next(cls, this_step):
        if Step.is_last(this_step):
            return None
        else:
            all_steps = Step.objects.filter(problem=this_step.problem).order_by("created")  # fmt: skip
            for step_num in range(0, len(all_steps)):
                if all_steps[step_num] == this_step:
                    if step_num + 1 < len(all_steps):
                        return all_steps[step_num + 1]

        return None

    @classmethod
    def get_mistakes(cls, step):
        # First item in list is the left expression's mistake and the second item is the right expression's
        mistakes = [Mistake.NONE, Mistake.NONE]
        if len(step.left_expr.latex.strip()) == 0:
            mistakes[0] = Mistake.BLANK_EXPR
        if len(step.right_expr.latex.strip()) == 0:
            mistakes[1] = Mistake.BLANK_EXPR

        if Step.is_first(step):
            if step.step_type != Step.DEFINE:
                if mistakes[0] != Mistake.BLANK_EXPR:
                    mistakes[0] = Mistake.NO_EQUATION
                if mistakes[1] != Mistake.BLANK_EXPR:
                    mistakes[1] = Mistake.NO_EQUATION
            else:
                mistakes = Problem.get_define_equation_mistakes(step)
                if mistakes[0] == mistakes[1] == Mistake.NONE:
                    if not step.problem.variable:
                        mistakes[0] = Mistake.NO_VAR_SELECTED
                        mistakes[1] = Mistake.NO_VAR_SELECTED
                    else:
                        # This is where I used to flag equations being non-linear as a mistake
                        pass
        else:
            if step.step_type == Step.DEFINE:
                if mistakes[0] != Mistake.BLANK_EXPR:
                    mistakes[0] = Mistake.ALREADY_DEFINED
                if mistakes[1] != Mistake.BLANK_EXPR:
                    mistakes[1] = Mistake.ALREADY_DEFINED
            elif step.step_type == Step.REWRITE:
                if step.problem.variable:
                    mistakes = Problem.get_rewrite_mistakes(step)
                else:
                    if mistakes[0] != Mistake.BLANK_EXPR:
                        mistakes[0] = Mistake.NO_VAR_SELECTED
                    if mistakes[1] != Mistake.BLANK_EXPR:
                        mistakes[1] = Mistake.NO_VAR_SELECTED
            elif step.step_type == Step.ARITHMETIC:
                if step.problem.variable:
                    mistakes = Problem.get_arithmetic_mistakes(step)
                else:
                    if mistakes[0] != Mistake.BLANK_EXPR:
                        mistakes[0] = Mistake.NO_VAR_SELECTED
                    if mistakes[1] != Mistake.BLANK_EXPR:
                        mistakes[1] = Mistake.NO_VAR_SELECTED
            else:
                if mistakes[0] != Mistake.BLANK_EXPR:
                    mistakes[0] = Mistake.NO_STEP_TYPE
                if mistakes[1] != Mistake.BLANK_EXPR:
                    mistakes[1] = Mistake.NO_STEP_TYPE

        return mistakes
