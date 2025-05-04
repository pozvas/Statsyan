from django import forms
from demo_database.models import Player


class PlayerCodeForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ('auth_code', 'last_match_steam_sharecode')
        labels = {
            'auth_code': 'Код аунтефикации',
            'last_match_steam_sharecode': 'Код последнего сыгранного матча',
        }
