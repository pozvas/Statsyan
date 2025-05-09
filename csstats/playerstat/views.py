from django.db import connection
from django.utils import timezone
import datetime
from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404, redirect
from playerstat.mixins import PlayerMixin, PlayerMixin
from mapstat.mixins import DemoMixin
from demo_database.models import (
    Demo,
    PlayerInDemo,
    ScoreBoard,
    Side,
    BuyType,
    Duels,
    Player,
    Round,
    KillsInRound,
    WeaponType,
)
from django.db.models import (
    Sum,
    Avg,
    Q,
    Count,
    Prefetch,
    F,
    Case,
    When,
    Value,
    IntegerField,
)
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
import json


class PlayerMatchesView(PlayerMixin, ListView):
    template_name = "playerstat/matches.html"
    context_object_name = "player_demos"
    paginate_by = 20

    def get_queryset(self) -> QuerySet[Any]:
        demos = super().get_queryset()
        return (
            PlayerInDemo.objects.filter(
                Q(demo_id__in=demos) & Q(player=self.player)
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
            .order_by("-demo__data_played")
        )


class PlayerStatsView(PlayerMixin, DetailView):
    model = Player
    template_name = "playerstat/stats.html"
    context_object_name = "player"
    pk_url_kwarg = "player_id"

    def post(self, request, *args, **kwargs):
        player = get_object_or_404(Player, pk=self.kwargs["player_id"])
        form = PlayerCodeForm(request.POST, instance=player)
        form.save()
        return HttpResponse(request.path)

    def get_object(self, queryset=None) -> QuerySet[Any]:
        demos = super().get_object(queryset)
        self.sides = Side.objects.all()

        side_filter = self.request.GET.get("side")
        buy_type_filter = self.request.GET.get("buy_type")
        enemy_buy_type_filter = self.request.GET.get("enemy_buy_type")

        filters = Q()

        if side_filter:
            filters = filters & Q(demos__scoreboard__side=side_filter)
        if buy_type_filter:
            filters = filters & Q(demos__scoreboard__buy_type=buy_type_filter)
        if enemy_buy_type_filter:
            filters = filters & Q(
                demos__scoreboard__enemy_buy_type=enemy_buy_type_filter
            )

        self.player_stat = (
            Player.objects.filter(
                Q(demos__demo__in=demos) & Q(pk=self.player.pk) & filters
            )
            .annotate(
                kills_total=Sum("demos__scoreboard__kills"),
                headshots_total=Sum("demos__scoreboard__headshots"),
                assists_total=Sum("demos__scoreboard__assists"),
                deaths_total=Sum("demos__scoreboard__deaths"),
                damage_total=Sum("demos__scoreboard__damage"),
                rounds_total=Sum("demos__scoreboard__rounds"),
                first_kills_total=Sum("demos__scoreboard__first_kills"),
                first_attempts_total=Sum("demos__scoreboard__first_deaths")
                + Sum("demos__scoreboard__first_kills"),
                win_clutches_1x1_total=Sum(
                    "demos__scoreboard__win_clutches_1x1"
                ),
                win_clutches_1x2_total=Sum(
                    "demos__scoreboard__win_clutches_1x2"
                ),
                win_clutches_1x3_total=Sum(
                    "demos__scoreboard__win_clutches_1x3"
                ),
                win_clutches_1x4_total=Sum(
                    "demos__scoreboard__win_clutches_1x4"
                ),
                win_clutches_1x5_total=Sum(
                    "demos__scoreboard__win_clutches_1x5"
                ),
                loss_clutches_1x1_total=Sum(
                    "demos__scoreboard__loss_clutches_1x1"
                ),
                loss_clutches_1x2_total=Sum(
                    "demos__scoreboard__loss_clutches_1x2"
                ),
                loss_clutches_1x3_total=Sum(
                    "demos__scoreboard__loss_clutches_1x3"
                ),
                loss_clutches_1x4_total=Sum(
                    "demos__scoreboard__loss_clutches_1x4"
                ),
                loss_clutches_1x5_total=Sum(
                    "demos__scoreboard__loss_clutches_1x5"
                ),
                clutches_1x1_total=Sum("demos__scoreboard__loss_clutches_1x1")
                + Sum("demos__scoreboard__win_clutches_1x1"),
                clutches_1x2_total=Sum("demos__scoreboard__loss_clutches_1x2")
                + Sum("demos__scoreboard__win_clutches_1x2"),
                clutches_1x3_total=Sum("demos__scoreboard__loss_clutches_1x3")
                + Sum("demos__scoreboard__win_clutches_1x3"),
                clutches_1x4_total=Sum("demos__scoreboard__loss_clutches_1x4")
                + Sum("demos__scoreboard__win_clutches_1x4"),
                clutches_1x5_total=Sum("demos__scoreboard__loss_clutches_1x5")
                + Sum("demos__scoreboard__win_clutches_1x5"),
                win_clutches_total=(
                    Sum("demos__scoreboard__win_clutches_1x1")
                    + Sum("demos__scoreboard__win_clutches_1x2")
                    + Sum("demos__scoreboard__win_clutches_1x3")
                    + Sum("demos__scoreboard__win_clutches_1x4")
                    + Sum("demos__scoreboard__win_clutches_1x5")
                ),
                loss_clutches_total=(
                    Sum("demos__scoreboard__loss_clutches_1x1")
                    + Sum("demos__scoreboard__loss_clutches_1x2")
                    + Sum("demos__scoreboard__loss_clutches_1x3")
                    + Sum("demos__scoreboard__loss_clutches_1x4")
                    + Sum("demos__scoreboard__loss_clutches_1x5")
                ),
                clutches_total=(
                    Sum("demos__scoreboard__loss_clutches_1x1")
                    + Sum("demos__scoreboard__loss_clutches_1x2")
                    + Sum("demos__scoreboard__loss_clutches_1x3")
                    + Sum("demos__scoreboard__loss_clutches_1x4")
                    + Sum("demos__scoreboard__loss_clutches_1x5")
                    + Sum("demos__scoreboard__win_clutches_1x1")
                    + Sum("demos__scoreboard__win_clutches_1x2")
                    + Sum("demos__scoreboard__win_clutches_1x3")
                    + Sum("demos__scoreboard__win_clutches_1x4")
                    + Sum("demos__scoreboard__win_clutches_1x5")
                ),
                kills_1_total=Sum("demos__scoreboard__kills_1"),
                kills_2_total=Sum("demos__scoreboard__kills_2"),
                kills_3_total=Sum("demos__scoreboard__kills_3"),
                kills_4_total=Sum("demos__scoreboard__kills_4"),
                kills_5_total=Sum("demos__scoreboard__kills_5"),
                rating_total=(
                    (
                        0.73 * Sum("demos__scoreboard__kast_rounds")
                        + 0.3591 * Sum("demos__scoreboard__kills")
                        - 0.5329 * Sum("demos__scoreboard__deaths")
                        + 0.0032 * Sum("demos__scoreboard__damage")
                    )
                    / Sum("demos__scoreboard__rounds")
                    + 0.2372
                    * (
                        (
                            2.13 * Sum("demos__scoreboard__kills")
                            + 0.42 * Sum("demos__scoreboard__assists")
                        )
                        / Sum("demos__scoreboard__rounds")
                        - 0.41
                    )
                    + 0.1587
                ),
            )
            .first()
        )

        self.maps_stat = (
            Player.objects.filter(
                Q(demos__demo__in=demos) & Q(pk=self.player.pk)
            )
            .annotate(
                demos_count=Count("demos__id"),
                win_count=Count(
                    "demos__demo__id",
                    filter=Q(demos__demo__win_team=F("demos__team")),
                ),
                lose_count=Count(
                    "demos__demo__id",
                    filter=Q(
                        ~Q(demos__demo__win_team=F("demos__team"))
                        & Q(demos__demo__win_team__isnull=False)
                    ),
                ),
                tie_count=Count(
                    "demos__demo__id",
                    filter=Q(demos__demo__win_team__isnull=True),
                ),
            )
            .first()
        )

        if self.player_stat is None:
            self.player_stat = {
                "kills_total": 0,
                "headshots_total": 0,
                "assists_total": 0,
                "deaths_total": 0,
                "damage_total": 0,
                "rounds_total": 0,
                "first_kills_total": 0,
                "first_attempts_total": 0,
                "win_clutches_1x1_total": 0,
                "win_clutches_1x2_total": 0,
                "win_clutches_1x3_total": 0,
                "win_clutches_1x4_total": 0,
                "win_clutches_1x5_total": 0,
                "loss_clutches_1x1_total": 0,
                "loss_clutches_1x2_total": 0,
                "loss_clutches_1x3_total": 0,
                "loss_clutches_1x4_total": 0,
                "loss_clutches_1x5_total": 0,
                "clutches_1x1_total": 0,
                "clutches_1x2_total": 0,
                "clutches_1x3_total": 0,
                "clutches_1x4_total": 0,
                "clutches_1x5_total": 0,
                "win_clutches_total": 0,
                "loss_clutches_total": 0,
                "clutches_total": 0,
                "kills_1_total": 0,
                "kills_2_total": 0,
                "kills_3_total": 0,
                "kills_4_total": 0,
                "kills_5_total": 0,
                "rating_total": 0.0,
            }

        if self.maps_stat is None:
            self.maps_stat = {
                "demos_count": 0,
                "win_count": 0,
                "lose_count": 0,
                "tie_count": 0,
            }

        return self.player

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["player_stat"] = self.player_stat
        context["maps_stat"] = self.maps_stat
        context["sides"] = self.sides
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


class PlayerWeaponView(PlayerMixin, ListView):
    template_name = "playerstat/weapons.html"
    context_object_name = "weapons"

    def get_queryset(self) -> QuerySet[Any]:
        demos = super().get_queryset()
        self.weapon_types = WeaponType.objects.all()

        side_filter = self.request.GET.get("side")
        weapon_type_filter = self.request.GET.get("weapon_type")

        filters = Q(
            weapon_player_stat__isnull=False,
            weapon_player_stat__hitgroup_stat__isnull=False,
        )

        if side_filter:
            filters = filters & Q(weapon_player_stat__side=side_filter)

        if weapon_type_filter:
            filters = filters & Q(weapon_type=weapon_type_filter)

        # изменить когда перейду на постре и для карт
        # SELECT
        #     w.id,
        #     w.name,
        #     w.caption,
        #     w.weapon_type_id,
        #     w.image,
        #     SUM(pws.fires_count) AS fires,
        #     phs.damage,
        #     phs.kills,
        #     phs.hits,
        #     SUM(CASE WHEN hg.name = 'head' THEN phs.hits ELSE 0 END) AS headshots
        # FROM demo_database_weapon w
        # JOIN demo_database_playerweaponstat pws ON w.id = pws.weapon_id
        # JOIN LATERAL (
        #     SELECT
        #     SUM(phs1.damage) AS damage,
        #     SUM(phs1.kills) AS kills,
        #     SUM(phs1.hits) AS hits
        #     FROM demo_database_playerhitgroupstat phs1
        #     WHERE pws.id = phs1.player_weapon_stat_id
        # ) phs ON TRUE

        query = f"""
        SELECT
            w.id,
            w.name,
            w.caption,
            w.weapon_type_id,
            w.image,
            SUM(DISTINCT pws.fires_count) AS fires,
            SUM(phs.damage) AS damage,
            SUM(phs.kills) AS kills,
            SUM(phs.hits) AS hits,
            SUM(CASE WHEN hg.name = 'head' THEN phs.hits ELSE 0 END) AS headshots
        FROM demo_database_weapon w
        JOIN demo_database_playerweaponstat pws ON w.id = pws.weapon_id
        JOIN demo_database_playerhitgroupstat phs ON pws.id = phs.player_weapon_stat_id
        LEFT JOIN demo_database_playerindemo pid ON pid.demo_id = pws.demo_id AND pid.player_id = pws.player_id
        LEFT JOIN demo_database_hitgroup hg ON phs.hit_group_id = hg.id
        WHERE pws.demo_id in ({",".join(str(demo["id"]) for demo in demos)}) 
        AND pws.player_id = {self.player.pk}
        {f"AND pws.side_id = {side_filter}" if side_filter else ""}
        {f"AND w.weapon_type_id = {weapon_type_filter}" if weapon_type_filter else ""}
        GROUP BY w.id, w.name, w.caption, w.weapon_type_id, w.image
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["weapon_types"] = self.weapon_types
        return contex


class PlayerGraphsView(PlayerMixin, ListView):
    template_name = "playerstat/graphs.html"
    context_object_name = "data"

    def get_queryset(self) -> QuerySet[Any]:
        demos = super().get_queryset()
        side_filter = self.request.GET.get("side")
        buy_type_filter = self.request.GET.get("buy_type")
        enemy_buy_type_filter = self.request.GET.get("enemy_buy_type")

        filters = Q()

        if side_filter:
            filters = filters & Q(scoreboard__side=side_filter)
        if buy_type_filter:
            filters = filters & Q(scoreboard__buy_type=buy_type_filter)
        if enemy_buy_type_filter:
            filters = filters & Q(
                scoreboard__enemy_buy_type=enemy_buy_type_filter
            )

        self.elo = (
            PlayerInDemo.objects.filter(player=self.player, demo__in=demos)
            .select_related("rang", "demo")
            .order_by("demo__data_played")
        )

        return (
            PlayerInDemo.objects.filter(player=self.player, demo__in=demos)
            .select_related("rang", "demo")
            .filter(filters)
            .annotate(
                kdr=Sum("scoreboard__kills")
                * 1.00
                / Sum("scoreboard__deaths"),
                adr=(
                    Sum("scoreboard__damage") * 1.0 / Sum("scoreboard__rounds")
                ),
                kast=(
                    Sum("scoreboard__kast_rounds")
                    * 100.0
                    / Sum("scoreboard__rounds")
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
            .order_by("demo__data_played")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        elo = []
        rating = []
        adr = []
        kast = []
        kdr = []

        for map in self.elo:
            elem_elo = {
                "x": map.demo.data_played.strftime("%d-%m %H:%M"),
                "y": (
                    map.elo_old
                    if map.elo_old
                    else map.rang.code * 1111 if map.rang.code else None
                ),
            }
            elo.append(elem_elo)

        for map in context["data"]:
            elem_rating = {
                "x": map.demo.data_played.strftime("%d-%m %H:%M"),
                "y": (map.rating),
            }
            rating.append(elem_rating)

            elem_adr = {
                "x": map.demo.data_played.strftime("%d-%m %H:%M"),
                "y": (map.adr),
            }
            adr.append(elem_adr)

            elem_kdr = {
                "x": map.demo.data_played.strftime("%d-%m %H:%M"),
                "y": (map.kdr),
            }
            kdr.append(elem_kdr)

            elem_kast = {
                "x": map.demo.data_played.strftime("%d-%m %H:%M"),
                "y": (map.kast),
            }
            kast.append(elem_kast)

        context["elo"] = json.dumps(elo)
        context["rating"] = json.dumps(rating)
        context["adr"] = json.dumps(adr)
        context["kast"] = json.dumps(kast)
        context["kdr"] = json.dumps(kdr)
        return context
