from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from demoparser.demoparser import get_stats
from demo_database.savedb import save_stats
from demo_database.models import ScoreBoard, Demo, Player
from demo_database.serializers import ScoreBoardSerializer, PlayersMatchesSerializer
import json
import os
import tempfile


class DemoFileUploadView(APIView):
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES['file']

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_obj.read())
            temp_file_path = temp_file.name

        try:
            # Обрабатываем файл
            data = get_stats(temp_file_path)
            save_stats(data)
            return Response(json.loads(data.to_json(orient='records')), status=status.HTTP_200_OK)
        finally:
            # Удаляем временный файл
            os.remove(temp_file_path)


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