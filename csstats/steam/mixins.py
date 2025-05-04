from typing import Any
from demo_database.models import Player
from social_django.models import UserSocialAuth
from demo_database.savedb import update_players_info


class SteamUserBaseMixin:

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated and not self.request.user.is_superuser:
            user_social_auf = UserSocialAuth.objects.get(user=self.request.user)
            user_player, is_created = Player.objects.get_or_create(pk=user_social_auf.uid)
            if is_created:
                update_players_info([user_player.pk])
                user_player = Player.objects.get(pk=user_player.pk)

            contex['steam_player'] = user_player
            contex['steam_user'] = user_social_auf
        return contex
