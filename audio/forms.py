from django import forms
from .models import AudioFile

class AudioFileForm(forms.ModelForm):
    class Meta:
        model = AudioFile
        fields = ['audio_file', 'language']
        widgets = {
            'audio_file': forms.FileInput(attrs={
                'class': 'd-none',
                'accept': '.mp3,.wav,.m4a'
            }),
            'language': forms.Select(attrs={
                'class': 'form-select language-select',
                'required': True
            })
        }