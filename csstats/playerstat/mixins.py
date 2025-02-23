from typing import Any
from django.db.models.query import QuerySet
from demo_database.models import Demo, Player, PlayerInDemo
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404


class PlayerMixin:

    def get_queryset(self) -> QuerySet[Any]:
        self.player = get_object_or_404(Player, pk=self.kwargs['player_id'])
        player_in_demos = PlayerInDemo.objects.filter(player=self.player.pk)

        return Demo.objects.filter(id__in=player_in_demos.values('demo'))

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex['player'] = self.player
        return contex
