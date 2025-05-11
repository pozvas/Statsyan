from typing import Any
from django.db.models.query import QuerySet
from steam.mixins import SteamUserBaseMixin
from demo_database.models import (
    BuyType,
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


class PlayerMixin(SteamUserBaseMixin):

    def get_demos(self) -> QuerySet[Any]:
        self.sides = Side.objects.all()
        self.maps = Map.objects.all()
        self.math_types = MatchType.objects.all()
        self.buy_types = BuyType.objects.all()

        start_date_filter = self.request.GET.get("start_date")
        end_date_filter = self.request.GET.get("end_date")
        map_filter = self.request.GET.get("map")
        mode_filter = self.request.GET.get("mode")
        min_rating_filter = self.request.GET.get("min_rating")
        max_rating_filter = self.request.GET.get("max_rating")

        filters = Q()

        try:
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
                    datetime.datetime.combine(
                        end_date_filter, datetime.time.max
                    )
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
        except Exception:
            pass

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

    def get_object(self, queryset=None) -> QuerySet[Any]:
        return self.get_demos()

    def get_queryset(self) -> QuerySet[Any]:
        return self.get_demos()

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["maps"] = self.maps
        context["math_types"] = self.math_types
        context["player"] = self.player
        context["sides"] = self.sides
        context["buy_types"] = self.buy_types
        return context
