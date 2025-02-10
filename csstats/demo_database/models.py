from django.db import models


class Player(models.Model):
    steamid = models.CharField(primary_key=True, max_length=20)
    auth_code = models.CharField(max_length=50, null=True, blank=True)
    last_nickname = models.CharField(max_length=32)
    last_avatar = models.CharField(max_length=255)
    date_check = models.DateTimeField(auto_now_add=True)


class Side(models.Model):
    name = models.CharField(max_length=32)


class Map(models.Model):
    name = models.CharField(max_length=32)


class MatchType(models.Model):
    code = models.IntegerField()
    name = models.CharField(max_length=32)
    is_elo = models.BooleanField(default=False)


class WinReason(models.Model):
    code = models.IntegerField()
    name = models.CharField(max_length=32)


class BuyType(models.Model):
    name = models.CharField(max_length=32)
    equipment_value_from = models.IntegerField()
    equipment_value_to = models.IntegerField()
    is_pistol = models.BooleanField(default=False)


class Demo(models.Model):
    hash_id = models.CharField(max_length=64, unique=True)
    sharecode = models.CharField(max_length=50, null=True, blank=True)
    data_played = models.DateTimeField(null=True, blank=True)
    win_team = models.CharField(max_length=32, null=True, blank=True)
    score_win = models.SmallIntegerField()
    score_lose = models.SmallIntegerField()
    map_id = models.ForeignKey(Map, on_delete=models.DO_NOTHING)
    match_type_id = models.ForeignKey(MatchType, on_delete=models.DO_NOTHING)


class Round(models.Model):
    demo_id = models.ForeignKey(Demo, on_delete=models.DO_NOTHING)
    round_number = models.SmallIntegerField()
    win_side_id = models.ForeignKey(Side, on_delete=models.DO_NOTHING)
    win_team = models.CharField(max_length=32)
    win_reason_id = models.ForeignKey(WinReason, on_delete=models.DO_NOTHING)
    ct_buy_type_id = models.ForeignKey(BuyType, on_delete=models.DO_NOTHING, related_name='t_buy_type')
    t_buy_type_id = models.ForeignKey(BuyType, on_delete=models.DO_NOTHING, related_name='ct_buy_type')


class MMRank(models.Model):
    code = models.IntegerField()
    name = models.CharField(max_length=32)


class PlayerInDemo(models.Model):
    player_id = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    demo_id = models.ForeignKey(Demo, on_delete=models.DO_NOTHING)
    team = models.CharField(max_length=20)
    crosshair_code = models.CharField(max_length=40)
    elo_old = models.IntegerField(null=True, blank=True)
    elo_new = models.IntegerField(null=True, blank=True)
    rang_id = models.ForeignKey(MMRank, on_delete=models.DO_NOTHING, null=True, blank=True)


class ScoreBoard(models.Model):
    player_in_demo_id = models.ForeignKey(PlayerInDemo, on_delete=models.DO_NOTHING)
    side_id = models.ForeignKey(Side, on_delete=models.DO_NOTHING)

    buy_type_id = models.ForeignKey(BuyType, on_delete=models.DO_NOTHING, related_name='buy_type')
    enemy_buy_type_id = models.ForeignKey(BuyType, on_delete=models.DO_NOTHING, related_name='emnemy_buy_type')

    rounds = models.IntegerField()

    kills = models.SmallIntegerField()
    assists = models.SmallIntegerField()
    deaths = models.SmallIntegerField()

    damage = models.IntegerField()
    kast_rounds = models.IntegerField()

    win_clutches_1x1 = models.SmallIntegerField()
    win_clutches_1x2 = models.SmallIntegerField()
    win_clutches_1x3 = models.SmallIntegerField()
    win_clutches_1x4 = models.SmallIntegerField()
    win_clutches_1x5 = models.SmallIntegerField()

    loss_clutches_1x1 = models.SmallIntegerField()
    loss_clutches_1x2 = models.SmallIntegerField()
    loss_clutches_1x3 = models.SmallIntegerField()
    loss_clutches_1x4 = models.SmallIntegerField()
    loss_clutches_1x5 = models.SmallIntegerField()

    kills_1 = models.SmallIntegerField()
    kills_2 = models.SmallIntegerField()
    kills_3 = models.SmallIntegerField()
    kills_4 = models.SmallIntegerField()
    kills_5 = models.SmallIntegerField()

    first_kills = models.SmallIntegerField()
    first_deaths = models.SmallIntegerField()

    utility_damage = models.SmallIntegerField()
    enemy_flashed = models.SmallIntegerField()
    flash_assists = models.SmallIntegerField()

    impact = models.FloatField()
    rating = models.FloatField()


class Duels(models.Model):
    demo_id = models.ForeignKey(Demo, on_delete=models.DO_NOTHING)
    attacker_player_id = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='attacker')
    victim_player_id = models.ForeignKey(Player, on_delete=models.DO_NOTHING, related_name='victim')
    kills = models.IntegerField()
    open_kills = models.IntegerField()


class WeaponType(models.Model):
    name = models.CharField(max_length=32)


class Weapon(models.Model):
    name = models.CharField(max_length=32)
    weapon_type_id = models.ForeignKey(WeaponType, on_delete=models.DO_NOTHING, null=True, blank=True)


class HitGroup(models.Model):
    name = models.CharField(max_length=32)


class PlayerWeaponStat(models.Model):
    demo_id = models.ForeignKey(Demo, on_delete=models.DO_NOTHING)
    player_id = models.ForeignKey(Player, on_delete=models.DO_NOTHING)
    side_id = models.ForeignKey(Side, on_delete=models.DO_NOTHING)
    weapon_id = models.ForeignKey(Weapon, on_delete=models.DO_NOTHING)
    fires_count = models.IntegerField()


class PlayerHitgroupStat(models.Model):
    player_weapon_stat_id = models.ForeignKey(PlayerWeaponStat, on_delete=models.DO_NOTHING)
    hit_group_id = models.ForeignKey(HitGroup, on_delete=models.DO_NOTHING)
    damage = models.IntegerField()
    hits = models.IntegerField()
    kills = models.IntegerField()
