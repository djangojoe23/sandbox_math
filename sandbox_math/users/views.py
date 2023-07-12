from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView
from guest_user.functions import is_guest_user

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


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UserPassesTestMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def test_func(self):
        print("herhehere")
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
