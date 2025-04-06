from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.shortcuts import redirect
from .mixins import SteamUserBaseMixin


class Main(SteamUserBaseMixin, TemplateView):
    template_name = 'base.html'


def logout_view(request):
    logout(request)
    return redirect('home')
