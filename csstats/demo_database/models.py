from django.db import models


class Player(models.Model):
    steamid = models.CharField(primary_key=True, max_length=20)
    auth_code = models.CharField(max_length=50, null=True, blank=True)


class Demo(models.Model):
    token = models.CharField(max_length=50, null=True, blank=True)
    data_played = models.DateTimeField(null=True, blank=True)


class ScoreBoard(models.Model):
    steamid = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    demo = models.ForeignKey(Demo, on_delete=models.DO_NOTHING)

    side = models.CharField(max_length=10)
    team = models.CharField(max_length=20)

    kills = models.SmallIntegerField()
    assists = models.SmallIntegerField()
    deaths = models.SmallIntegerField()

    adr = models.FloatField()
    kast = models.FloatField()
    impact = models.FloatField()
    rating = models.FloatField()

    clutches_1x1 = models.SmallIntegerField()
    clutches_1x2 = models.SmallIntegerField()
    clutches_1x3 = models.SmallIntegerField()
    clutches_1x4 = models.SmallIntegerField()
    clutches_1x5 = models.SmallIntegerField()

    first_kills = models.SmallIntegerField()
    first_deaths = models.SmallIntegerField()

    utility_damage = models.SmallIntegerField()
    enemy_flashed = models.SmallIntegerField()
    flash_assists = models.SmallIntegerField()
