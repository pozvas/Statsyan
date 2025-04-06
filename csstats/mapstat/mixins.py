from typing import Any
from django.db.models.query import QuerySet
from demo_database.models import Demo, Player, PlayerInDemo
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from steam.mixins import SteamUserBaseMixin


class DemoMixin(SteamUserBaseMixin):

    def get_queryset(self) -> QuerySet[Any]:
        self.demo = get_object_or_404(Demo, pk=self.kwargs['demo_id'])
        players_by_team = (
            PlayerInDemo.objects.values('team')
            .annotate(total_players=Count('id'))
        )
        self.teams_name = [item['team'] for item in players_by_team]

        self.team_a_players = Player.objects.filter(
            Q(playerindemo__team=self.teams_name[0]) &
            Q(playerindemo__demo=self.demo)
        )
        self.team_b_players = Player.objects.filter(
            Q(playerindemo__team=self.teams_name[1]) &
            Q(playerindemo__demo=self.demo)
        )
        return None

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex['demo'] = self.demo
        contex['teams_name'] = self.teams_name
        contex['team_a_players'] = self.team_a_players
        contex['team_b_players'] = self.team_b_players
        return contex
