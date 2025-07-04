import requests
from django.core.cache import cache
from decouple import config


API_KEY = config("API_KEY")


def get_players_names_and_avatars(stemaids):
    max_retries = 5
    retries = 0
    while retries < max_retries:
        response = requests.get(
            "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/",
            params={"steamids": ",".join(map(str, stemaids)), "key": API_KEY},
        )
        if response.status_code == 200:
            data = response.json()
            players = data["response"]["players"]
            result = [
                {
                    "personaname": player["personaname"],
                    "avatar": player["avatar"],
                    "steamid": player["steamid"],
                    "avatarfull": player["avatarfull"],
                }
                for player in players
            ]
            return result
        elif response.status_code != 429:
            return None


def get_next_match_code_by_player(code, steamid, steamidkey):
    api_url = "https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1"
    max_retries = 5
    retries = 0
    while retries < max_retries:
        response = requests.get(
            api_url,
            params={
                "key": API_KEY,
                "steamid": steamid,
                "steamidkey": steamidkey,
                "knowncode": code,
            },
            timeout=5,
        )
        if response.status_code == 200:
            return response.json()["result"]["nextcode"]
        elif response.status_code != 429:
            return None
