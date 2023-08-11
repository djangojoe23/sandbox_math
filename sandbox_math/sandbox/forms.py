from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, Div, Field, Layout, Submit
from django import forms
from django.core.mail import BadHeaderError, send_mail
from django.http import HttpResponse, HttpResponseRedirect


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    sender = forms.EmailField(required=True)
    subject = forms.CharField(max_length=100, required=True)
    message = forms.CharField(widget=forms.Textarea, required=True)
    captcha = ReCaptchaField(widget=ReCaptchaV3)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_id = "contactForm"
        self.helper.form_class = "row g-4 needs-validation"
        self.helper.attrs = {"novalidate": ""}
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div(
                HTML('<label class="form-label fs-base" for="name">Name</label>'),
                Field("name", css_class="form-control form-control-lg"),
                css_class="col-sm-6",
            ),
            Div(
                HTML('<label class="form-label fs-base" for="sender">Email</label>'),
                Field("sender", css_class="form-control form-control-lg"),
                css_class="col-sm-6",
            ),
            Div(
                HTML('<label class="form-label fs-base" for="subject">Subject</label>'),
                Field("subject", css_class="form-control form-control-lg"),
                css_class="col-sm-12",
            ),
            Div(
                HTML('<label class="form-label fs-base" for="message">Message</label>'),
                Field("message", css_class="form-control form-control-lg", rows="5"),
                css_class="col-sm-12",
            ),
            Field("captcha"),
        )
        self.helper.add_input(Submit("submitForm", "Submit", css_class="btn-lg"))

    def send_email(self):
        name = self.cleaned_data.get("name", "")
        sender = self.cleaned_data.get("sender", "")
        subject = self.cleaned_data.get("subject", "")
        message = self.cleaned_data.get("message", "")
        if subject and message and sender:
            try:
                send_mail(subject, f"SENDER NAME: {name}\n\nMESSAGE: {message}", sender, ["joe@sandboxmath.com"])
            except BadHeaderError:
                return HttpResponse("Invalid header found.")
            return HttpResponseRedirect("/contact/thanks/")
        else:
            # In reality we'd use a form class
            # to get proper validation errors.
            return HttpResponse("Make sure all fields are entered and valid.")
