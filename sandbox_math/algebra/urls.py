from django.urls import path

from sandbox_math.algebra.views import BaseView, SaveNewView, StartNewView, UpdateHelpClickView, UpdateStepTypeView

app_name = "algebra"
urlpatterns = [
    path("", BaseView.as_view(), name="base"),
    path("start-new/", StartNewView.as_view(), name="start-new", ),  # fmt: skip
    path("save-new/", SaveNewView.as_view(), name="save-new", ),  # fmt: skip
    path("update-step-type/", UpdateStepTypeView.as_view(), name="update-step-type", ),  # fmt: skip
    path("update-help-click/", UpdateHelpClickView.as_view(), name="update-help-click", ),  # fmt: skip
]
