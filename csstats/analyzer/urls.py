from django.urls import path
from .views import ItemView, DemoFileUploadView

urlpatterns = [
    path('item/', ItemView.as_view(), name='item'),
    path('upload/', DemoFileUploadView.as_view(), name='upload'),
]