"""dasd."""

from awpy import Demo, stats
import pandas as pd
from demoparser2 import DemoParser
import json


def _merge_many(list: list[pd.DataFrame], how='inner', on=None) -> pd.DataFrame:
    if len(list) == 0:
        return None

    result = list[0]
    for i in range(1, len(list)):
        result = pd.merge(result, list[i], on=on, how=how)

    return result


def get_start_info(parser: DemoParser) -> pd.DataFrame:
    df = parser.parse_event('round_announce_match_start')
    team_name = parser.parse_ticks(['team_name'], ticks=df['tick'])
    team_name['steamid'] = team_name['steamid'].astype(str)
    team_name['global_team_name'] = team_name.apply(lambda row: 'Team 1' if row['team_name'] == 'CT' else 'Team 2', axis=1)
    return team_name


def get_kd(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death")
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

    for column_name, prefix in columns.items():
        df = filter_deaths.rename(columns={
            f'{prefix}_steamid': 'steamid',
            f'{prefix}_team_name': 'team_name',
        })
        data_sides = df.groupby(['steamid', 'team_name',]).size().reset_index(name=column_name)
        data_all = df.groupby(['steamid',]).size().reset_index(name=column_name)
        data_all['team_name'] = 'all'

        combined_data = pd.concat([data_all, data_sides], ignore_index=True)

        if result is None:
            result = combined_data
        else:
            result = result.merge(combined_data, on=['steamid', 'team_name'], how='outer')

    return result.fillna(0)


def get_full_clutches_info(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event("player_death", other=["total_rounds_played"])
    round_ends = parser.parse_event("round_end")
    df = parser.parse_ticks(["is_alive", "team_name", "team_rounds_total"], ticks=deaths["tick"].to_list())
    max_round = deaths["total_rounds_played"].max() + 1
    result = pd.DataFrame(columns=['steamid', 'round', 'against', 'team_name'])

    for round_idx in range(0, max_round):
        for _, death in deaths.iterrows():
            if death["total_rounds_played"] == round_idx:
                subdf = df[df["tick"] == death["tick"]]
                ct_alive = subdf[(subdf["team_name"] == "CT") & (subdf["is_alive"] == True)]
                t_alive = subdf[(subdf["team_name"] == "TERRORIST") & (subdf["is_alive"] == True)]

                if len(ct_alive) == 1 and len(t_alive) != 0 and round_ends.iloc[round_idx]["winner"] == "CT":
                    result.loc[len(result)] = pd.Series({'steamid': ct_alive["steamid"].iloc[0].astype(str),
                                                      'round': round_idx + 1,
                                                      'against': len(t_alive),
                                                     'team_name': 'CT'})
                    break

                if len(t_alive) == 1 and len(ct_alive) != 0 and round_ends.iloc[round_idx]["winner"] == "T":
                    result.loc[len(result)] = pd.Series({'steamid': t_alive["steamid"].iloc[0].astype(str),
                                                      'round': round_idx + 1,
                                                      'against': len(ct_alive),
                                                     'team_name': 'TERRORIST'})
                    break
    return result


def get_clutches(parser: DemoParser) -> pd.DataFrame:
    full_clutches = get_full_clutches_info(parser)
    # T and CT
    total_clutches = full_clutches.groupby(['steamid', 'team_name']).size().reset_index(name='total_clutches')
    clutches_1x1 = full_clutches[full_clutches['against'] == 1].groupby(['steamid', 'team_name']).size().reset_index(name='clutches_1x1')
    clutches_1x2 = full_clutches[full_clutches['against'] == 2].groupby(['steamid', 'team_name']).size().reset_index(name='clutches_1x2')
    clutches_1x3 = full_clutches[full_clutches['against'] == 3].groupby(['steamid', 'team_name']).size().reset_index(name='clutches_1x3')
    clutches_1x4 = full_clutches[full_clutches['against'] == 4].groupby(['steamid', 'team_name']).size().reset_index(name='clutches_1x4')
    clutches_1x5 = full_clutches[full_clutches['against'] == 5].groupby(['steamid', 'team_name']).size().reset_index(name='clutches_1x5')
    result_sides = _merge_many([total_clutches, clutches_1x1, clutches_1x2, clutches_1x3, clutches_1x4, clutches_1x5], how='left', on=['steamid', 'team_name']).fillna(0)

    # All sides
    total_clutches = full_clutches.groupby(['steamid']).size().reset_index(name='total_clutches')
    clutches_1x1 = full_clutches[full_clutches['against'] == 1].groupby(['steamid']).size().reset_index(name='clutches_1x1')
    clutches_1x2 = full_clutches[full_clutches['against'] == 2].groupby(['steamid']).size().reset_index(name='clutches_1x2')
    clutches_1x3 = full_clutches[full_clutches['against'] == 3].groupby(['steamid']).size().reset_index(name='clutches_1x3')
    clutches_1x4 = full_clutches[full_clutches['against'] == 4].groupby(['steamid']).size().reset_index(name='clutches_1x4')
    clutches_1x5 = full_clutches[full_clutches['against'] == 5].groupby(['steamid']).size().reset_index(name='clutches_1x5')
    result_all = _merge_many([total_clutches, clutches_1x1, clutches_1x2, clutches_1x3, clutches_1x4, clutches_1x5], how='left', on=['steamid']).fillna(0)
    result_all['team_name'] = 'all'

    return pd.concat([result_all, result_sides])


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
    # All sides
    first_kills_count = first_kills.groupby(['attacker_steamid']).size().reset_index(name='first_kills').rename(columns={
        'attacker_steamid': 'steamid',
        'attacker_team_name': 'team_name'
    })
    first_kills_count['team_name'] = 'all'

    first_deaths_count = first_kills.groupby(['victim_steamid']).size().reset_index(name='first_deaths').rename(columns={
        'victim_steamid': 'steamid',
        'victim_team_name': 'team_name'
    })
    first_deaths_count['team_name'] = 'all'

    # Sides
    first_kills_count_sides = first_kills.groupby(['attacker_steamid', 'attacker_team_name']).size().reset_index(name='first_kills').rename(columns={
        'attacker_steamid': 'steamid',
        'attacker_team_name': 'team_name'
    })
    first_deaths_count_sides = first_kills.groupby(['victim_steamid', 'victim_team_name']).size().reset_index(name='first_deaths').rename(columns={
        'victim_steamid': 'steamid',
        'victim_team_name': 'team_name'
    })

    tmp = pd.merge(first_kills_count, first_deaths_count, how='outer', on=['steamid', 'team_name'])
    tmp_sides = pd.merge(first_kills_count_sides, first_deaths_count_sides, how='outer', on=['steamid', 'team_name'])
    return pd.concat([tmp, tmp_sides]).reset_index(drop=True).fillna(0)


def get_utility_damage(parser: DemoParser) -> pd.DataFrame:
    df = parser.parse_event("player_hurt")
    util_dmg = df[(df["weapon"] == "hegrenade") | (df["weapon"] == "molotov") | (df["weapon"] == "inferno")]
    ticks = parser.parse_ticks(['team_name'], ticks=util_dmg['tick'])

    for idx, row in util_dmg.iterrows():
        util_dmg.loc[idx, 'team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['attacker_steamid']))]['team_name'].iloc[0]
    util_dmg = util_dmg.rename(columns={'attacker_steamid': 'steamid'})

    util_dmg_sides = util_dmg.groupby(['steamid', 'team_name'])['dmg_health'].sum().reset_index(name='utility_damage')
    util_dmg_all = util_dmg.groupby(['steamid'])['dmg_health'].sum().reset_index(name='utility_damage')
    util_dmg_all['team_name'] = 'all'

    return pd.concat([util_dmg_sides, util_dmg_all]).fillna(0)


def get_enemy_flashed(parser: DemoParser) -> pd.DataFrame:
    rounds_end = parser.parse_event("round_end")["tick"]
    flashes = parser.parse_ticks(['enemies_flashed_total', 'team_name', 'total_rounds_played'], ticks=rounds_end)
    flashes['steamid'] = flashes['steamid'].astype(str)

    enemy_flashed_sides = flashes.groupby(['steamid', 'team_name'])['enemies_flashed_total'].max().reset_index(name='enemy_flashed')
    enemy_flashed = flashes.groupby(['steamid'])['enemies_flashed_total'].max().reset_index(name='enemy_flashed')
    enemy_flashed['team_name'] = 'all'

    return pd.concat([enemy_flashed, enemy_flashed_sides]).fillna(0)


def get_flash_assists(parser: DemoParser) -> pd.DataFrame:
    deaths = parser.parse_event('player_death')
    flash_assists = deaths[deaths['assistedflash']]
    ticks = parser.parse_ticks(['team_name'], ticks=flash_assists['tick'])
    for idx, row in flash_assists.iterrows():
        flash_assists.loc[idx, 'assister_team_name'] = ticks[(ticks['tick'] == row['tick']) & (ticks['steamid'] == int(row['assister_steamid']))]['team_name'].iloc[0]

    flash_assists_sides = flash_assists.groupby(['assister_steamid', 'assister_team_name']).size().reset_index(name='flash_assists')
    flash_assists_all = flash_assists_sides.groupby(['assister_steamid']).size().reset_index(name='flash_assists')
    flash_assists_all['assister_team_name'] = 'all'

    return pd.concat([flash_assists_sides, flash_assists_all]).rename(columns={
        'assister_team_name': 'team_name',
        'assister_steamid': 'steamid'
    })


# csstats\files\natus-vincere-vs-imperial-nuke.dem
parser = DemoParser(r'C:\Projects\Python\diplom\csstats_backend\csstats\files\spirit-vs-faze-m1-nuke.dem')
parser2 = DemoParser(r'C:\Projects\Python\diplom\csstats_backend\csstats\files\match730_003729204860554314148_1540754158_187.dem')

print(parser2.parse_header())

#print(parser.parse_event('round_announce_match_start'))

def get_stats(path: str):
    """das."""
    demo = Demo(path)
    scoreboard = []
    scoreboard.append(stats.adr(demo, team_dmg=True))
    scoreboard.append(stats.kast(demo))
    scoreboard.append(stats.rating(demo))
    scoreboard.append(stats.impact(demo))

    parser = DemoParser(path)
    scoreboard.append(get_kd(parser))
    scoreboard.append(get_clutches(parser))
    scoreboard.append(get_firt_kills_count(parser))
    scoreboard.append(get_enemy_flashed(parser))
    scoreboard.append(get_utility_damage(parser))
    scoreboard.append(get_flash_assists(parser))

    result = _merge_many(scoreboard, how='left').fillna(0)
    result = result.merge(get_start_info(parser)[['steamid', 'global_team_name']], how='left', on=['steamid'])

    return result


#print(get_stats(r'C:\Projects\Python\diplom\csstats_backend\csstats\files\natus-vincere-vs-imperial-nuke.dem').columns)

