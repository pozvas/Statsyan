from typing import Any
from django.db.models.query import QuerySet
from steam.mixins import SteamUserBaseMixin
from demo_database.models import (
    Demo,
    Player,
    PlayerInDemo,
    Map,
    MatchType,
    Side,
)
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from .forms import PlayerCodeForm
from django.http import HttpResponse
from django.utils import timezone
import datetime
from django.db.models import Sum, Avg, Q, Count, Prefetch, F


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

        self.sides = Side.objects.all()

        start_date_filter = self.request.GET.get("start_date")
        end_date_filter = self.request.GET.get("end_date")
        map_filter = self.request.GET.get("map")
        mode_filter = self.request.GET.get("mode")
        min_rating_filter = self.request.GET.get("min_rating")
        max_rating_filter = self.request.GET.get("max_rating")

        filters = Q()

        if start_date_filter:
            start_date_filter = timezone.datetime.strptime(
                start_date_filter, "%Y-%m-%d"
            ).date()
            filters = filters & Q(data_played__gte=start_date_filter)

        if end_date_filter:
            end_date_filter = timezone.datetime.strptime(
                end_date_filter, "%Y-%m-%d"
            ).date()
            end_date_filter = timezone.make_aware(
                datetime.datetime.combine(end_date_filter, datetime.time.max)
            )
            filters = filters & Q(data_played__lte=end_date_filter)

        if map_filter:
            filters = filters & Q(map=map_filter)

        if mode_filter:
            filters = filters & Q(match_type=mode_filter)

        if min_rating_filter:
            filters = filters & Q(rating__gte=float(min_rating_filter))

        if max_rating_filter:
            filters = filters & Q(rating__lte=float(max_rating_filter))

        self.player = get_object_or_404(Player, pk=self.kwargs["player_id"])
        return (
            Demo.objects.filter(players__player=self.player)
            .annotate(
                rating=(
                    (
                        0.73 * Sum("players__scoreboard__kast_rounds")
                        + 0.3591 * Sum("players__scoreboard__kills")
                        - 0.5329 * Sum("players__scoreboard__deaths")
                        + 0.0032 * Sum("players__scoreboard__damage")
                    )
                    / Sum("players__scoreboard__rounds")
                    + 0.2372
                    * (
                        (
                            2.13 * Sum("players__scoreboard__kills")
                            + 0.42 * Sum("players__scoreboard__assists")
                        )
                        / Sum("players__scoreboard__rounds")
                        - 0.41
                    )
                    + 0.1587
                ),
            )
            .filter(filters)
            .values("id")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["player"] = self.player
        contex["sides"] = self.sides
        return contex
