from django.urls import path

from sandbox_math.algebra.views import BaseView

app_name = "algebra"
urlpatterns = [
    path("", BaseView.as_view(), name="base"),
]
