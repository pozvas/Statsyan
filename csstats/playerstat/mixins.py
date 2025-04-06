from typing import Any
from django.db.models.query import QuerySet
from steam.mixins import SteamUserBaseMixin
from demo_database.models import Demo, Player, PlayerInDemo
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from .forms import PlayerCodeForm
from django.http import HttpResponse


class PlayerAuthCodeMixin:

    def post(self, request, *args, **kwargs):
        player = get_object_or_404(Player, pk=self.kwargs['player_id'])
        form = PlayerCodeForm(request.POST, instance=player)
        form.save()
        return HttpResponse(request.path)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex['form'] = PlayerCodeForm()
        return contex


class PlayerListMixin(SteamUserBaseMixin, PlayerAuthCodeMixin):

    def get_queryset(self) -> QuerySet[Any]:
        self.player = get_object_or_404(Player, pk=self.kwargs['player_id'])
        player_in_demos = PlayerInDemo.objects.filter(player=self.player.pk)

        return Demo.objects.filter(id__in=player_in_demos.values('demo'))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex['player'] = self.player
        return contex
