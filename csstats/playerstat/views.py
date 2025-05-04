from django.utils import timezone
import datetime
from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404, redirect
from playerstat.mixins import PlayerListMixin, PlayerMixin
from mapstat.mixins import DemoMixin
from demo_database.models import (
    Demo,
    PlayerInDemo,
    Side,
    BuyType,
    Duels,
    Player,
    Round,
    KillsInRound,
)
from django.db.models import Sum, Avg, Q, Count, Prefetch, F
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, View, UpdateView
from demo_database.savedb import save_demo
from steam.mixins import SteamUserBaseMixin
from .forms import PlayerCodeForm
from django.contrib.auth.mixins import LoginRequiredMixin
from social_django.models import UserSocialAuth
import traceback
from demo_database.tasks import get_new_sharecodes


class PlayerMatchesView(PlayerListMixin, ListView):
    template_name = "playerstat/matches.html"
    context_object_name = "player_demos"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[Any]:
        demos = super().get_queryset()

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
            filters = filters & Q(demo__data_played__gte=start_date_filter)

        if end_date_filter:
            end_date_filter = timezone.datetime.strptime(
                end_date_filter, "%Y-%m-%d"
            ).date()
            end_date_filter = timezone.make_aware(
                datetime.datetime.combine(end_date_filter, datetime.time.max)
            )
            filters = filters & Q(demo__data_played__lte=end_date_filter)

        if map_filter:
            filters = filters & Q(demo__map=map_filter)

        if mode_filter:
            filters = filters & Q(demo__match_type=mode_filter)

        if min_rating_filter:
            filters = filters & Q(rating__gte=float(min_rating_filter))

        if max_rating_filter:
            filters = filters & Q(rating__lte=float(max_rating_filter))

        return (
            PlayerInDemo.objects.filter(
                Q(demo__in=demos) & Q(player=self.player)
            )
            .select_related("rang", "demo", "demo__map", "demo__match_type")
            .annotate(
                kills=Sum("scoreboard__kills"),
                assists=Sum("scoreboard__assists"),
                deaths=Sum("scoreboard__deaths"),
                adr=Sum("scoreboard__damage") / Sum("scoreboard__rounds"),
                win_clutches_1x1=Sum("scoreboard__win_clutches_1x1"),
                win_clutches_1x2=Sum("scoreboard__win_clutches_1x2"),
                win_clutches_1x3=Sum("scoreboard__win_clutches_1x3"),
                win_clutches_1x4=Sum("scoreboard__win_clutches_1x4"),
                win_clutches_1x5=Sum("scoreboard__win_clutches_1x5"),
                kills_3=Sum("scoreboard__kills_3"),
                kills_4=Sum("scoreboard__kills_4"),
                kills_5=Sum("scoreboard__kills_5"),
                rating=(
                    (
                        0.73 * Sum("scoreboard__kast_rounds")
                        + 0.3591 * Sum("scoreboard__kills")
                        - 0.5329 * Sum("scoreboard__deaths")
                        + 0.0032 * Sum("scoreboard__damage")
                    )
                    / Sum("scoreboard__rounds")
                    + 0.2372
                    * (
                        (
                            2.13 * Sum("scoreboard__kills")
                            + 0.42 * Sum("scoreboard__assists")
                        )
                        / Sum("scoreboard__rounds")
                        - 0.41
                    )
                    + 0.1587
                ),
            )
            .filter(filters)
            .order_by("-demo__data_played")
        )


class PlayerStatsView(SteamUserBaseMixin, PlayerMixin, DetailView):
    model = Player
    template_name = "playerstat/stats.html"
    context_object_name = "player"
    pk_url_kwarg = "player_id"

    def get_object(self, queryset=None) -> QuerySet[Any]:
        super().get_object(queryset)
        player = get_object_or_404(Player, pk=self.kwargs["player_id"])
        player_in_demos = PlayerInDemo.objects.filter(player=player.pk)
        demos = Demo.objects.filter(id__in=player_in_demos.values("demo"))

        self.player_stat = (
            PlayerInDemo.objects.filter(Q(demo__in=demos) & Q(player=player))
            .select_related("rang", "demo", "demo__map")
            .annotate(
                kills=Sum("scoreboard__kills"),
                assists=Sum("scoreboard__assists"),
                deaths=Sum("scoreboard__deaths"),
                adr=Sum("scoreboard__damage") / Sum("scoreboard__rounds"),
                win_clutches_1x1=Sum("scoreboard__win_clutches_1x1"),
                win_clutches_1x2=Sum("scoreboard__win_clutches_1x2"),
                win_clutches_1x3=Sum("scoreboard__win_clutches_1x3"),
                win_clutches_1x4=Sum("scoreboard__win_clutches_1x4"),
                win_clutches_1x5=Sum("scoreboard__win_clutches_1x5"),
                loss_clutches_1x1=Sum("scoreboard__loss_clutches_1x1"),
                loss_clutches_1x2=Sum("scoreboard__loss_clutches_1x2"),
                loss_clutches_1x3=Sum("scoreboard__loss_clutches_1x3"),
                loss_clutches_1x4=Sum("scoreboard__loss_clutches_1x4"),
                loss_clutches_1x5=Sum("scoreboard__loss_clutches_1x5"),
                kills_1=Sum("scoreboard__kills_1"),
                kills_2=Sum("scoreboard__kills_2"),
                kills_3=Sum("scoreboard__kills_3"),
                kills_4=Sum("scoreboard__kills_4"),
                kills_5=Sum("scoreboard__kills_5"),
                demos_count=Count("demo__id", distinct=True),
                win_count=Count(
                    "demo__id",
                    distinct=True,
                    filter=Q(team=F("demo__win_team")),
                ),
                rating=(
                    (
                        0.73 * Sum("scoreboard__kast_rounds")
                        + 0.3591 * Sum("scoreboard__kills")
                        - 0.5329 * Sum("scoreboard__deaths")
                        + 0.0032 * Sum("scoreboard__damage")
                    )
                    / Sum("scoreboard__rounds")
                    + 0.2372
                    * (
                        (
                            2.13 * Sum("scoreboard__kills")
                            + 0.42 * Sum("scoreboard__assists")
                        )
                        / Sum("scoreboard__rounds")
                        - 0.41
                    )
                    + 0.1587
                ),
            )
            .first()
        )
        return player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["player_stat"] = self.player_stat
        return context


class AuthCodeUpdateView(SteamUserBaseMixin, LoginRequiredMixin, UpdateView):
    form_class = PlayerCodeForm
    model = Player
    template_name = "playerstat/changeAuthCode.html"
    pk_url_kwarg = "player_id"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("social:begin", "steam")

        if self.request.user.is_superuser:
            return redirect("csstats:home")

        if (
            self.get_object().pk
            != UserSocialAuth.objects.get(user=self.request.user).uid
        ):
            return redirect("playerstat:stats", self.kwargs["player_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            "playerstat:stats", kwargs={"player_id": self.kwargs["player_id"]}
        )
