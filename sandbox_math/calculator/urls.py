from django.urls import path

from sandbox_math.calculator.views import GetResponseView

app_name = "calculator"
urlpatterns = [
    path(
        "get-response/",
        GetResponseView.as_view(),
        name="get_response",
    ),
]
