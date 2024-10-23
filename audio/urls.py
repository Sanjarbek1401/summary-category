

from django.urls import path
from .views import upload_audio

app_name = 'audio'

urlpatterns = [
    path('upload_audio/', upload_audio, name='upload_audio'),
]
