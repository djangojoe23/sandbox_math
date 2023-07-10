from allauth.account.forms import LoginForm, SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django.contrib.auth import forms as admin_forms
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserLoginForm(LoginForm):

    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "login needs-validation"
        self.helper.form_action = reverse("account_login")
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML('<i class="ai-mail fs-lg position-absolute top-50 start-0 translate-middle-y ms-3"></i>'),
                    Field("login", css_class="form-control-lg ps-5"),
                    css_class="position-relative",
                ),
                css_class="pb-3",
            ),
            Div(
                Div(
                    HTML(
                        '<i class="ai-lock-closed fs-lg position-absolute top-50 start-0 translate-middle-y ms-3"></i>'
                    ),
                    Div(
                        Field("password", css_class="form-control-lg ps-5"),
                        HTML(
                            '<label class="password-toggle-btn" aria-label="Show/hide password"><input tabindex="-1" '
                            'class="password-toggle-check" type="checkbox"><span class="password-toggle-indicator">'
                            "</span></label>"
                        ),
                        css_class="password-toggle",
                    ),
                    css_class="position-relative",
                ),
                css_class="mb-4",
            ),
            RememberCheckbox("remember"),
            Submit("submit", "Log In", css_class="btn-lg w-100 mb-4"),
        )

        try:
            if self.request.GET["next"]:
                self.helper.layout.insert(
                    3, HTML('<input type="hidden" name="next" value="{}" />'.format(self.request.GET["next"]))
                )
        except KeyError:
            pass


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "signup needs-validation"
        self.helper.form_show_labels = False
        self.helper.form_id = "signup_form"
        self.helper.form_action = reverse("account_signup")
        self.helper.layout = Layout(
            Div(UserSignupInput("username"), UserSignupInput("email"), css_class="row row-cols-1 row-cols-sm-2"),
            Div(
                Field("password1", css_class="form-control-lg"),
                HTML(
                    '<label class="password-toggle-btn" aria-label="Show/hide password"><input tabindex="-1" '
                    'class="password-toggle-check" type="checkbox"><span class="password-toggle-indicator">'
                    "</span></label>"
                ),
                css_class="password-toggle mb-4",
            ),
            Div(
                Field("password2", css_class="form-control-lg"),
                HTML(
                    '<label class="password-toggle-btn" aria-label="Show/hide password"><input tabindex="-1" '
                    'class="password-toggle-check" type="checkbox"><span class="password-toggle-indicator">'
                    "</span></label>"
                ),
                css_class="password-toggle mb-4",
            ),
            Submit("submit", "Join", css_class="btn-lg w-100 mb-4"),
        )


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class RememberCheckbox(Field):
    template = "account/remember_checkbox.html"


class UserSignupInput(Field):
    template = "account/user_signup_input.html"
