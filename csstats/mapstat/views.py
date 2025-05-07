from typing import Any
from django.db import connection
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404
import os
from mapstat.mixins import DemoMixin
from demo_database.models import (
    Demo,
    PlayerInDemo,
    PlayerWeaponStat,
    Side,
    BuyType,
    Duels,
    Player,
    Round,
    KillsInRound,
    Weapon,
    WeaponType,
)
from django.db.models.functions import Coalesce
from django.db.models import (
    Sum,
    Avg,
    Q,
    Count,
    Prefetch,
    Subquery,
    OuterRef,
    IntegerField,
    CharField,
    Case,
    When,
    Value,
    F,
)
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView
from demo_database.savedb import save_demo
import traceback


class DemoScoreBoardView(DemoMixin, ListView):
    template_name = "mapstat/scoreboard.html"
    model = PlayerInDemo
    context_object_name = "players_in_demo"

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        self.buy_types = BuyType.objects.all()

        self.win_team_t_score = (
            Round.objects.filter(
                demo=self.demo,
                t_team_name=self.demo.win_team,
                win_reason__win_side__code="TERRORIST",
            )
            .values("demo")
            .annotate(count=Count("id"))
            .values("count")
        )

        self.lose_team_t_score = (
            Round.objects.filter(
                ~Q(t_team_name=self.demo.win_team)
                & Q(demo=self.demo)
                & Q(win_reason__win_side__code="TERRORIST")
            )
            .values("demo")
            .annotate(count=Count("id"))
            .values("count")
        )

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

        return (
            PlayerInDemo.objects.filter(demo=self.demo)
            .select_related("player", "rang")
            .filter(filters)
            .annotate(
                rounds=Sum("scoreboard__rounds"),
                kills=Sum("scoreboard__kills"),
                assists=Sum("scoreboard__assists"),
                deaths=Sum("scoreboard__deaths"),
                damage=Sum("scoreboard__damage"),
                adr=(
                    Sum("scoreboard__damage") * 1.0 / Sum("scoreboard__rounds")
                ),
                kast_rounds=Sum("scoreboard__kast_rounds"),
                kast=(
                    Sum("scoreboard__kast_rounds")
                    * 100.0
                    / Sum("scoreboard__rounds")
                ),
                win_clutches_1x1=Sum("scoreboard__win_clutches_1x1"),
                win_clutches_1x2=Sum("scoreboard__win_clutches_1x2"),
                win_clutches_1x3=Sum("scoreboard__win_clutches_1x3"),
                win_clutches_1x4=Sum("scoreboard__win_clutches_1x4"),
                win_clutches_1x5=Sum("scoreboard__win_clutches_1x5"),
                all_win_clutches=(
                    Sum("scoreboard__win_clutches_1x1")
                    + Sum("scoreboard__win_clutches_1x2")
                    + Sum("scoreboard__win_clutches_1x3")
                    + Sum("scoreboard__win_clutches_1x4")
                    + Sum("scoreboard__win_clutches_1x5")
                ),
                kills_1=Sum("scoreboard__kills_1"),
                kills_2=Sum("scoreboard__kills_2"),
                kills_3=Sum("scoreboard__kills_3"),
                kills_4=Sum("scoreboard__kills_4"),
                kills_5=Sum("scoreboard__kills_5"),
                kills_3_over=(
                    Sum("scoreboard__kills_3")
                    + Sum("scoreboard__kills_4")
                    + Sum("scoreboard__kills_5")
                ),
                first_kills=Sum("scoreboard__first_kills"),
                first_deaths=Sum("scoreboard__first_deaths"),
                first_kills_dif=(
                    Sum("scoreboard__first_kills")
                    - Sum("scoreboard__first_deaths")
                ),
                utility_damage=Sum("scoreboard__utility_damage"),
                enemy_flashed=Sum("scoreboard__enemy_flashed"),
                flash_assists=Sum("scoreboard__flash_assists"),
                impact=(
                    (
                        2.13 * Sum("scoreboard__kills")
                        + 0.42 * Sum("scoreboard__assists")
                    )
                    / Sum("scoreboard__rounds")
                    - 0.41
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
            .order_by("-rating")
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["buy_types"] = self.buy_types
        contex["lose_team_t_score"] = self.lose_team_t_score.count
        contex["win_team_t_score"] = self.win_team_t_score.count
        return contex


class DemoDeulsView(DemoMixin, ListView):
    template_name = "mapstat/duels.html"
    context_object_name = "duel_stats"

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        return Duels.objects.filter(demo=self.demo).select_related(
            "attacker_player",
            "victim_player",
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)

        duel_stats = {}
        for duel in contex["duel_stats"]:
            if duel.attacker_player.pk not in duel_stats:
                duel_stats[duel.attacker_player.pk] = {}
            if (
                duel.victim_player.pk
                not in duel_stats[duel.attacker_player.pk]
            ):
                duel_stats[duel.attacker_player.pk][duel.victim_player.pk] = 0

            duel_stats[duel.attacker_player.pk][duel.victim_player.pk] = {
                "kills": duel.kills,
                "open_kills": duel.open_kills,
            }

        contex["duel_stats"] = duel_stats
        contex["default_kills"] = {
            "kills": 0,
            "open_kills": 0,
        }

        return contex


class DemoRoundsView(DemoMixin, ListView):
    model = Round
    template_name = "mapstat/rounds.html"
    context_object_name = "rounds"

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()

        return (
            Round.objects.annotate(
                win_team=Case(
                    When(
                        win_reason__win_side__code="CT",
                        then=F("ct_team_name"),
                    ),
                    default=F("t_team_name"),
                    output_field=CharField(),
                ),
                win_buy=Case(
                    When(
                        win_reason__win_side__code="CT",
                        then=F("ct_buy_type__name"),
                    ),
                    default=F("t_buy_type__name"),
                    output_field=CharField(),
                ),
                lose_team=Case(
                    When(
                        win_reason__win_side__code="CT",
                        then=F("t_team_name"),
                    ),
                    default=F("ct_team_name"),
                    output_field=CharField(),
                ),
                lose_buy=Case(
                    When(
                        win_reason__win_side__code="CT",
                        then=F("t_buy_type__name"),
                    ),
                    default=F("ct_buy_type__name"),
                    output_field=CharField(),
                ),
            )
            .filter(Q(demo=self.demo))
            .prefetch_related(
                Prefetch(
                    "kills",
                    queryset=KillsInRound.objects.select_related(
                        "round",
                        "round__win_reason",
                        "round__win_reason__win_side",
                        "weapon",
                        "attacker",
                        "attacker_side",
                        "assister",
                        "assister_side",
                        "victim",
                        "victim_side",
                    ),
                )
            )
            .select_related(
                "win_reason",
                "win_reason__win_side",
                "ct_buy_type",
                "t_buy_type",
                "demo__match_type",
            )
            .annotate(
                deaths_1=Count(
                    "kills__id",
                    filter=Q(
                        Q(
                            kills__victim_side__code="CT",
                            kills__round__ct_team_name=self.teams_name[0],
                        )
                        | Q(
                            kills__victim_side__code="TERRORIST",
                            kills__round__t_team_name=self.teams_name[0],
                        )
                    ),
                ),
                deaths_2=Count(
                    "kills__id",
                    filter=Q(
                        Q(
                            kills__victim_side__code="CT",
                            kills__round__ct_team_name=self.teams_name[1],
                        )
                        | Q(
                            kills__victim_side__code="TERRORIST",
                            kills__round__t_team_name=self.teams_name[1],
                        )
                    ),
                ),
                wins_1=Coalesce(
                    Subquery(
                        Round.objects.annotate(
                            win_team=Case(
                                When(
                                    win_reason__win_side__code="CT",
                                    then=F("ct_team_name"),
                                ),
                                default=F("t_team_name"),
                                output_field=CharField(),
                            )
                        )
                        .filter(
                            demo=self.demo,
                            round_number__lte=OuterRef("round_number"),
                            win_team=self.teams_name[0],
                        )
                        .values("demo")
                        .annotate(count=Count("id"))
                        .values("count"),
                        output_field=IntegerField(),
                    ),
                    0,
                ),
                wins_2=Coalesce(
                    Subquery(
                        Round.objects.annotate(
                            win_team=Case(
                                When(
                                    win_reason__win_side__code="CT",
                                    then=F("ct_team_name"),
                                ),
                                default=F("t_team_name"),
                                output_field=CharField(),
                            )
                        )
                        .filter(
                            demo=self.demo,
                            round_number__lte=OuterRef("round_number"),
                            win_team=self.teams_name[1],
                        )
                        .values("demo")
                        .annotate(count=Count("id"))
                        .values("count"),
                        output_field=IntegerField(),
                    ),
                    0,
                ),
                max_players=Case(
                    When(demo__match_type__code=7, then=Value(2)),
                    default=Value(5),
                    output_field=IntegerField(),
                ),
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        return contex


class DemoWeaponView(DemoMixin, ListView):
    template_name = "mapstat/weapons.html"
    context_object_name = "weapons"

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        self.weapon_types = WeaponType.objects.all()

        side_filter = self.request.GET.get("side")
        player_filter = self.request.GET.get("player")
        weapon_type_filter = self.request.GET.get("weapon_type")

        filters = Q(
            weapon_player_stat__isnull=False,
            weapon_player_stat__hitgroup_stat__isnull=False,
        )

        if side_filter:
            filters = filters & Q(weapon_player_stat__side=side_filter)

        if weapon_type_filter:
            filters = filters & Q(weapon_type=weapon_type_filter)

        if player_filter:
            filters = filters & Q(Q(weapon_player_stat__player=player_filter))

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
        WHERE pws.demo_id = %s 
        {f"AND pws.side_id = {side_filter}" if side_filter else ""}
        {f"AND w.weapon_type_id = {weapon_type_filter}" if weapon_type_filter else ""}
        {f"AND (pws.player_id = {player_filter} OR pid.team = '{player_filter}')" if player_filter else ""}
        GROUP BY w.id, w.name, w.caption, w.weapon_type_id, w.image
        """

        with connection.cursor() as cursor:
            cursor.execute(
                query,
                [
                    self.demo.id,
                ],
            )
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]

            return results

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex["weapon_types"] = self.weapon_types
        return contex


def upload_demo(request):
    if request.method == "POST" and request.FILES["file"]:
        uploaded_file = request.FILES["file"]
        file_path = default_storage.save(
            uploaded_file.name, ContentFile(uploaded_file.read())
        )
        file_modification_time = request.POST.get("file_mtime")

        absolute_file_path = default_storage.path(file_path)
        try:
            if file_modification_time:
                mod_time = float(file_modification_time)
                os.utime(absolute_file_path, (mod_time, mod_time))

            demo = save_demo(absolute_file_path)
            return HttpResponseRedirect(
                reverse("mapstat:demo", kwargs={"demo_id": demo})
            )
        except Exception:
            traceback.print_exc()
            return HttpResponseRedirect(reverse("mapstat:upload"))
        finally:
            default_storage.delete(file_path)

    return render(request, "uploaddemo/uploaddemo.html")
