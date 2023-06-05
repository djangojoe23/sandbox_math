from django.urls import path

from sandbox_math.algebra.views import (
    AttemptNewStepView,
    BaseView,
    DeleteStepView,
    NewStepView,
    SaveNewView,
    StartNewView,
    UpdateExpressionView,
    UpdateHelpClickView,
    UpdateStepTypeView,
    UpdateVariableView,
)

app_name = "algebra"
urlpatterns = [
    path("", BaseView.as_view(), name="base"),
    path("start-new/", StartNewView.as_view(), name="start-new", ),  # fmt: skip
    path("save-new/", SaveNewView.as_view(), name="save-new", ),  # fmt: skip
    path("update-step-type/", UpdateStepTypeView.as_view(), name="update-step-type", ),  # fmt: skip
    path("update-expression/", UpdateExpressionView.as_view(), name="update-expression", ),  # fmt: skip
    path("update-help-click/", UpdateHelpClickView.as_view(), name="update-help-click", ),  # fmt: skip
    path("update-variable/", UpdateVariableView.as_view(), name="update-variable", ),  # fmt: skip
    path("delete-step/", DeleteStepView.as_view(), name="delete-step", ),  # fmt: skip
    path("attempt-new-step/", AttemptNewStepView.as_view(), name="attempt-new-step", ),  # fmt: skip
    path("new-step/", NewStepView.as_view(), name="new-step", ),  # fmt: skip
]
