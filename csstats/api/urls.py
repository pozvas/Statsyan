from django.urls import path
from .views import ScoreBoardDetailView, PlayerMatchesView, DemoFileUploadView, WathDemo

urlpatterns = [
    path('match/<int:demo_id>/', ScoreBoardDetailView.as_view(), name='scoreboard-detail'),
    path('player/<int:steamid>/', PlayerMatchesView.as_view(), name='players-matches'),
    path('upload/', DemoFileUploadView.as_view(), name='upload'),
    path('watch/', WathDemo.as_view(), name='watch')
]