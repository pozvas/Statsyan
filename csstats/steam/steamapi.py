import requests
from django.core.cache import cache
from decouple import config


API_KEY = config('API_KEY')


def get_players_names_and_avatars(stemaids):
    response = requests.get('https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/', params={
            'steamids': ','.join(map(str, stemaids)),
            'key': API_KEY
        })
    if response.status_code == 200:
        data = response.json()
        players = data['response']['players']
        result = [{
            "personaname": player["personaname"],
            "avatar": player["avatar"],
            "steamid": player["steamid"]
        } for player in players]
        return result
    else:
        return None
