from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.db.models import Count
from .models import AudioFile, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'clickable_audio_count', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at',)
    fields = ('name', 'description', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return self.readonly_fields + ('created_at',)
        return self.readonly_fields

    def clickable_audio_count(self, obj):
        count = obj.audiofile_set.count()
        url = reverse('admin:audio_audiofile_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{} files</a>', url, count)

    clickable_audio_count.short_description = 'Audio Files'
    clickable_audio_count.admin_order_field = 'audio_count'

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.annotate(audio_count=Count('audiofile'))


@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'language', 'category_link', 'file_format_display',
        'file_size_display', 'created_at'
    )
    list_filter = ('language', 'category', 'file_format', 'created_at')
    search_fields = ('title', 'category__name', 'transcription')
    readonly_fields = (
        'file_format', 'file_size', 'transcription',
        'formatted_transcription', 'audio_player', 'duration_display'
    )
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'audio_file', 'language', 'category')
        }),
        ('File Information', {
            'fields': ('file_format', 'file_size'),
        }),
        ('Audio Preview', {
            'fields': ('audio_player',),
        }),
        ('Processing Results', {
            'fields': ('formatted_transcription', 'transcription', 'summary'),
        }),
    )

    def category_link(self, obj):
        if obj.category:
            return format_html(
                '<a href="{}">{}</a>',
                f'/admin/audio/category/{obj.category.id}/change/',
                obj.category.name
            )
        return '-'

    category_link.short_description = 'Category'
    category_link.admin_order_field = 'category__name'

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
            import json
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

    formatted_transcription.short_description = 'Formatted Transcription'

    def format_timestamp(self, milliseconds):
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
            super().save_model(request, obj, form, change)
        else:
            if not change or not form.changed_data:
                super().save_model(request, obj, form, change)
            else:
                changed_fields = set(form.changed_data)
                if 'audio_file' in changed_fields:
                    obj.save()
                else:
                    super().save_model(request, obj, form, change)

    class Media:
        css = {
            'all': ('audio/css/custom.css',)
        }
        js = ('audio/js/transcription.js',)