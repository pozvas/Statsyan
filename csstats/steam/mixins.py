from typing import Any

from django.shortcuts import redirect
from demo_database.models import Player
from social_django.models import UserSocialAuth
from demo_database.savedb import update_players_info
from django.db.models import Q
from django.db.models.query import QuerySet


class SteamUserBaseMixin:

    def get(self, request, *args, **kwargs):
        query = self.request.GET.get("search")
        if query:
            try:
                id = int(query)
            except Exception:
                id = None
            result = Player.objects.filter(
                Q(pk=id) | Q(last_nickname__startswith=query)
            ).first()

            if result is not None:
                return redirect("playerstat:stats", result.pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        contex = super().get_context_data(**kwargs)
        if (
            self.request.user.is_authenticated
            and not self.request.user.is_superuser
        ):
            user_social_auf = UserSocialAuth.objects.get(
                user=self.request.user
            )
            user_player, is_created = Player.objects.get_or_create(
                pk=user_social_auf.uid
            )
            if is_created:
                update_players_info([user_player.pk])
                user_player = Player.objects.get(pk=user_player.pk)

            contex["steam_player"] = user_player
            contex["steam_user"] = user_social_auf
        return contex
