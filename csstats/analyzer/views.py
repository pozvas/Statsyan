from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from demoparser.demoparser import get_stats
from pathlib import Path
import json
import os
import tempfile


class ItemView(APIView):
    def get(self, request, *args, **kwargs):
        json_data = get_stats(r'C:\Projects\Python\сsstats\csstats\csstats\files\natus-vincere-vs-imperial-nuke.dem')
        return Response(json.loads(json_data), status=status.HTTP_200_OK)


class DemoFileUploadView(APIView):
    def post(self, request, *args, **kwargs):
        file_obj = request.FILES['file']

        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file_obj.read())
            temp_file_path = temp_file.name

        try:
            # Обрабатываем файл
            json_data = get_stats(temp_file_path)
            return Response(json.loads(json_data), status=status.HTTP_200_OK)
        finally:
            # Удаляем временный файл
            os.remove(temp_file_path)