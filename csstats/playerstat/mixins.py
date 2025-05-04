from typing import Any
from django.db.models.query import QuerySet
from steam.mixins import SteamUserBaseMixin
from demo_database.models import Demo, Player, PlayerInDemo, Map, MatchType
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from .forms import PlayerCodeForm
from django.http import HttpResponse


class PlayerMixin:

    def get_queryset(self) -> QuerySet[Any]:
        self.maps = Map.objects.all()
        self.math_types = MatchType.objects.all()
        return None

    def get_object(self, queryset=None) -> QuerySet[Any]:
        self.maps = Map.objects.all()
        self.math_types = MatchType.objects.all()
        return None

    def post(self, request, *args, **kwargs):
        player = get_object_or_404(Player, pk=self.kwargs["player_id"])
        form = PlayerCodeForm(request.POST, instance=player)
        form.save()
        return HttpResponse(request.path)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["form"] = PlayerCodeForm()
        contex["maps"] = self.maps
        contex["math_types"] = self.math_types
        return contex


class PlayerListMixin(SteamUserBaseMixin, PlayerMixin):

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        self.player = get_object_or_404(Player, pk=self.kwargs["player_id"])
        player_in_demos = PlayerInDemo.objects.filter(player=self.player.pk)

        return Demo.objects.filter(id__in=player_in_demos.values("demo"))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["player"] = self.player
        return contex
