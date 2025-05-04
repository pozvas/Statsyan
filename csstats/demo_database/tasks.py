from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
import os
import requests
from steam.steamapi import get_next_match_code_by_player
from demo_database.models import Player, PlayerInDemo, Demo
from django.core.files.storage import default_storage
from demo_database.savedb import save_demo
from django.db.models import Q
from csstats.settings import REDIS_CLIENT
from django.db import connection
from decouple import config
import itertools
import bz2
from csstats.settings import ZIP_STTORAGE, UNZIP_STTORAGE


BOT_PORT = config("BOT_PORT")


def sql_func(sql):
    with connection.cursor() as cursor:
        cursor.execute(sql)


def debug_func():
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE demo_database_player SET auth_code = '9TCA-NV8HM-LVQE', last_match_steam_sharecode = 'CSGO-GNKXq-cKp5a-HedPq-n7uaX-85syM' WHERE steamid = 76561199467171390"
        )
        cursor.execute(
            "UPDATE demo_database_player SET last_match_steam_sharecode = 'CSGO-GNKXq-cKp5a-HedPq-n7uaX-85syM' WHERE steamid = 76561198305227842"
        )


def get_new_sharecodes(player_id):
    player = Player.objects.get(pk=player_id)
    current_code = player.last_match_steam_sharecode
    new_codes = []
    while True:
        new_code = get_next_match_code_by_player(
            code=current_code, steamid=player.pk, steamidkey=player.auth_code
        )
        if not new_code:
            if current_code is not None:
                player.last_match_steam_sharecode = current_code
                player.save()
            break
        new_codes.append(new_code)
        current_code = new_code

    return new_codes


def process_demo(sharecode):
    try:
        response_from_bot = requests.get(
            f"http://127.0.0.1:{BOT_PORT}/getDemoLink",
            params={"sharecode": sharecode},
        )
        response_from_bot.raise_for_status()
        data = response_from_bot.json()
        demo_url = data["matchData"]["matchUrl"]
        demo_time = datetime.fromtimestamp(data["matchData"]["matchTime"])
        file_name = demo_url.split("/")[-1]
        download_dir = ZIP_STTORAGE

        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, file_name)
        print(file_path)

        response = requests.get(demo_url, stream=True)
        response.raise_for_status()

        with open(file_path, "wb") as file:
            for chunck in response.iter_content(chunk_size=8192):
                file.write(chunck)

        print(f"Файл успешно скачан в {file_path}")

        extracted_dir = UNZIP_STTORAGE
        os.makedirs(extracted_dir, exist_ok=True)

        with open(file_path, "rb") as compressed_file:
            decompressed_data = bz2.decompress(compressed_file.read())

        extracted_path = os.path.join(
            extracted_dir, file_name.replace(".bz2", "")
        )
        with open(extracted_path, "wb") as decompressed_file:
            decompressed_file.write(decompressed_data)

        print(f"Файл распакован в {extracted_path}")

        save_demo(extracted_path, demo_time)

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при скачивании файла: {e}")

    except Exception as e:
        print(f"Ошибка распаковки файла: {e}")

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        if os.path.exists(extracted_path):
            os.remove(extracted_path)


def get_and_analize_new_demos():
    players_ids = Player.objects.filter(
        Q(last_match_steam_sharecode__isnull=False)
        & Q(auth_code__isnull=False)
    ).values_list("pk", flat=True)

    games_codes = []
    with ThreadPoolExecutor(max_workers=4) as executor:
        games_codes = list(executor.map(get_new_sharecodes, players_ids))

    games_codes_set = list(set(itertools.chain.from_iterable(games_codes)))
    print(games_codes_set)

    with ThreadPoolExecutor(max_workers=4) as executor:
        executor.map(process_demo, games_codes_set)


# def get_new_sharecodes(self, player_id):
#     player = Player.objects.get(pk=player_id)
#     current_code = player.last_match_steam_sharecode
#     new_codes = []
#     while True:
#         new_code = get_next_match_code_by_player(
#             code=current_code,
#             steamid=player.pk,
#             steamidkey=player.auth_code
#         )
#         if not new_code:
#             player.last_match_steam_sharecode = current_code
#             player.save()
#             break
#         new_codes.append(new_code)
#         current_code = new_code

#     REDIS_CLIENT.sadd("new_sharecodes", *new_codes)
#     return new_codes

# @shared_task
# def get_new_demos():
#     players_ids = Player.objects.filter(last_match_steam_sharecode__isnull=False).values_list('pk', flat=True)
#     group_result = group(get_new_sharecodes.s(id) for id in players_ids).apply_async()

#     while not group_result.ready():
#         gevent.sleep(1)

#     print(REDIS_CLIENT.smembers("unique_codes"))
