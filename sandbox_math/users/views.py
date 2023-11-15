from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
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

        context["hello"] = "howdy!"

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

        context["hello"] = "howdy!"

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
