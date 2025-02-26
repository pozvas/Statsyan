"""dasd."""

from awpy import Demo, stats
import pandas as pd
from demoparser2 import DemoParser
import json


BUYTYPE = [
    {
        "name": "pistol",
        "equipment_value_from": 0,
        "equipment_value_to": 0,
        "is_pistol": 1
    },
    {
        "name": "force",
        "equipment_value_from": 1001,
        "equipment_value_to": 2000,
        "is_pistol": 0
    },
    {
        "name": "semi_buy",
        "equipment_value_from": 2001,
        "equipment_value_to": 4000,
        "is_pistol": 0
    },
    {
        "name": "eco",
        "equipment_value_from": 0,
        "equipment_value_to": 1000,
        "is_pistol": 0
    },
    {
        "name": "full_buy",
        "equipment_value_from": 4001,
        "equipment_value_to": 160000,
        "is_pistol": 0
    },
]


def _merge_many(list: list[pd.DataFrame], how='inner', on=None) -> pd.DataFrame:
    if len(list) == 0:
        return None

    result = list[0]
    for i in range(1, len(list)):
        result = pd.merge(result, list[i], on=on, how=how)

    return result


def get_max_tick(parser: DemoParser):
    return parser.parse_event('cs_win_panel_match')['tick'][0]

# УЗНАЧТЬ ЧТО БУДЕТ ЕСЛИ ЧЕЛ ЛИВНЕТ ПРИ СМЕНЕ СТОРОН (можно в напарниках)
# ЧО КАК С НАБЛЮДАТЕЛЯМИ (ХЗ ЕСТЬ ЛИ ОНИ НО НУЖНО ПОНЯТЬ)
# удалить все команды кроме 2(Т) и 3(СТ)
def get_start_info(parser: DemoParser) -> pd.DataFrame:
    df = parser.parse_event('cs_win_panel_match')
    team = parser.parse_event('player_team')
    min_tick = min(team['tick'].to_list())
    team = team[(team['tick'] == min_tick) & (team['oldteam'].isin([2, 3]))]
    team = team.rename(columns={
        'user_steamid': 'steamid'
    })

    wanted_props = [
        'team_name', 'crosshair_code',
        'rank', 'rank_if_win', 'rank_if_loss', 'rank_if_tie',
        'team_rounds_total', 'comp_rank_type', 'team_clan_name'
    ]
    team_name = parser.parse_ticks(wanted_props, ticks=df['tick'])
    team_name['steamid'] = team_name['steamid'].astype(str)
    team_name['map'] = parser.parse_header()['map_name']
    team_name = team_name.merge(team[['steamid', 'oldteam']], how='left', on=['steamid'])
    team_name['global_team_name'] = team_name.apply(lambda row: 'Team ' + str(row['oldteam'] - 1), axis=1)
    team_name['is_tie'] = team_name['team_rounds_total'].drop_duplicates().size == 1
    win_team = team_name.loc[team_name['team_rounds_total'].idxmax()]['global_team_name']
    team_name['is_win'] = team_name.apply(
        lambda row: True if not row['is_tie'] and row['global_team_name'] == win_team else False,
        axis=1
    )

    return team_name

# НЕ ДЕЛАТЬ ЗАВЯЗКУ НА КОЛИЧЕСТВЕ РАУНДОВ ХАРДКОДОМ
def get_buy_type_by_rounds(parser: DemoParser) -> pd.DataFrame:

    def get_buy_type_name(row):
        if row['total_rounds_played'] in [0, 12]:
            pistol_record = None
            for record in BUYTYPE:
                if record["is_pistol"] == 1:
                    pistol_record = record
                    break
            return pistol_record['name']

        for buy_type in BUYTYPE:
            if buy_type["equipment_value_from"] <= row['equip_value'] <= buy_type["equipment_value_to"] and buy_type["is_pistol"] == 0:
                return buy_type["name"]
        return "unknown"

    wanted_ticks = parser.parse_event("round_freeze_end")["tick"].tolist()
    df = parser.parse_ticks(["current_equip_value", "total_rounds_played", 'team_name'], ticks=wanted_ticks)
    df['steamid'] = df['steamid'].astype(str)
    start_info = get_start_info(parser)
    df = df.merge(start_info[['steamid', 'global_team_name']], how="left", on='steamid')

    group_df = (
        df.groupby(['total_rounds_played', 'team_name', 'global_team_name'])
        .agg(
            equip_value=('current_equip_value', 'mean'),
            equip_value_sum=('current_equip_value', 'sum'),)
        .reset_index()
    )
    group_df['equip_value_name'] = group_df.apply(get_buy_type_name, axis=1)

    group_df = group_df.merge(group_df, on=['total_rounds_played'], suffixes=('', '_enemy'))
    group_df = group_df[group_df['team_name'] != group_df['team_name_enemy']].reset_index(drop=True)
    return group_df


def get_rounds_count(parser: DemoParser) -> pd.DataFrame:
    round_start_ticks = parser.parse_event('round_poststart').drop_duplicates()
    round_start = parser.parse_ticks(['player_steamid', 'team_name', "total_rounds_played"], ticks=round_start_ticks['tick'])
    round_start = round_start.merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'])
    rouns_num = round_start.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name='rounds')
    rouns_num['steamid'] = rouns_num['steamid'].astype(str)
    return rouns_num


def get_adr(parser: DemoParser) -> pd.DataFrame:
    df = parser.parse_event("player_hurt", other=['total_rounds_played'])
    df = df[df['attacker_steamid'].notna()]
    ticks = parser.parse_ticks(['team_name', 'health', 'total_rounds_played'], ticks=pd.concat([df['tick'], df['tick'] - 1]))

    for idx, row in df.iterrows():
        df.loc[idx, 'attacker_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['attacker_steamid']))]['team_name'].iloc[0]
        df.loc[idx, 'user_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['user_steamid']))]['team_name'].iloc[0]
        df.loc[idx, 'was_health'] = ticks[(ticks['tick'] == row['tick'] - 1) & (ticks['steamid'] == int(row['user_steamid']))]['health'].iloc[0]

    filtred_df = df[df['user_team_name'] != df['attacker_team_name']]
    filtred_df = filtred_df.rename(columns={
        'attacker_steamid': 'steamid',
        'attacker_team_name': 'team_name'
    })

    filtred_df['damage'] = filtred_df.apply(
        lambda row: row['was_health'] if row['health'] == 0 else row['dmg_health'],
        axis=1
    )

    filtred_df = filtred_df.merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'], how='left')

    damage = filtred_df.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])['damage'].sum().reset_index(name='damage')

    return damage.fillna(0)


def calculate_trades(kills: pd.DataFrame, trade_ticks: int = 128 * 5) -> pd.DataFrame:
    rounds = kills["total_rounds_played"].unique()

    was_traded = []

    for r in rounds:
        kills_round = kills[kills["total_rounds_played"] == r]
        for _, row in kills_round.iterrows():
            kills_in_trade_window = kills_round[
                (kills_round["tick"] >= row["tick"] - trade_ticks)
                & (kills_round["tick"] <= row["tick"])
            ]
            if row["victim_steamid"] in kills_in_trade_window["attacker_steamid"].to_numpy():
                last_kill_by_attacker = None
                for __, attacker_row in kills_in_trade_window.iterrows():
                    if attacker_row["attacker_steamid"] == row["victim_steamid"]:
                        last_kill_by_attacker = attacker_row.name
                was_traded.append(last_kill_by_attacker)

    kills["was_traded"] = False
    kills.loc[was_traded, "was_traded"] = True

    return kills


def get_kast_rounds(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=["total_rounds_played"]).rename(columns={
        'user_steamid': 'victim_steamid'
    })
    ticks = parser.parse_ticks(["team_name", 'total_rounds_played'], ticks=deaths["tick"].to_list())

    def get_team_name(row, ticks, steamid_column):
        return ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row[steamid_column]))]['team_name'].iloc[0]

    deaths['attacker_team_name'] = deaths[deaths['attacker_steamid'].notna()].apply(lambda row: get_team_name(row, ticks, 'attacker_steamid'), axis=1)
    deaths['assister_team_name'] = deaths[deaths['assister_steamid'].notna()].apply(lambda row: get_team_name(row, ticks, 'assister_steamid'), axis=1)
    deaths['victim_team_name'] = deaths.apply(lambda row: get_team_name(row, ticks, 'victim_steamid'), axis=1)

    kills_with_trades = calculate_trades(deaths)

    buy_type_by_rounds = get_buy_type_by_rounds(parser)

    kills = (
        kills_with_trades[kills_with_trades['attacker_steamid'].notna()]
        .loc[:, ["attacker_team_name", "attacker_steamid", "total_rounds_played"]]
        .drop_duplicates()
        .rename(columns={"attacker_team_name": "team_name", "attacker_steamid": "steamid"})
        .reset_index(drop=True)
    ).merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])
    

    assists = (
        kills_with_trades[kills_with_trades['assister_steamid'].notna()]
        .loc[:, ["assister_team_name", "assister_steamid", "total_rounds_played"]]
        .drop_duplicates()
        .rename(columns={"assister_team_name": "team_name", "assister_steamid": "steamid"})
        .reset_index(drop=True)
    ).merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])

    trades = (
        kills_with_trades.loc[
            kills_with_trades["was_traded"],
            ["victim_team_name", "victim_steamid", "total_rounds_played"],
        ]
        .drop_duplicates()
        .rename(columns={"victim_team_name": "team_name", "victim_steamid": "steamid"})
        .reset_index(drop=True)
    ).merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])

    ticks = pd.concat(
        [parser.parse_event('round_officially_ended').drop_duplicates(),
         parser.parse_event('cs_win_panel_match')]
    )

    survive = (
        parser.parse_ticks(
            ['team_name', 'total_rounds_played', 'health'],
            ticks=ticks['tick'] -1
        )
        .rename(columns={
            'user_stemaid': 'steamid'
        })
        .reset_index(drop=True)
    )

    survive = survive[survive['health'] > 0].groupby(['steamid', 'team_name', 'total_rounds_played']).tail(1)
    survive['total_rounds_played'] = survive.apply(lambda row: row['total_rounds_played'] - 1, axis=1)
    survive = survive[['team_name', 'steamid', 'total_rounds_played',]].reset_index(drop=True)
    survive['steamid'] = survive['steamid'].astype(str)
    survive = survive.merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])

    kast = (
        pd.concat([kills, assists, trades, survive])
        .drop_duplicates()
        .reset_index(drop=True)
        .groupby(["steamid", 'team_name', 'equip_value_name', 'equip_value_name_enemy'])
        .size()
        .reset_index(name='kast_rounds')
    )

    return kast


def get_kd(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=['total_rounds_played'])
    filter_deaths = deaths[deaths['attacker_name'].notna()]
    ticks = parser.parse_ticks(["team_name"], ticks=deaths["tick"].to_list())

    def get_team_name(row, ticks, steamid_column):
        return ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row[steamid_column]))]['team_name'].iloc[0]

    filter_deaths['attacker_team_name'] = filter_deaths.apply(lambda row: get_team_name(row, ticks, 'attacker_steamid'), axis=1)
    filter_deaths['assister_team_name'] = filter_deaths[filter_deaths['assister_steamid'].notna()].apply(lambda row: get_team_name(row, ticks, 'assister_steamid'), axis=1)
    filter_deaths['user_team_name'] = filter_deaths.apply(lambda row: get_team_name(row, ticks, 'user_steamid'), axis=1)

    columns = {
        'kills': 'attacker',
        'assists': 'assister',
        'deaths': 'user'
    }
    result = None

    buy_type_by_rounds = get_buy_type_by_rounds(parser)

    for column_name, prefix in columns.items():
        df = filter_deaths.rename(columns={
            f'{prefix}_steamid': 'steamid',
            f'{prefix}_team_name': 'team_name',
        })
        df = df.merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'], how='left')
        data_sides = df.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name=column_name)

        if column_name == 'kills':
            headshots = df[df['headshot']]
            hs_sides = headshots.groupby(['steamid', 'team_name',]).size().reset_index(name='headshots')
            data_sides = data_sides.merge(hs_sides, on=['steamid', 'team_name'], how='left')

        if result is None:
            result = data_sides
        else:
            result = result.merge(data_sides, on=['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'], how='outer')

    return result.fillna(0)


def get_multykills(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=['total_rounds_played'])
    ticks = parser.parse_ticks(["team_name"], ticks=deaths["tick"].to_list())
    deaths = deaths[deaths['attacker_steamid'].notna()].rename(columns={
        'attacker_team_name': 'team_name',
        'attacker_steamid': 'steamid'
    })

    for idx, row in deaths.iterrows():
        deaths.loc[idx, 'team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['steamid']))]['team_name'].iloc[0]

    deaths = deaths.merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'])
    multykills = deaths.groupby(['team_name', 'steamid', 'total_rounds_played', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name='kills_in_round')
    result = None

    for i in range(1, 6):
        kills = multykills[multykills['kills_in_round'] == i].groupby(['team_name', 'steamid', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name=f'kills_{i}')
        if result is None:
            result = kills
        else:
            result = result.merge(kills, how='outer')

    return result.fillna(0)


def get_full_clutches_info(parser: DemoParser, is_win: bool = True) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=["total_rounds_played"])
    round_ends = parser.parse_event("round_end")
    df = parser.parse_ticks(["is_alive", "team_name", "team_rounds_total"], ticks=deaths["tick"].to_list())
    max_round = deaths["total_rounds_played"].max() + 1
    result = pd.DataFrame(columns=['steamid', 'total_rounds_played', 'against', 'team_name'])

    for round_idx in range(0, max_round):
        for _, death in deaths.iterrows():
            if death["total_rounds_played"] == round_idx:
                subdf = df[df["tick"] == death["tick"]]
                ct_alive = subdf[(subdf["team_name"] == "CT") & (subdf["is_alive"] == True)]
                t_alive = subdf[(subdf["team_name"] == "TERRORIST") & (subdf["is_alive"] == True)]

                if len(ct_alive) == 1 and len(t_alive) != 0 and round_ends.iloc[round_idx]["winner"] == ("CT" if is_win else 'T'):
                    result.loc[len(result)] = pd.Series({'steamid': ct_alive["steamid"].iloc[0].astype(str),
                                                      'total_rounds_played': round_idx,
                                                      'against': len(t_alive),
                                                     'team_name': 'CT'})
                    break

                if len(t_alive) == 1 and len(ct_alive) != 0 and round_ends.iloc[round_idx]["winner"] == ("T" if is_win else 'CT'):
                    result.loc[len(result)] = pd.Series({'steamid': t_alive["steamid"].iloc[0].astype(str),
                                                      'total_rounds_played': round_idx,
                                                      'against': len(ct_alive),
                                                     'team_name': 'TERRORIST'})
                    break
    return result


def get_clutches(parser: DemoParser) -> pd.DataFrame:
    buy_type_by_rounds = get_buy_type_by_rounds(parser)
    full_win_clutches = get_full_clutches_info(parser).merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])
    full_lose_clutches = get_full_clutches_info(parser, is_win=False).merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])
    result = None

    for i in range(1, 6):
        win_clutches = full_win_clutches[full_win_clutches['against'] == i].groupby(['steamid', 'team_name','equip_value_name', 'equip_value_name_enemy']).size().reset_index(name=f'win_clutches_1x{i}')
        lose_clutches = full_lose_clutches[full_lose_clutches['against'] == i].groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name=f'loss_clutches_1x{i}')

        tmp = lose_clutches.merge(win_clutches, how='outer', on=['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])
        if i == 1:
            result = tmp
        else:
            result = result.merge(tmp, how='outer', on=['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])

    return result.fillna(0)


def get_first_kills(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=["total_rounds_played"])
    filter_deaths = deaths[deaths['attacker_name'].notna()]
    idx = filter_deaths.groupby('total_rounds_played')['tick'].idxmin()
    firt_kills = deaths.loc[idx].reset_index(drop=True)
    df = parser.parse_ticks(["team_name"], ticks=firt_kills["tick"].to_list())

    result = pd.DataFrame(columns=['attacker_name', 'attacker_steamid', 'attacker_team_name', 'total_rounds_played', 'victim_name', 'victim_steamid', 'victim_team_name'])
    for _, kill in firt_kills.iterrows():
        attacker_team = df[(df['tick'] == kill['tick']) & (df['steamid'] == int(kill['attacker_steamid']))]['team_name'].iloc[0]
        victim_team = df[(df['tick'] == kill['tick']) & (df['steamid'] == int(kill['user_steamid']))]['team_name'].iloc[0]
        result.loc[len(result)] = pd.Series({
            'attacker_name': kill['attacker_name'],
            'attacker_steamid': kill['attacker_steamid'],
            'attacker_team_name': attacker_team,
            'total_rounds_played': kill['total_rounds_played'],
            'victim_name': kill['user_name'],
            'victim_steamid': kill['user_steamid'],
            'victim_team_name': victim_team,
        })

    return result


def get_firt_kills_count(parser: DemoParser) -> pd.DataFrame:
    first_kills = get_first_kills(parser)
    buy_type_by_rounds = get_buy_type_by_rounds(parser)

    first_kills_count_sides = (first_kills.rename(columns={
        'attacker_steamid': 'steamid',
        'attacker_team_name': 'team_name'
    })
        .merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])
        .groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])
        .size()
        .reset_index(name='first_kills')
    )

    first_deaths_count_sides = (first_kills.rename(columns={
        'victim_steamid': 'steamid',
        'victim_team_name': 'team_name'
    })
        .merge(buy_type_by_rounds, on=['total_rounds_played', 'team_name'])
        .groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])
        .size()
        .reset_index(name='first_deaths')
    )

    tmp_sides = pd.merge(first_kills_count_sides, first_deaths_count_sides, how='outer', on=['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])
    return tmp_sides.fillna(0)


def get_utility_damage(parser: DemoParser) -> pd.DataFrame:
    df = parser.parse_event("player_hurt", other=["total_rounds_played"])
    util_dmg = df[(df["weapon"] == "hegrenade") | (df["weapon"] == "molotov") | (df["weapon"] == "inferno")]
    ticks = parser.parse_ticks(['team_name', 'health'], ticks=pd.concat([df['tick'], df['tick'] - 1]))

    for idx, row in util_dmg.iterrows():
        util_dmg.loc[idx, 'attacker_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['attacker_steamid']))]['team_name'].iloc[0]
        util_dmg.loc[idx, 'user_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['user_steamid']))]['team_name'].iloc[0]
        health_value = ticks[(ticks['tick'] == row['tick'] - 1) & (ticks['steamid'] == int(row['user_steamid']))]['health']
        util_dmg.loc[idx, 'was_health'] = health_value.iloc[0] if not health_value.empty else row['dmg_health']

    util_dmg = util_dmg[util_dmg['user_team_name'] != util_dmg['attacker_team_name']]
    util_dmg = util_dmg.rename(columns={
        'attacker_steamid': 'steamid',
        'attacker_team_name': 'team_name'
    })

    util_dmg['damage'] = util_dmg.apply(
        lambda row: row['was_health'] if row['health'] == 0 else row['dmg_health'],
        axis=1
    )
    util_dmg = util_dmg.merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'])

    util_dmg_sides = util_dmg.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])['damage'].sum().reset_index(name='utility_damage')

    return util_dmg_sides.fillna(0)


def get_enemy_flashed(parser: DemoParser) -> pd.DataFrame:
    rounds_end = parser.parse_event("round_end")["tick"]
    flashes = parser.parse_ticks(['enemies_flashed_total', 'team_name', 'total_rounds_played'], ticks=rounds_end)
    flashes['steamid'] = flashes['steamid'].astype(str)

    flashes = flashes.merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'])

    enemy_flashed_sides = flashes.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy'])['enemies_flashed_total'].max().reset_index(name='enemy_flashed')

    return enemy_flashed_sides.fillna(0)[enemy_flashed_sides.fillna(0)['enemy_flashed'] != 0]


def get_flash_assists(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event('player_death', other=["total_rounds_played"])
    flash_assists = deaths[deaths['assistedflash']]
    ticks = parser.parse_ticks(['team_name'], ticks=flash_assists['tick'])
    flash_assists['assister_team_name'] = None
    for idx, row in flash_assists.iterrows():
        flash_assists.loc[idx, 'assister_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['assister_steamid']))]['team_name'].iloc[0]

    flash_assists = flash_assists.rename(columns={
        'assister_team_name': 'team_name',
        'assister_steamid': 'steamid'
    }).merge(get_buy_type_by_rounds(parser), on=['total_rounds_played', 'team_name'], how='left')

    flash_assists_sides = flash_assists.groupby(['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy']).size().reset_index(name='flash_assists')

    return flash_assists_sides


def get_kills_and_damage_by_weapon(parser: DemoParser) -> pd.DataFrame:

    def add_sides(df: pd.DataFrame, is_damage=False) -> pd.DataFrame:
        df = df[df['attacker_steamid'].notna()]
        ticks = parser.parse_ticks(['team_name', 'health'], ticks=pd.concat([df['tick'], df['tick'] - 1]))

        for idx, row in df.iterrows():
            df.loc[idx, 'attacker_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['attacker_steamid']))]['team_name'].iloc[0]
            df.loc[idx, 'user_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['user_steamid']))]['team_name'].iloc[0]
            if is_damage:
                df.loc[idx, 'was_health'] = ticks[(ticks['tick'] == row['tick'] - 1) & (ticks['steamid'] == int(row['user_steamid']))]['health'].iloc[0]

        df = df[df['user_team_name'] != df['attacker_team_name']]
        return df

    kills = add_sides(parser.parse_event('player_death'))
    kills = kills.rename(columns={
            'attacker_steamid': 'steamid',
            'attacker_team_name': 'team_name'
        })
    kills_by_weapon_and_hitgroup = (
        kills.groupby(['steamid', 'team_name', 'weapon', 'hitgroup'])
        .size()
        .reset_index(name='kills')
    )

    hits = add_sides(parser.parse_event('player_hurt'), True)
    hits = hits.rename(columns={
            'attacker_steamid': 'steamid',
            'attacker_team_name': 'team_name'
        })

    hits['damage'] = hits.apply(
        lambda row: row['was_health'] if row['health'] == 0 else row['dmg_health'],
        axis=1
    )

    hits_by_weapon_and_hitgroup = (
        hits.groupby(['steamid', 'team_name', 'weapon', 'hitgroup'])
        .agg(
            hits=('dmg_health', 'size'),
            damage_sum=('damage', 'sum'),)
        .reset_index()
    )

    return (hits_by_weapon_and_hitgroup
            .merge(kills_by_weapon_and_hitgroup,
                   how='left',
                   on=['steamid', 'team_name', 'weapon', 'hitgroup'])
            ).fillna(0)


def get_weapon_fired(parser: DemoParser) -> pd.DataFrame:
    fires = parser.parse_event('weapon_fire')
    ticks = parser.parse_ticks(['team_name'], ticks=fires['tick'])

    for idx, row in fires.iterrows():
        fires.loc[idx, 'user_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['user_steamid']))]['team_name'].iloc[0]

    fires = fires.rename(columns={
        'user_steamid': 'steamid',
        'user_team_name': 'team_name'
    })

    return (fires
            .groupby(['steamid', 'team_name', 'weapon'])
            .size()
            .reset_index(name='fires'))


def get_weapon_stat(parser: DemoParser) -> tuple[pd.DataFrame, pd.DataFrame]:
    granades_name = [
        'molotov',
        'flashbang',
        'hegrenade',
        'decoy',
        'smokegrenade',
        'incgrenade',
        'inferno'

    ]
    deaths = (
        parser
        .parse_event('player_death', other=['total_rounds_played']).rename(columns={
            'attacker_steamid': 'steamid'
        })
        [['tick', 'steamid', 'weapon', 'hitgroup', 'distance', 'user_steamid']]
    )
    deaths = deaths[deaths['steamid'].notna()]
    deaths['weapon'] = 'weapon_' + deaths['weapon']
    deaths['is_kill'] = 1

    fires = parser.parse_event('weapon_fire', other=['total_rounds_played']).rename(columns={
            'user_steamid': 'steamid'
        })[['tick', 'steamid', 'weapon']]
    fires = fires[fires['steamid'].notna()]

    hurt = parser.parse_event('player_hurt', other=['total_rounds_played']).rename(columns={
        'attacker_steamid': 'steamid'
    })[['tick', 'steamid', 'weapon', 'hitgroup', 'dmg_health', 'user_steamid', 'health']]
    hurt = hurt[hurt['steamid'].notna()]
    hurt['is_damage'] = 1

    def set_right_name(row):
        weapon_name = fires[
                (fires['tick'] == row['tick']) &
                (fires['steamid'] == row['steamid'])
            ]['weapon']

        if row['weapon'] in granades_name or weapon_name.size == 0:
            return 'weapon_' + row['weapon']

        return weapon_name.iloc[0]

    hurt['weapon'] = hurt.apply(
        lambda row: set_right_name(row),
        axis=1
    )

    all_fires = (
        fires.merge(hurt, on=['tick', 'steamid', 'weapon'], how='outer')
        .merge(
            deaths,
            on=['tick', 'steamid', 'weapon', 'user_steamid'],
            how='left',
            suffixes=['_hurt', '']
        ).fillna(0)
    )
    ticks = parser.parse_ticks(['team_name', 'health'], ticks=pd.concat([all_fires['tick'], all_fires['tick'] - 1]))

    for idx, row in all_fires.iterrows():
        all_fires.loc[idx, 'team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['steamid']))]['team_name'].iloc[0]
        if row['is_damage'] != 0:
            all_fires.loc[idx, 'user_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['user_steamid']))]['team_name'].iloc[0]
            all_fires.loc[idx, 'was_health'] = ticks[(ticks['tick'] == row['tick'] - 1) & (ticks['steamid'] == int(row['user_steamid']))]['health'].iloc[0]

    all_fires = all_fires[all_fires['user_team_name'] != all_fires['team_name']]

    group_fields = [
        'tick', 'steamid', 'weapon', 'hitgroup', 'team_name',
        'was_health', 'is_kill', 'is_damage', 'user_steamid'
    ]
    all_fires = (
        all_fires.groupby(group_fields, dropna=False)
        .agg(
            dmg_health=('dmg_health', 'sum'),
            hitgroup_hurt=('hitgroup_hurt', 'min')  # что-то придумать и поправить не макс
        ).reset_index()
    )

    all_fires['damage'] = all_fires.apply(
        lambda row: row['was_health'] if row['dmg_health'] > row['was_health'] else row['dmg_health'],
        axis=1
    )
    all_fires['hitgroup'] = all_fires.apply(
        lambda row: row['hitgroup'] if row['hitgroup'] != 0 else row['hitgroup_hurt'],
        axis=1
    )
    all_fires['weapon'] = all_fires.apply(
        lambda row: 'weapon_knife' if 'knife' in row['weapon'] else row['weapon'],
        axis=1
    )

    group_df = (
        all_fires.groupby(['steamid', 'weapon', 'hitgroup', 'team_name'])
        .agg(
            fires_count=('tick', 'size'),
            hits_count=('is_damage', lambda x: (x == 1).sum()),
            kills_count=('is_kill', lambda x: (x == 1).sum()),
            damage=('damage', 'sum')
        )
        .reset_index()
    )

    fires_all = group_df.groupby(['steamid', 'weapon', 'team_name'])['fires_count'].sum().reset_index(name='fires_count')
    hurt_only = group_df[group_df['hitgroup'] != 0]
    return (fires_all, hurt_only)


def get_duels(parser: DemoParser) -> pd.DataFrame:
    first_kills = get_first_kills(parser)
    deaths = parser.parse_event('player_death')
    duels = deaths.groupby(['attacker_steamid', 'user_steamid']).size().reset_index(name='duels').rename(columns={
        'user_steamid': 'victim_steamid'
    })
    first_kills_duels = first_kills.groupby(['attacker_steamid', 'victim_steamid']).size().reset_index(name='open_duels')
    awp_duels = deaths[deaths['weapon'] == 'awp'].groupby(['attacker_steamid', 'user_steamid']).size().reset_index(name='awp_duels').rename(columns={
        'user_steamid': 'victim_steamid'
    })
    return _merge_many([duels, first_kills_duels, awp_duels], how='left').fillna(0)


def get_rounds(parser: DemoParser) -> pd.DataFrame:
    round_end = parser.parse_event('round_officially_ended').drop_duplicates()
    round_end['tick'] = round_end['tick'] - 1
    ticks_end = pd.concat(
            [
                round_end,
                parser.parse_event('cs_win_panel_match')
            ]
        )
    end = parser.parse_ticks(['round_win_reason', 'total_rounds_played'], ticks=ticks_end['tick'])[['round_win_reason', 'total_rounds_played']].drop_duplicates()

    buy_type = get_buy_type_by_rounds(parser)[[
        'total_rounds_played', 'team_name',
        'equip_value_name', 'equip_value', 'equip_value_sum',
        'global_team_name'
        ]]
    buy_type['total_rounds_played'] = buy_type['total_rounds_played'] + 1

    return end.merge(
        buy_type[buy_type['team_name'] == 'CT'][[
            'total_rounds_played', 'equip_value_name',
            'equip_value', 'equip_value_sum', 'global_team_name'
            ]],
        on=['total_rounds_played'],
        how='left',
    ).merge(
        buy_type[buy_type['team_name'] == 'TERRORIST'][[
            'total_rounds_played', 'equip_value_name',
            'equip_value', 'equip_value_sum', 'global_team_name'
            ]],
        on=['total_rounds_played'],
        how='left',
        suffixes=['_ct', '_t']
    )


def get_kills_in_round(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event('player_death', other=['total_rounds_played', "game_time", "round_start_time"]).rename(columns={
        'user_steamid': 'victim_steamid',
        'headshot': 'is_headshot',
        'noscope': 'is_no_scope',
        'penetrated': 'is_penetrated',
        'thrusmoke': 'is_smoke',
        'attackerinair': 'is_in_air',
        'attackerblind': 'is_blind',
        'total_rounds_played': 'round'
    })
    deaths = deaths[deaths['attacker_steamid'].notna()]
    ticks = parser.parse_ticks(["team_name"], ticks=deaths["tick"].to_list())

    def get_team_name(row, ticks, steamid_column):
        return ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row[steamid_column]))]['team_name'].iloc[0]

    deaths['attacker_team_name'] = deaths[deaths['attacker_steamid'].notna()].apply(lambda row: get_team_name(row, ticks, 'attacker_steamid'), axis=1)
    deaths['assister_team_name'] = deaths[deaths['assister_steamid'].notna()].apply(lambda row: get_team_name(row, ticks, 'assister_steamid'), axis=1)
    deaths['victim_team_name'] = deaths.apply(lambda row: get_team_name(row, ticks, 'victim_steamid'), axis=1)
    deaths['weapon'] = 'weapon_' + deaths['weapon']
    deaths['round'] = deaths['round'] + 1
    deaths['kill_time'] = deaths["game_time"] - deaths["round_start_time"]
    deaths['is_penetrated'] = deaths['is_penetrated'] > 0

    return deaths[
        ['attacker_steamid', 'attacker_team_name',
         'assister_steamid', 'assister_team_name',
         'victim_steamid', 'victim_team_name',
         'weapon', 'tick', 'is_headshot',
         'is_no_scope', 'is_penetrated',
         'is_smoke', 'is_in_air',
         'is_blind', 'round', 'kill_time']
    ]




parser = DemoParser(r'C:\Projects\Python\diplom\csstats_backend\csstats\files\allweapon.dem')

# print(get_start_info(parser).loc[0])


def watch_demo(parser: DemoParser = DemoParser(r'C:\Projects\Python\diplom\csstats_backend\csstats\files\spirit-vs-faze-m1-nuke.dem')) -> pd.DataFrame:
    end = parser.parse_event('round_officially_ended')['tick'][0]
    start = parser.parse_event('round_freeze_end')['tick'][0]
    ticks = list(range(start, end, 8))
    df = parser.parse_ticks(['X', 'Y', 'Z'], ticks=ticks)
    result = []
    for tick, group in df.groupby('tick'):
        players = []
        for _, row in group.iterrows():
            player = {
                'X': row['X'],
                'Y': row['Y'],
                'Z': row['Z'],
                'name': row['name'],
                'steamid': row['steamid']
            }
            players.append(player)
        result.append(players)

    # Преобразование в JSON
    json_result = json.dumps(result, indent=4)
    return result



#print(watch_demo(parser))    


def get_stats(parser: DemoParser):
    """das."""
    scoreboard = []
    scoreboard.append(get_rounds_count(parser))
    scoreboard.append(get_kd(parser))
    scoreboard.append(get_clutches(parser))
    scoreboard.append(get_firt_kills_count(parser))
    scoreboard.append(get_enemy_flashed(parser))
    scoreboard.append(get_utility_damage(parser))
    scoreboard.append(get_flash_assists(parser))
    scoreboard.append(get_adr(parser))
    scoreboard.append(get_kast_rounds(parser))
    scoreboard.append(get_multykills(parser))

    result = _merge_many(scoreboard, how='left', on=['steamid', 'team_name', 'equip_value_name', 'equip_value_name_enemy']).fillna(0)
    result = result.merge(get_start_info(parser)[['steamid', 'global_team_name']], how='left', on=['steamid'])

    return result


# print(get_stats(parser).groupby('steamid')['rounds'].sum().reset_index())



#print(get_multykills(parser))
# print(get_multykills(parser).loc[0])