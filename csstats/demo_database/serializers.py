from rest_framework import serializers
from .models import ScoreBoard


class ScoreBoardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreBoard
        fields = '__all__'


class PlayersMatchesSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScoreBoard
        fields = ['kills', 'deaths', 'assists', 'demo_id']