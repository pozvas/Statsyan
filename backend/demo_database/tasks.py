from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
import os
import requests
from steam.steamapi import get_next_match_code_by_player
from demo_database.models import Player, PlayerInDemo, Demo
from django.core.files.storage import default_storage
from demo_database.savedb import save_demo
from django.db.models import Q
from django.db import connection
from decouple import config
import itertools
import bz2
from csstats.settings import ZIP_STTORAGE, UNZIP_STTORAGE
import shutil


BOT_PORT = config("BOT_PORT")


def debug_func():
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE demo_database_player SET last_match_steam_sharecode = 'CSGO-GNKXq-cKp5a-HedPq-n7uaX-85syM' WHERE steamid = 76561198305227842"
        )


def uzip():
    folder = "files/demos/zip"
    folder_to = "files/demos/unzip"

    # Создаем папку для распакованных файлов, если её нет
    os.makedirs(folder_to, exist_ok=True)

    # Перебираем все файлы в исходной папке
    for filename in os.listdir(folder):
        if filename.endswith(".bz2"):
            # Полный путь к архиву
            bz2_path = os.path.join(folder, filename)
            # Имя файла без расширения .bz2
            output_filename = os.path.splitext(filename)[0]
            # Полный путь к распакованному файлу
            output_path = os.path.join(folder_to, output_filename)

            # Получаем время модификации исходного архива
            mod_time = os.path.getmtime(bz2_path)

            # Распаковываем архив
            with bz2.BZ2File(bz2_path, "rb") as f_in:
                with open(output_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # Устанавливаем время модификации для распакованного файла
            os.utime(output_path, (mod_time, mod_time))

            print(f"{filename} распакован (сохранена дата модификации)")

    print("Распаковка завершена!")


def save():
    folder = "files/demos/unzip"
    for filename in os.listdir(folder):
        path = os.path.join(folder, filename)
        try:
            save_demo(path)
        except Exception as e:
            print(f"Ошибка {e} в {filename}")


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
        demo = Demo.objects.filter(sharecode=sharecode)
        if demo.first() is not None:
            return

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

        save_demo(extracted_path, demo_time, sharecode)

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
