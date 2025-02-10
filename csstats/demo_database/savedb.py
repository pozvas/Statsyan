from pandas import DataFrame
from demoparser2 import DemoParser
from demoparser.demoparser import get_duels, get_start_info, get_max_tick, get_stats, get_weapon_stat
from .models import Player, Demo, ScoreBoard, Duels, Map, MatchType, PlayerInDemo, MMRank, Side, BuyType, Weapon, PlayerWeaponStat, PlayerHitgroupStat, HitGroup
from hashlib import sha256
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction


def save_stats(df: DataFrame):
    demo = Demo()
    demo.save()
    for _, row in df.iterrows():
        player, created = Player.objects.get_or_create(steamid=row['steamid'])

        scoreboard = ScoreBoard(
            player_id=player,
            demo_id=demo,
            side=row['team_name'],
            team=row['global_team_name'],
            kills=row['kills'],
            assists=row['assists'],
            deaths=row['deaths'],
            adr=row['adr'],
            kast=row['kast'],
            impact=row['impact'],
            rating=row['rating'],
            clutches_1x1=row['clutches_1x1'],
            clutches_1x2=row['clutches_1x2'],
            clutches_1x3=row['clutches_1x3'],
            clutches_1x4=row['clutches_1x4'],
            clutches_1x5=row['clutches_1x5'],
            first_kills=row['first_kills'],
            first_deaths=row['first_deaths'],
            utility_damage=row['utility_damage'],
            enemy_flashed=row['enemy_flashed'],
            flash_assists=row['flash_assists']
        )
        scoreboard.save()
    
    return demo.pk


def save_demo(path: str):
    parser = DemoParser(path)
    info = get_start_info(parser)

    list_data = [
        info['map'].drop_duplicates()[0],
        ','.join(info['steamid'].drop_duplicates().tolist()),
        str(get_max_tick(parser))
    ]
    string = '|'.join(list_data)

    hash_id = sha256(string.encode()).hexdigest()

    demo = Demo.objects.filter(hash_id=hash_id).first()

    if demo is not None:
        return demo.pk

    # try:
    map = Map.objects.get(name=list_data[0])
    match_type = MatchType.objects.get(code=info['comp_rank_type'][0])

    is_tie = info['is_tie'][0]
    duels = get_duels(parser)
    scoreboard = get_stats(parser)
    (weapon_fires, weapon_hurt) = get_weapon_stat(parser)

    with transaction.atomic():
        demo = Demo.objects.create(
            hash_id=hash_id,
            win_team=None if is_tie else info[info['is_win']].reset_index(drop=True).loc[0, 'global_team_name'],
            score_win=info[(info['is_win']) | (info['is_tie'])].reset_index(drop=True).loc[0, 'team_rounds_total'],
            score_lose=info[~(info['is_win']) | (info['is_tie'])].reset_index(drop=True).loc[0, 'team_rounds_total'],
            map_id=map,
            match_type_id=match_type
        )

        for _, row in info.iterrows():
            player, _ = Player.objects.get_or_create(steamid=row['steamid'])
            rank = None if match_type.is_elo else MMRank.objects.get(code=row['rank'])
            new_elo = row['rank_if_win'] if row['is_win'] else row['rank_if_tie'] if row['is_tie'] else row['rank_if_loss']
            player_in_demo = PlayerInDemo.objects.create(
                player_id=player,
                demo_id=demo,
                team=row['global_team_name'],
                crosshair_code=row['crosshair_code'],
                elo_old=row['rank'] if match_type.is_elo else None,
                elo_new=new_elo if match_type.is_elo else None,
                rang_id=rank
            )

            for _, row2 in scoreboard[scoreboard['steamid'] == player.steamid].iterrows():
                side = Side.objects.get(name=row2['team_name'])
                buy_type = BuyType.objects.get(name=row2['equip_value_name'])
                buy_type_enemy = BuyType.objects.get(name=row2['equip_value_name_enemy'])
                impact = (2.13 * row2['kills'] + 0.42 * row2['assists']) / row2['rounds'] - 0.41
                rating = (
                    (0.73 * row2['kast_rounds'] + 0.3591 * row2['kills']
                        - 0.5329 * row2['deaths'] + 0.0032 * row2['damage'])
                    / row2['rounds'] + 0.2372 * impact + 0.1587)

                ScoreBoard.objects.create(
                    player_in_demo_id=player_in_demo,
                    side_id=side,
                    buy_type_id=buy_type,
                    enemy_buy_type_id=buy_type_enemy,
                    rounds=row2['rounds'],
                    kills=row2['kills'],
                    assists=row2['assists'],
                    deaths=row2['deaths'],
                    damage=row2['damage'],
                    kast_rounds=row2['kast_rounds'],
                    win_clutches_1x1=row2['win_clutches_1x1'],
                    win_clutches_1x2=row2['win_clutches_1x2'],
                    win_clutches_1x3=row2['win_clutches_1x3'],
                    win_clutches_1x4=row2['win_clutches_1x4'],
                    win_clutches_1x5=row2['win_clutches_1x5'],
                    loss_clutches_1x1=row2['loss_clutches_1x1'],
                    loss_clutches_1x2=row2['loss_clutches_1x2'],
                    loss_clutches_1x3=row2['loss_clutches_1x3'],
                    loss_clutches_1x4=row2['loss_clutches_1x4'],
                    loss_clutches_1x5=row2['loss_clutches_1x5'],
                    kills_1=row2['kills_1'],
                    kills_2=row2['kills_2'],
                    kills_3=row2['kills_3'],
                    kills_4=row2['kills_4'],
                    kills_5=row2['kills_5'],
                    first_kills=row2['first_kills'],
                    first_deaths=row2['first_deaths'],
                    utility_damage=row2['utility_damage'],
                    enemy_flashed=row2['enemy_flashed'],
                    flash_assists=row2['flash_assists'],
                    impact=impact,
                    rating=rating,
                )

        for _, row in duels.iterrows():
            attacker, _ = Player.objects.get_or_create(steamid=row['attacker_steamid'])
            victim, _ = Player.objects.get_or_create(steamid=row['victim_steamid'])
            Duels.objects.create(
                demo_id=demo,
                attacker_player_id=attacker,
                victim_player_id=victim,
                kills=row['duels'],
                open_kills=row['open_duels']
            )

        for _, row in weapon_fires.iterrows():
            player, _ = Player.objects.get_or_create(steamid=row['steamid'])
            side = Side.objects.get(name=row['team_name'])
            print(row['weapon'])
            weapon = Weapon.objects.get(name=row['weapon'])
            weapon_stat = PlayerWeaponStat.objects.create(
                demo_id=demo,
                player_id=player,
                side_id=side,
                weapon_id=weapon,
                fires_count=row['fires_count']
            )
            for _, row2 in weapon_hurt[
                (weapon_hurt['weapon'] == weapon.name) &
                (weapon_hurt['team_name'] == side.name) &
                (weapon_hurt['steamid'] == player.steamid)
            ].iterrows():
                hit_group = HitGroup.objects.get(name=row2['hitgroup'])
                PlayerHitgroupStat.objects.create(
                    player_weapon_stat_id=weapon_stat,
                    hit_group_id=hit_group,
                    damage=row2['damage'],
                    hits=row2['hits_count'],
                    kills=row2['kills_count']
                )

        return demo.pk

    # except ObjectDoesNotExist:
    #     return None
