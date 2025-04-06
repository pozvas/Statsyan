from typing import Any
from django.db.models.query import QuerySet
from django.shortcuts import render, get_object_or_404
from mapstat.mixins import DemoMixin
from demo_database.models import (Demo, PlayerInDemo, Side,
                                  BuyType, Duels, Player,
                                  Round, KillsInRound)
from django.db.models import Sum, Avg, Q, Count, Prefetch
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView
from demo_database.savedb import save_demo
import traceback


class DemoScoreBoardView(DemoMixin, ListView):
    template_name = 'mapstat/scoreboard.html'
    model = PlayerInDemo
    context_object_name = 'players_in_demo'

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        self.sides = Side.objects.all()
        self.buy_types = BuyType.objects.all()

        side_filter = self.request.GET.get('side')
        buy_type_filter = self.request.GET.get('buy_type')
        enemy_buy_type_filter = self.request.GET.get('enemy_buy_type')

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
            .select_related('player', 'rang')
            .filter(filters).annotate(
                rounds=Sum('scoreboard__rounds'),
                kills=Sum('scoreboard__kills'),
                assists=Sum('scoreboard__assists'),
                deaths=Sum('scoreboard__deaths'),
                damage=Sum('scoreboard__damage'),
                adr=(
                    Sum('scoreboard__damage') * 1.0
                    / Sum('scoreboard__rounds')
                ),
                kast_rounds=Sum('scoreboard__kast_rounds'),
                kast=(
                    Sum('scoreboard__kast_rounds') * 100.0
                    / Sum('scoreboard__rounds')
                ),
                win_clutches_1x1=Sum('scoreboard__win_clutches_1x1'),
                win_clutches_1x2=Sum('scoreboard__win_clutches_1x2'),
                win_clutches_1x3=Sum('scoreboard__win_clutches_1x3'),
                win_clutches_1x4=Sum('scoreboard__win_clutches_1x4'),
                win_clutches_1x5=Sum('scoreboard__win_clutches_1x5'),
                all_win_clutches=(
                    Sum('scoreboard__win_clutches_1x1') +
                    Sum('scoreboard__win_clutches_1x2') +
                    Sum('scoreboard__win_clutches_1x3') +
                    Sum('scoreboard__win_clutches_1x4') +
                    Sum('scoreboard__win_clutches_1x5')
                ),
                kills_1=Sum('scoreboard__kills_1'),
                kills_2=Sum('scoreboard__kills_2'),
                kills_3=Sum('scoreboard__kills_3'),
                kills_4=Sum('scoreboard__kills_4'),
                kills_5=Sum('scoreboard__kills_5'),
                kills_3_over=(
                    Sum('scoreboard__kills_3') +
                    Sum('scoreboard__kills_4') +
                    Sum('scoreboard__kills_5')
                ),
                first_kills=Sum('scoreboard__first_kills'),
                first_deaths=Sum('scoreboard__first_deaths'),
                first_kills_dif=(
                    Sum('scoreboard__first_kills') -
                    Sum('scoreboard__first_deaths')
                ),
                utility_damage=Sum('scoreboard__utility_damage'),
                enemy_flashed=Sum('scoreboard__enemy_flashed'),
                flash_assists=Sum('scoreboard__flash_assists'),
                impact=(
                    (
                        2.13 * Sum('scoreboard__kills') +
                        0.42 * Sum('scoreboard__assists')
                    ) /
                    Sum('scoreboard__rounds') - 0.41
                    ),
                rating=(
                    (
                        0.73 * Sum('scoreboard__kast_rounds') +
                        0.3591 * Sum('scoreboard__kills') -
                        0.5329 * Sum('scoreboard__deaths') +
                        0.0032 * Sum('scoreboard__damage')
                    )
                    / Sum('scoreboard__rounds') + 0.2372 * (
                            (
                                2.13 * Sum('scoreboard__kills') +
                                0.42 * Sum('scoreboard__assists')
                            ) / Sum('scoreboard__rounds') - 0.41
                        ) + 0.1587),
            )
            .order_by('-rating')
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        contex['sides'] = self.sides
        contex['buy_types'] = self.buy_types
        return contex


class DemoDeulsView(DemoMixin, ListView):
    template_name = 'mapstat/duels.html'
    context_object_name = 'duel_stats'

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()
        return Duels.objects.filter(demo=self.demo).select_related(
            'attacker_player', 'victim_player',
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)

        duel_stats = {}
        for duel in contex['duel_stats']:
            if duel.attacker_player.pk not in duel_stats:
                duel_stats[duel.attacker_player.pk] = {}
            if duel.victim_player.pk not in duel_stats[duel.attacker_player.pk]:
                duel_stats[duel.attacker_player.pk][duel.victim_player.pk] = 0

            duel_stats[duel.attacker_player.pk][duel.victim_player.pk] = {
                'kills': duel.kills,
                'open_kills': duel.open_kills,
            }

        contex['duel_stats'] = duel_stats
        contex['default_kills'] = {
            'kills': 0,
            'open_kills': 0,
        }

        return contex


class DemoRoundsView(DemoMixin, ListView):
    model = Round
    template_name = 'mapstat/rounds.html'
    context_object_name = 'rounds'

    def get_queryset(self) -> QuerySet[Any]:
        super().get_queryset()

        return (
            Round.objects.filter(
                Q(demo=self.demo)
            )
            .prefetch_related(
                Prefetch(
                    'kills',
                    queryset=KillsInRound.objects.select_related(
                        'weapon', 'attacker', 'attacker_side',
                        'assister', 'assister_side', 'victim',
                        'victim_side'
                    )
                )
            )
            .select_related(
                'win_reason', 'win_reason__win_side',
                'ct_buy_type', 't_buy_type'
            )
            .annotate(
                kills_t=Count(
                    'kills__id',
                    Q(kills__victim_side__name='CT')
                ),
                kills_ct=Count(
                    'kills__id',
                    Q(kills__victim_side__name='TERRORIST')
                )
            )
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        return contex


class DemoWeaponView(DemoMixin, ListView):
    pass


def upload_demo(request):
    if request.method == 'POST' and request.FILES['file']:
        uploaded_file = request.FILES['file']
        file_path = default_storage.save(uploaded_file.name, ContentFile(uploaded_file.read()))
        absolute_file_path = default_storage.path(file_path)
        try:
            demo = save_demo(absolute_file_path)
            return HttpResponseRedirect(reverse(
                'mapstat:demo',
                kwargs={'demo_id': demo}
            ))
        except Exception:
            traceback.print_exc()
            return HttpResponseRedirect(reverse('mapstat:upload'))
        finally:
            default_storage.delete(file_path)

    return render(request, 'uploaddemo/uploaddemo.html')
