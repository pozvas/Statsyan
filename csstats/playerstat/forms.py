from django import forms
from demo_database.models import Player


class PlayerCodeForm(forms.ModelForm):
    class Meta:
        model = Player
        fields = ('auth_code',)
        labels = {
            'auth_code': 'Код аунтефикации',
        }
