from typing import Any
from demo_database.models import Player
from social_django.models import UserSocialAuth


class SteamUserBaseMixin:

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            user_social_auf = UserSocialAuth.objects.get(user=self.request.user)
            user_player, _ = Player.objects.get_or_create(pk=user_social_auf.uid)
            contex['steam_player'] = user_player
            contex['steam_user'] = user_social_auf
        return contex
