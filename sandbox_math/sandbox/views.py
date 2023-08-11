from django.conf import settings
from django.views.generic.edit import FormView

from sandbox_math.sandbox.forms import ContactForm


class ContactFormView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = "/contact-thanks/"
    extra_context = {"recaptcha_key": settings.RECAPTCHA_PUBLIC_KEY}

    def form_valid(self, form):
        form.send_email()

        return super().form_valid(form)
