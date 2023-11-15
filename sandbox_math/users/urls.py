from django.urls import path

from sandbox_math.users.views import (
    user_activity_info_view,
    user_detail_view,
    user_mistakes_info_view,
    user_redirect_view,
    user_solutions_info_view,
    user_update_view,
    user_variety_info_view,
)

app_name = "users"
urlpatterns = [
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("<str:username>/", view=user_detail_view, name="detail"),
    path("<str:username>/activity_info", view=user_activity_info_view, name="activity_info"),
    path("<str:username>/mistakes_info", view=user_mistakes_info_view, name="mistakes_info"),
    path("<str:username>/solutions_info", view=user_solutions_info_view, name="solutions_info"),
    path("<str:username>/variety_info", view=user_variety_info_view, name="variety_info"),
]
