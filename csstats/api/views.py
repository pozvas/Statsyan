from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework import status
from demoparser.demoparser import get_stats, watch_demo
from demo_database.savedb import save_demo
from steam.steamapi import get_players_names_and_avatars
from demo_database.models import ScoreBoard, Demo, Player
from demo_database.serializers import ScoreBoardSerializer, PlayersMatchesSerializer
import json
import os
import tempfile
from .models import UploadedFile
from .serializers import UploadedFileSerializer


class DemoFileUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        file_serializer = UploadedFileSerializer(data=request.data)

        if file_serializer.is_valid():
            uploaded_file = file_serializer.save()
            file_path = uploaded_file.file.path

            try:
                demo_id = save_demo(file_path)
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)

                uploaded_file.delete()

            return Response({"demo_id": demo_id}, status=status.HTTP_200_OK)
        else:
            return Response(file_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ScoreBoardDetailView(APIView):
    def get(self, request, demo_id):
        try:
            demo = Demo.objects.get(id=demo_id)
            scoreboards = ScoreBoard.objects.filter(demo=demo)
            steamids = scoreboards.values_list('steamid', flat=True).distinct()
            players_data = get_players_names_and_avatars(steamids)
            serializer = ScoreBoardSerializer(scoreboards, many=True, context={'players_data': players_data})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Demo.DoesNotExist:
            return Response({"error": "Demo not found"}, status=status.HTTP_404_NOT_FOUND)


class PlayerMatchesView(APIView):
    def get(self, request, steamid):
        try:
            player = Player.objects.get(steamid=steamid)
            scoreboards = ScoreBoard.objects.filter(steamid=player, side='all')
            serializer = PlayersMatchesSerializer(scoreboards, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Player.DoesNotExist:
            return Response({"error": "Player not found"}, status=status.HTTP_404_NOT_FOUND)


class WathDemo(APIView):
    def get(self, request):
        response = watch_demo()
        return Response(response, status=status.HTTP_200_OK)