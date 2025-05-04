from pathlib import Path
from pandas import DataFrame
from demoparser2 import DemoParser
from demoparser.demoparser import (
    get_duels,
    get_start_info,
    get_max_tick,
    get_stats,
    get_weapon_stat,
    get_rounds,
    get_kills_in_round,
)
from .models import (
    Player,
    Demo,
    ScoreBoard,
    Duels,
    Map,
    MatchType,
    PlayerInDemo,
    MMRank,
    Side,
    BuyType,
    Weapon,
    PlayerWeaponStat,
    PlayerHitgroupStat,
    HitGroup,
    Round,
    WinReason,
    KillsInRound,
)
from hashlib import sha256
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from steam.steamapi import get_players_names_and_avatars
from datetime import datetime
from django.utils import timezone


def update_players_info(steamids=None):
    if steamids is None:
        steamids = Player.objects.values_list("pk", flat=True)

    players_data = get_players_names_and_avatars(steamids)
    for player_data in players_data:
        with transaction.atomic():
            player = Player.objects.get(pk=player_data["steamid"])
            player.last_avatar = player_data["avatar"]
            player.last_nickname = player_data["personaname"]
            player.save()


def save_demo(path: str, match_time: datetime | None = None):
    parser = DemoParser(path)
    info = get_start_info(parser)

    list_data = [
        info["map"].drop_duplicates()[0],
        ",".join(info["steamid"].drop_duplicates().tolist()),
        str(get_max_tick(parser)),
    ]
    string = "|".join(list_data)

    hash = sha256(string.encode()).hexdigest()

    demo = Demo.objects.filter(hash=hash).first()

    if demo is not None:
        del parser
        return demo.pk

    # try:
    map = Map.objects.get(name=list_data[0])
    match_type = MatchType.objects.get(code=info["comp_rank_type"][0])

    if match_time is None:
        file_path = Path(path)
        match_time = datetime.fromtimestamp(file_path.stat().st_mtime)

    match_time = timezone.make_aware(match_time)

    is_tie = info["is_tie"][0]
    duels = get_duels(parser)
    scoreboard = get_stats(parser)
    (weapon_fires, weapon_hurt) = get_weapon_stat(parser)
    rounds = get_rounds(parser)
    kills_in_round = get_kills_in_round(parser)
    del parser

    with transaction.atomic():
        demo = Demo.objects.create(
            hash=hash,
            win_team=(
                None
                if is_tie
                else info[info["is_win"]]["global_team_name"].max()
            ),
            score_win=info[(info["is_win"]) | (info["is_tie"])][
                "team_rounds_total"
            ].max(),
            score_lose=info[~(info["is_win"]) | (info["is_tie"])][
                "team_rounds_total"
            ].max(),
            map=map,
            match_type=match_type,
            data_played=match_time,
        )

        for _, row in info.iterrows():
            player, _ = Player.objects.get_or_create(steamid=row["steamid"])
            rank = (
                None
                if match_type.is_elo
                else MMRank.objects.get(code=row["rank"])
            )
            new_elo = (
                row["rank_if_win"]
                if row["is_win"]
                else (
                    row["rank_if_tie"]
                    if row["is_tie"]
                    else row["rank_if_loss"]
                )
            )
            player_in_demo = PlayerInDemo.objects.create(
                player=player,
                demo=demo,
                team=row["global_team_name"],
                crosshair_code=row["crosshair_code"],
                elo_old=row["rank"] if match_type.is_elo else None,
                elo_new=new_elo if match_type.is_elo else None,
                rang=rank,
            )

            for _, row2 in scoreboard[
                scoreboard["steamid"] == player.steamid
            ].iterrows():
                side = Side.objects.get(code=row2["team_name"])
                buy_type = BuyType.objects.get(code=row2["equip_value_name"])
                buy_type_enemy = BuyType.objects.get(
                    code=row2["equip_value_name_enemy"]
                )
                impact = (
                    2.13 * row2["kills"] + 0.42 * row2["assists"]
                ) / row2["rounds"] - 0.41
                rating = (
                    (
                        0.73 * row2["kast_rounds"]
                        + 0.3591 * row2["kills"]
                        - 0.5329 * row2["deaths"]
                        + 0.0032 * row2["damage"]
                    )
                    / row2["rounds"]
                    + 0.2372 * impact
                    + 0.1587
                )

                ScoreBoard.objects.create(
                    player_in_demo=player_in_demo,
                    side=side,
                    buy_type=buy_type,
                    enemy_buy_type=buy_type_enemy,
                    rounds=row2["rounds"],
                    kills=row2["kills"],
                    assists=row2["assists"],
                    deaths=row2["deaths"],
                    damage=row2["damage"],
                    kast_rounds=row2["kast_rounds"],
                    win_clutches_1x1=row2["win_clutches_1x1"],
                    win_clutches_1x2=row2["win_clutches_1x2"],
                    win_clutches_1x3=row2["win_clutches_1x3"],
                    win_clutches_1x4=row2["win_clutches_1x4"],
                    win_clutches_1x5=row2["win_clutches_1x5"],
                    loss_clutches_1x1=row2["loss_clutches_1x1"],
                    loss_clutches_1x2=row2["loss_clutches_1x2"],
                    loss_clutches_1x3=row2["loss_clutches_1x3"],
                    loss_clutches_1x4=row2["loss_clutches_1x4"],
                    loss_clutches_1x5=row2["loss_clutches_1x5"],
                    kills_1=row2["kills_1"],
                    kills_2=row2["kills_2"],
                    kills_3=row2["kills_3"],
                    kills_4=row2["kills_4"],
                    kills_5=row2["kills_5"],
                    first_kills=row2["first_kills"],
                    first_deaths=row2["first_deaths"],
                    utility_damage=row2["utility_damage"],
                    enemy_flashed=row2["enemy_flashed"],
                    flash_assists=row2["flash_assists"],
                    impact=impact,
                    rating=rating,
                )

        for _, row in duels.iterrows():
            attacker, _ = Player.objects.get_or_create(
                steamid=row["attacker_steamid"]
            )
            victim, _ = Player.objects.get_or_create(
                steamid=row["victim_steamid"]
            )
            Duels.objects.create(
                demo=demo,
                attacker_player=attacker,
                victim_player=victim,
                kills=row["duels"],
                open_kills=row["open_duels"],
            )

        for _, row in weapon_fires.iterrows():
            player, _ = Player.objects.get_or_create(steamid=row["steamid"])
            side = Side.objects.get(code=row["team_name"])
            weapon = Weapon.objects.filter(name=row["weapon"]).first()
            if weapon is None:
                weapon = Weapon.objects.get(name="weapon_knife")
            weapon_stat = PlayerWeaponStat.objects.create(
                demo=demo,
                player=player,
                side=side,
                weapon=weapon,
                fires_count=row["fires_count"],
            )
            for _, row2 in weapon_hurt[
                (weapon_hurt["weapon"] == weapon.name)
                & (weapon_hurt["team_name"] == side.name)
                & (weapon_hurt["steamid"] == player.steamid)
            ].iterrows():
                hit_group = HitGroup.objects.get(name=row2["hitgroup"])
                PlayerHitgroupStat.objects.create(
                    player_weapon_stat=weapon_stat,
                    hit_group=hit_group,
                    damage=row2["damage"],
                    hits=row2["hits_count"],
                    kills=row2["kills_count"],
                )

        for _, row in rounds.iterrows():
            buy_type_t = BuyType.objects.get(code=row["equip_value_name_t"])
            buy_type_ct = BuyType.objects.get(code=row["equip_value_name_ct"])
            win_reason = WinReason.objects.get(code=row["round_win_reason"])
            round = Round.objects.create(
                demo=demo,
                round_number=row["total_rounds_played"],
                win_reason=win_reason,
                win_team_name=(
                    row["global_team_name_ct"]
                    if win_reason.win_side.code == "CT"
                    else row["global_team_name_t"]
                ),
                ct_buy_type=buy_type_ct,
                ct_buy_sum=row["equip_value_sum_ct"],
                ct_buy_avg_sum=row["equip_value_ct"],
                ct_team_name=row["global_team_name_ct"],
                t_buy_type=buy_type_t,
                t_buy_sum=row["equip_value_sum_t"],
                t_buy_avg_sum=row["equip_value_t"],
                t_team_name=row["global_team_name_t"],
            )
            for _, row2 in kills_in_round[
                kills_in_round["round"] == row["total_rounds_played"]
            ].iterrows():
                attacker = Player.objects.filter(
                    steamid=row2["attacker_steamid"]
                ).first()
                attacker_side = Side.objects.filter(
                    code=row2["attacker_team_name"]
                ).first()
                assister = Player.objects.filter(
                    steamid=row2["assister_steamid"]
                ).first()
                assister_side = Side.objects.filter(
                    code=row2["assister_team_name"]
                ).first()
                victim = Player.objects.get(steamid=row2["victim_steamid"])
                victim_side = Side.objects.get(code=row2["victim_team_name"])
                weapon = Weapon.objects.filter(name=row2["weapon"]).first()
                if weapon is None:
                    weapon = Weapon.objects.get(name="weapon_knife")
                KillsInRound.objects.create(
                    round=round,
                    attacker=attacker,
                    attacker_side=attacker_side,
                    assister=assister,
                    assister_side=assister_side,
                    victim=victim,
                    victim_side=victim_side,
                    weapon=weapon,
                    is_headshot=row2["is_headshot"],
                    is_penetrated=row2["is_penetrated"],
                    is_in_air=row2["is_in_air"],
                    is_blind=row2["is_blind"],
                    is_smoke=row2["is_smoke"],
                    is_no_scope=row2["is_no_scope"],
                    tick=row2["tick"],
                    kill_time=row2["kill_time"],
                )

        update_players_info()
        return demo.pk

    # except ObjectDoesNotExist:
    #     return None
