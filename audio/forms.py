from django import forms
from .models import AudioFile
from django.core.exceptions import ValidationError
import os


class AudioFileForm(forms.ModelForm):
    class Meta:
        model = AudioFile
        fields = ['title', 'audio_file', 'language']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'language': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['audio_file'].widget.attrs.update({
            'class': 'form-control',
            'accept': 'audio/mp3,audio/wav,audio/x-m4a'
        })
        self.fields['audio_file'].help_text = 'Supported formats: MP3, WAV, M4A'

    def clean_audio_file(self):
        audio_file = self.cleaned_data.get('audio_file')
        if audio_file:
            # Get file extension
            ext = os.path.splitext(audio_file.name)[1].lower()

            # Define allowed extensions and their corresponding MIME types
            allowed_types = {
                '.mp3': 'audio/mpeg',
                '.wav': 'audio/wav',
                '.m4a': 'audio/x-m4a'
            }

            if ext not in allowed_types:
                raise ValidationError(
                    f'Invalid file format. Supported formats are: {", ".join(allowed_types.keys())}'
                )

            # Check file size (e.g., limit to 50MB)
            if audio_file.size > 50 * 1024 * 1024:  # 50MB in bytes
                raise ValidationError('File size cannot exceed 50MB')

            return audio_file