from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import ScoreBoard, Demo, Player
from .serializers import ScoreBoardSerializer, PlayersMatchesSerializer


class ScoreBoardDetailView(APIView):
    def get(self, request, demo_id):
        try:
            demo = Demo.objects.get(id=demo_id)
            scoreboards = ScoreBoard.objects.filter(demo=demo)
            serializer = ScoreBoardSerializer(scoreboards, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Demo.DoesNotExist:
            return Response({"error": "Demo not found"}, status=status.HTTP_404_NOT_FOUND)


class PlayerMatchesView(APIView):
    def get(self, request, steamid):
        try:
            player = Player.objects.get(steamid=steamid)
            scoreboards = ScoreBoard.objects.filter(player=player, side='all')
            serializer = PlayersMatchesSerializer(scoreboards, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Player.DoesNotExist:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)