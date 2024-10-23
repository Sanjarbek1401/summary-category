# admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import AudioFile

@admin.register(AudioFile)
class AudioFileAdmin(admin.ModelAdmin):
    list_display = ('title', 'language', 'category', 'file_format_display', 'file_size_display', 'created_at')
    list_filter = ('language', 'category', 'file_format', 'created_at')
    search_fields = ('title', 'category', 'transcription')
    readonly_fields = ('category', 'summary', 'file_format', 'file_size', 'transcription')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'audio_file', 'language')
        }),
        ('File Information', {
            'fields': ('file_format', 'file_size'),
        }),
        ('Processing Results', {
            'fields': ('transcription', 'summary', 'category'),
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
            # Convert bytes to appropriate unit
            size = obj.file_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
        return '-'
    file_size_display.short_description = 'Size'

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