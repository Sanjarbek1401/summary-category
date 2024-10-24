from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import AudioFile


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = (
    'title', 'language', 'category', 'file_format_display', 'file_size_display',  'created_at')
    list_filter = ('language', 'category', 'file_format', 'created_at')
    search_fields = ('title', 'category', 'transcription')
    readonly_fields = (
    'category', 'summary', 'file_format', 'file_size', 'transcription', 'formatted_transcription', 'audio_player',
    'duration_display')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'audio_file', 'language')
        }),
        ('File Information', {
            'fields': ('file_format', 'file_size'),
        }),
        ('Audio Preview', {
            'fields': ('audio_player',),
        }),
        ('Processing Results', {
            'fields': ('formatted_transcription', 'transcription', 'summary', 'category'),
        }),
    )

    def file_format_display(self, obj):
        if obj.file_format:
            format_icons = {
                'mp3': '🎵',
                'wav': '🎼',
                'm4a': '🎧'
            }
            return f"{format_icons.get(obj.file_format, '📁')} {obj.file_format.upper()}"
        return '-'

    file_format_display.short_description = 'Format'

    def file_size_display(self, obj):
        if obj.file_size:
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
        return '-'

    file_size_display.short_description = 'Size'

    def duration_display(self, obj):
        if hasattr(obj, 'duration') and obj.duration:
            minutes = int(obj.duration // 60)
            seconds = int(obj.duration % 60)
            return f"{minutes:02d}:{seconds:02d}"
        return '-'

    duration_display.short_description = 'Duration'

    def formatted_transcription(self, obj):
        if not obj.transcription:
            return '-'

        try:
            # Assuming transcription is stored as a JSON string with speaker and timestamp info
            import json
            transcript_data = json.loads(obj.transcription)

            # Format the transcription with speakers and timestamps
            formatted_text = []
            current_speaker = None

            for segment in transcript_data:
                timestamp = self.format_timestamp(segment.get('start_time', 0))
                speaker = segment.get('speaker', 'Speaker 1')
                text = segment.get('text', '').strip()

                # Only show speaker label if it's different from the previous speaker
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
            # Fallback for plain text transcriptions
            return mark_safe(f'<div class="transcription-container">{obj.transcription}</div>')

    formatted_transcription.short_description = 'Formatted Transcription'

    def format_timestamp(self, milliseconds):
        """Convert milliseconds to MM:SS format"""
        total_seconds = int(milliseconds / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def audio_player(self, obj):
        if obj.audio_file:
            return format_html(
                '<audio controls style="width: 100%; max-width: 500px;">'
                '<source src="{}" type="audio/{}">'
                'Your browser does not support the audio element.'
                '</audio>',
                obj.audio_file.url,
                obj.file_format or 'mpeg'
            )
        return '-'

    audio_player.short_description = 'Audio Preview'

    def save_model(self, request, obj, form, change):
        if not obj.pk or (obj.audio_file and not obj.category):
            # New object or new audio file uploaded
            super().save_model(request, obj, form, change)
        else:
            # Existing object with no new audio file
            if not change or not form.changed_data:
                super().save_model(request, obj, form, change)
            else:
                changed_fields = set(form.changed_data)
                # Only process if audio_file was changed
                if 'audio_file' in changed_fields:
                    obj.save()
                else:
                    super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('audio/css/custom.css',)
        }
        js = ('audio/js/transcription.js',)