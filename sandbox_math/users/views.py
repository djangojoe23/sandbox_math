from datetime import datetime, timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView
from guest_user.functions import is_guest_user

from sandbox_math.users.models import User as myUser

User = get_user_model()


class UserDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def test_func(self):
        if self.request.user.username != self.get_object().username or is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        days_prior = 90
        context["days_prior"] = days_prior

        practice_messages = myUser.get_activity_overview(self.request.user.id, days_prior)
        if practice_messages["activity_score"] <= 0.5:
            context["last_week_activity_message"] = "You need to be more active."
            context["activity_text_color"] = "danger"
        elif 0.5 < practice_messages["activity_score"] <= 0.75:
            context["last_week_activity_message"] = "You are pretty active. Don't let up!"
            context["activity_text_color"] = "warning"
        else:
            context["last_week_activity_message"] = "You are very active! Keep it up!"
            context["activity_text_color"] = "success"

        for key, value in practice_messages.items():
            context[key] = value

        mistake_stats = myUser.get_mistakes_overview(self.request.user.id, days_prior)
        context["recent_mistakes_count"] = mistake_stats["recent_made_count"]
        context["most_common_mistake"] = mistake_stats["recent_most_common"]
        context["mistakes_text_color"] = "danger"
        if mistake_stats["per_action"]:
            if mistake_stats["per_action"] == "worse":
                context["last_week_mistakes_message"] = "You are making mistakes more frequently."
            elif mistake_stats["per_action"] == "same":
                context["last_week_mistakes_message"] = "You are making mistakes at the same rate."
                context["mistakes_text_color"] = "warning"
            else:
                context["last_week_mistakes_message"] = "You are making mistakes less frequently."
                context["mistakes_text_color"] = "success"
        else:
            context["last_week_mistakes_message"] = "You didn't do anything last week! See section above."

        if mistake_stats["find_rate"]:
            if mistake_stats["find_rate"] == "worse":
                context[
                    "find_rate_message"
                ] = "You are clicking on the <span class='fs-3'><i class='ai-circle-help'></i></span> icons too much."
            elif mistake_stats["find_rate"] == "same":
                context[
                    "find_rate_message"
                ] = "The rate at which you are finding your mistakes did not change last week."
            else:
                context["find_rate_message"] = (
                    "You are getting better at using the <span class='fs-3'><i class='ai-circle-help'></i></span> "
                    "icons to find your mistakes."
                )
        else:
            context["find_rate_message"] = None

        if mistake_stats["fixed_rate"]:
            if mistake_stats["fixed_rate"] == "worse":
                context["fixed_rate_message"] = "Fix the mistakes that you have made."
            elif mistake_stats["fixed_rate"] == "same":
                context[
                    "fixed_rate_message"
                ] = "The rate at which you are fixing your mistakes did not change last week."
            else:
                context[
                    "fixed_rate_message"
                ] = "You are getting better at fixing the mistakes that you make. Keep it up!"
        else:
            context["fixed_rate_message"] = None

        solved_stats = myUser.get_solved_overview(self.request.user.id, days_prior)
        context["solved_detail"] = (
            f"Since you opened your account, you've started {solved_stats['problems_started']}"
            f" problems and solved {solved_stats['problems_solved']} of them."
        )
        context["recently_solved_detail"] = (
            f"In the last {days_prior} days, you started "
            f"{solved_stats['recently_started']} problems and solved "
            f"{solved_stats['recently_solved']} of them."
        )
        context["solved_text_color"] = "danger"
        if solved_stats["solved_rate_status"] == "worse":
            context["solved_message"] = "You need to solve more of the problems that you start."
        elif solved_stats["solved_rate_status"] == "better":
            context["solved_message"] = "You are solving more of the problems you are starting."
            context["solved_text_color"] = "success"
        else:
            context["solved_message"] = "You are solving problems at the same rate."
            context["solved_text_color"] = "warning"

        return context


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def test_func(self):
        if is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_success_url(self):
        assert self.request.user.is_authenticated  # for mypy to know that the user is authenticated
        return self.request.user.get_absolute_url()

    def get_object(self):
        return self.request.user


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


class UserActivityInfoView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_activity_info.html"

    def test_func(self):
        if self.request.user.username != self.get_object().username or is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["chart_title"] = "Activity per Day All Time"
        activity_per_day = {}
        date_dict = {"Problems Started": 0, "Steps Added": 0, "Rewrite Checks": 0, "Solution Checks": 0}
        label_model_dict = {
            "Problems Started": "Problem",
            "Steps Added": "Step",
            "Rewrite Checks": "CheckRewrite",
            "Solution Checks": "CheckSolution",
        }

        context["data_labels"] = []
        user_obj = User.objects.get(id=self.request.user.id)
        if user_obj:
            next_date = user_obj.date_joined
            today = timezone.make_aware(datetime.now())
            time_since_joining = today - user_obj.date_joined
            while next_date < today:
                date_string = next_date.strftime('"%b %-d, %Y"')
                activity_per_day[date_string] = date_dict.copy()

                next_date += timedelta(days=1)

            # then put the activity dict into context variables that i can inject into my template
            for d in activity_per_day:
                if not len(context["data_labels"]) or d.startswith("Jan 1"):
                    context["data_labels"].append(d)
                else:
                    context["data_labels"].append(f'{d.split(",")[0]}"')

            count = 0
            for label in date_dict:
                count += 1
                context[f"dataset_{count}_label"] = label
                label_model = apps.get_model("algebra", label_model_dict[label])
                if label in ["Problems Started", "Steps Added"]:
                    count_by_date = label_model.get_recent_by_date(self.request.user.id, time_since_joining.days)
                else:
                    count_by_date = label_model.get_recent_by_date(
                        label_model_dict[label], self.request.user.id, time_since_joining.days
                    )

                for d in count_by_date:
                    if d in activity_per_day:
                        activity_per_day[d][label] = count_by_date[d]

                context[f"dataset_{count}_data"] = []
                for d in activity_per_day:
                    context[f"dataset_{count}_data"].append(activity_per_day[d][label])

        return context


user_activity_info_view = UserActivityInfoView.as_view()


class UserMistakesInfoView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_mistakes_info.html"

    def test_func(self):
        if self.request.user.username != self.get_object().username or is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["bar_chart_title"] = "Mistakes per Day All Time"
        context["pie_chart_title"] = "Most Common Mistakes All Time"

        # get count of mistakes made found and fixed per day
        date_dict = {"Mistakes Made": 0, "Mistakes Found": 0, "Mistakes Fixed": 0}

        date_list = []
        context["data_labels"] = []
        user_obj = User.objects.get(id=self.request.user.id)
        if user_obj:
            next_date = user_obj.date_joined
            today = timezone.make_aware(datetime.now())
            time_since_joining = today - user_obj.date_joined
            while next_date < today:
                date_string = next_date.strftime('"%b %-d, %Y"')
                date_list.append(date_string)
                next_date += timedelta(days=1)

            for d in date_list:
                if not len(context["data_labels"]) or d.startswith("Jan 1"):
                    context["data_labels"].append(d)
                else:
                    context["data_labels"].append(f'{d.split(",")[0]}"')

            count = 0
            mistake_model = apps.get_model("users", "Mistake")
            count_by_date = mistake_model.get_recent_by_date(self.request.user.id, time_since_joining.days)

            for label in date_dict:
                count += 1
                context[f"dataset_{count}_label"] = label

                context[f"dataset_{count}_data"] = []
                for d in date_list:
                    if d in count_by_date:
                        context[f"dataset_{count}_data"].append(count_by_date[d][label])
                    else:
                        context[f"dataset_{count}_data"].append(0)

            mistakes_by_type = (
                mistake_model.objects.exclude(mistake_type=mistake_model.NONE)
                .values("mistake_type")
                .annotate(type_count=Count("mistake_type"))
                .order_by("-type_count")
            )
            other_sum = 0
            count = 0
            context["pie_labels"] = []
            context["pie_data"] = []
            for m_dict in mistakes_by_type:
                if m_dict["type_count"] > 0:
                    if count < 9:
                        context["pie_labels"].append(f'"{mistake_model.get_mistake_message(m_dict["mistake_type"])}"')
                        context["pie_data"].append(m_dict["type_count"])
                    else:
                        if count == 9:
                            context["pie_labels"].append('"Other"')
                        other_sum += m_dict["type_count"]
                    count += 1
            context["pie_data"].append(other_sum)

        return context


user_mistakes_info_view = UserMistakesInfoView.as_view()


class UserSolutionsInfoView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_solutions_info.html"

    def test_func(self):
        if self.request.user.username != self.get_object().username or is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["hello"] = "howdy!"

        return context


user_solutions_info_view = UserSolutionsInfoView.as_view()


class UserVarietyInfoView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/user_variety_info.html"

    def test_func(self):
        if self.request.user.username != self.get_object().username or is_guest_user(self.request.user):
            return False
        else:
            return True

    def handle_no_permission(self):
        if is_guest_user(self.request.user):
            return redirect("account_signup")
        else:
            return redirect("account_login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["hello"] = "howdy!"

        return context


user_variety_info_view = UserVarietyInfoView.as_view()
