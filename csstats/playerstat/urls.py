from django.urls import path
from . import views

app_name = 'playerstat'

urlpatterns = [
    path('<int:player_id>/matches', views.PlayerMatchesView.as_view(), name='matches'),
]
