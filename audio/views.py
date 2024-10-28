from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .forms import AudioFileForm
from django.views.generic import DetailView
from django.utils.html import format_html
from django.utils.safestring import mark_safe
import json
from .models import AudioFile



from django.shortcuts import redirect

@require_http_methods(["GET", "POST"])
def upload_audio(request):
    if request.method == "POST":
        form = AudioFileForm(request.POST, request.FILES)
        if form.is_valid():
            audio_file = form.save()
            print(f"Audio file saved with ID: {audio_file.pk}")
            return JsonResponse({
                'status': 'success',
                'audio_id': audio_file.pk
            })
        else:
            return JsonResponse({
                'status': 'error',
                'errors': form.errors
            }, status=400)
    else:
        form = AudioFileForm()

    return render(request, 'audio/upload_audio.html', {'form': form})






class AudioFileDetailView(DetailView):
    model = AudioFile
    template_name = 'audio/audio_detail.html'
    context_object_name = 'audio_file'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()

        # Add formatted display methods from admin
        context['file_format_display'] = self.file_format_display(obj)
        context['file_size_display'] = self.file_size_display(obj)
        context['formatted_transcription'] = self.formatted_transcription(obj)
        context['audio_player'] = self.audio_player(obj)
        context['duration_display'] = self.duration_display(obj)

        return context

    def file_format_display(self, obj):
        if obj.file_format:
            format_icons = {
                'mp3': '🎵',
                'wav': '🎼',
                'm4a': '🎧'
            }
            return f"{format_icons.get(obj.file_format, '📁')} {obj.file_format.upper()}"
        return '-'

    def file_size_display(self, obj):
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
        return '-'

    def duration_display(self, obj):
        if hasattr(obj, 'duration') and obj.duration:
            minutes = int(obj.duration // 60)
            seconds = int(obj.duration % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return '-'

    def formatted_transcription(self, obj):
        if not obj.transcription:
            return '-'

        try:
            transcript_data = json.loads(obj.transcription)
            formatted_text = []
            current_speaker = None

            for segment in transcript_data:
                timestamp = self.format_timestamp(segment.get('start_time', 0))
                speaker = segment.get('speaker', 'Speaker 1')
                text = segment.get('text', '').strip()

                if speaker != current_speaker:
                    formatted_text.append(
                        f'<div class="transcript-segment">'
                        f'<span class="timestamp">[{timestamp}]</span> '
                        f'<span class="speaker">{speaker}:</span> '
                        f'<span class="text">{text}</span>'
                        f'</div>'
                    )
                else:
                    formatted_text.append(
                        f'<div class="transcript-segment">'
                        f'<span class="timestamp">[{timestamp}]</span> '
                        f'<span class="text">{text}</span>'
                        f'</div>'
                    )
                current_speaker = speaker

            return mark_safe(
                '<div class="transcription-container">' +
                '\n'.join(formatted_text) +
                '</div>'
            )
        except json.JSONDecodeError:
            return mark_safe(f'<div class="transcription-container">{obj.transcription}</div>')

    def format_timestamp(self, milliseconds):
        total_seconds = int(milliseconds / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def audio_player(self, obj):
        if obj.audio_file:
            return format_html(
                '<audio controls class="w-full max-w-xl">'
                '<source src="{}" type="audio/{}">'
                'Your browser does not support the audio element.'
                '</audio>',
                obj.audio_file.url,
                obj.file_format or 'mpeg'
            )
        return '-'