import requests
from django.conf import settings
from django.http import HttpResponseRedirect
from django.views.generic.edit import FormView

from sandbox_math.sandbox.forms import ContactForm


class ContactFormView(FormView):
    template_name = "pages/contact.html"
    form_class = ContactForm
    success_url = "/contact-thanks/"
    extra_context = {"recaptcha_key": settings.RECAPTCHA_PUBLIC_KEY}

    def form_valid(self, form):
        token = self.request.POST.get("captcha")
        if token:
            data = {"secret": settings.RECAPTCHA_PRIVATE_KEY, "response": token}
            # verify response with Google
            response = requests.post("https://www.google.com/recaptcha/api/siteverify", data=data)
            result = response.json()
            # check results
            print(result)
            if result["success"] is True and result["score"] >= 0.5:
                form.send_email()
            else:
                return HttpResponseRedirect("/contact-error/")

        return super().form_valid(form)
