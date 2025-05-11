from django.urls import path
from . import views

app_name = "mapstat"

urlpatterns = [
    path("<int:demo_id>/", views.DemoScoreBoardView.as_view(), name="demo"),
    path("<int:demo_id>/duels", views.DemoDeulsView.as_view(), name="duels"),
    path(
        "<int:demo_id>/rounds", views.DemoRoundsView.as_view(), name="rounds"
    ),
    path(
        "<int:demo_id>/weapons", views.DemoWeaponView.as_view(), name="weapons"
    ),
]
