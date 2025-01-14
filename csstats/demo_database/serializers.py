from rest_framework import serializers
from .models import ScoreBoard


class ScoreBoardSerializer(serializers.ModelSerializer):
    personaname = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def player_field_from_contex(self, steamid, field):
        players_data = self.context.get('players_data', {})
        if players_data is None:
            return None

        player = next((player for player in players_data if player["steamid"] == str(steamid)), None)
        if player is None:
            return None

        return player[field]

    def get_personaname(self, obj):
        steamid = obj.steamid.pk
        return self.player_field_from_contex(steamid, 'personaname')

    def get_avatar(self, obj):
        steamid = obj.steamid.pk
        return self.player_field_from_contex(steamid, 'avatar')

    class Meta:
        model = ScoreBoard
        fields = '__all__'


class PlayersMatchesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreBoard
        fields = ['kills', 'deaths', 'assists', 'demo_id']
