from pandas import DataFrame
from .models import Player, Demo, ScoreBoard


def save_stats(df: DataFrame):
    demo = Demo()
    demo.save()
    for _, row in df.iterrows():
        player, created = Player.objects.get_or_create(steamid=row['steamid'])

        scoreboard = ScoreBoard(
            steamid=player,
            demo=demo,
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
