"""dasd."""

from awpy import Demo, stats
import pandas as pd


def _get_kd(demo: Demo) -> pd.DataFrame:

    columns = {
        'kills': 'attacker',
        'assists': 'assister',
        'deaths': 'victim'
    }
    result = None

    for column_name, prefix in columns.items():
        df = demo.kills.rename(columns={
            f'{prefix}_steamid': 'steamid',
            f'{prefix}_team_name': 'team_name',
            f'{prefix}_name': 'name',
        })
        data_sides = df.groupby(['steamid', 'team_name', 'name',]).size().reset_index(name=column_name)
        data_all = df.groupby(['steamid', 'name',]).size().reset_index(name=column_name)
        data_all['team_name'] = 'all'

        combined_data = pd.concat([data_all, data_sides], ignore_index=True)

        if result is None:
            result = combined_data
        else:
            result = result.merge(combined_data, on=['steamid', 'team_name', 'name'], how='outer')

    return result.fillna(0)


def get_stats(path: str):
    """das."""
    demo = Demo(path)
    adr = stats.adr(demo, team_dmg=True)
    kast = stats.kast(demo)
    rating = stats.rating(demo)
    impact = stats.impact(demo)
    kd = _get_kd(demo)

    json = adr.merge(kast, how='left').merge(rating, how='left').merge(impact, how='left').merge(kd, how='left').to_json(orient='records')
    return json
