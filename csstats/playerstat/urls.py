from django.urls import path
from . import views

app_name = "playerstat"

urlpatterns = [
    path("<int:player_id>/", views.PlayerStatsView.as_view(), name="stats"),
    path(
        "<int:player_id>/matches",
        views.PlayerMatchesView.as_view(),
        name="matches",
    ),
    path(
        "<int:player_id>/weapons",
        views.PlayerWeaponView.as_view(),
        name="weapons",
    ),
    path(
        "<int:player_id>/auth_code",
        views.AuthCodeUpdateView.as_view(),
        name="auth_code",
    ),
]
