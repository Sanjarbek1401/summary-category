from django.urls import path
from .views import upload_audio,AudioFileDetailView

app_name = 'audio'

urlpatterns = [
    path('', upload_audio, name='upload_audio'),
    path('audio_detail/<int:pk>/', AudioFileDetailView.as_view(), name='audio_detail'),
]
