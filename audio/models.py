from django.db import models
import os
import requests
import time
from dotenv import load_dotenv
from django.core.exceptions import ValidationError

load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
SAMBANOVA_API_KEY = '67b1dd10-0091-41ed-8279-297a5ac47944'
UZBEK_STT_API_KEY = '9EcuExDk.K5006qdNmz6TJ8XVBFYkW5oab5lAWYHc'
UZBEK_STT_URL = "https://back.aisha.group/api/v1/stt/post/"


def validate_audio_format(value):
    """Validate audio file format"""
    valid_formats = ['.mp3', '.wav', '.m4a']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_formats:
        raise ValidationError(
            f'Unsupported file format. Allowed formats are: {", ".join(valid_formats)}'
        )


class AudioFile(models.Model):
    LANGUAGE_CHOICES = [
        ('uz', 'O\'zbek'),
        ('ru', 'Rus'),
        ('en', 'Ingliz'),
        ('kq', 'Qoraqalpoq'),
    ]

    FORMAT_CHOICES = [
        ('mp3', 'MP3'),
        ('wav', 'WAV'),
        ('m4a', 'M4A'),
    ]

    title = models.CharField(max_length=255, null=True, blank=True)
    audio_file = models.FileField(
        upload_to='audios/',
        null=True,
        blank=True,
        validators=[validate_audio_format]
    )
    file_format = models.CharField(
        max_length=3,
        choices=FORMAT_CHOICES,
        null=True,
        blank=True
    )
    language = models.CharField(choices=LANGUAGE_CHOICES, max_length=2)
    transcription = models.TextField(null=True, blank=True)
    summary = models.TextField(null=True, blank=True)
    category = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return self.title or "No title"

    def format_timestamp(self, milliseconds):
        """Convert milliseconds to minutes:seconds format"""
        total_seconds = int(milliseconds / 1000)
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes:02d}:{seconds:02d}"

    def clean(self):
        """Additional model validation"""
        super().clean()
        if self.audio_file:
            ext = os.path.splitext(self.audio_file.name)[1].lower()
            format_map = {'.mp3': 'mp3', '.wav': 'wav', '.m4a': 'm4a'}
            self.file_format = format_map.get(ext)

            if hasattr(self.audio_file, 'size'):
                self.file_size = self.audio_file.size

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        if self.audio_file and not self.category:
            if self.language == 'uz':
                self.transcription = self.transcribe_audio_uzbek(self.audio_file.path)
            else:
                self.transcription = self.transcribe_audio_assemblyai(self.audio_file.path)

            result = self.analyze_audio(self.transcription)
            self.summary = result['summary']
            self.category = result['category']
            super().save(*args, **kwargs)

    def transcribe_audio_uzbek(self, audio_file_path):
        """
        Transcribe audio using Uzbek STT service
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        try:
            headers = {
                'Authorization': f'Bearer {UZBEK_STT_API_KEY}',
                'Accept': 'application/json'
            }

            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'audio': ('audio.wav', audio_file, 'audio/wav'),
                    'diarization': (None, 'true')  # Enable speaker diarization
                }

                response = requests.post(
                    UZBEK_STT_URL,
                    headers=headers,
                    files=files
                )

                print(f"Uzbek STT Response Status Code: {response.status_code}")
                print(f"Uzbek STT Response Text: {response.text}")

                if response.status_code != 200:
                    raise Exception(f"Uzbek STT transcription failed: {response.text}")

                result = response.json()

                # Handle response with speaker diarization
                segments = result.get('segments', [])
                if segments:
                    formatted_transcript = []
                    current_speaker = None

                    for segment in segments:
                        start_time = segment.get('start', 0)
                        speaker = f"Speaker {segment.get('speaker', '1')}"
                        text = segment.get('text', '')

                        # Only add speaker label if it changes
                        if speaker != current_speaker:
                            formatted_transcript.append(f"\n[{self.format_timestamp(start_time)}] {speaker}:")
                            current_speaker = speaker
                        else:
                            formatted_transcript.append(f"[{self.format_timestamp(start_time)}]")

                        formatted_transcript.append(f" {text}")

                    return " ".join(formatted_transcript)
                else:
                    # Fallback for non-diarized response
                    text = result.get('text', '')
                    return f"[00:00] Speaker 1: {text}"

        except Exception as e:
            print(f"Error in Uzbek transcription: {str(e)}")
            raise

    def transcribe_audio_assemblyai(self, audio_file_path):
        """
        Transcribe audio using AssemblyAI for non-Uzbek languages
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }

        with open(audio_file_path, 'rb') as audio_file:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=audio_file
            )

        if upload_response.status_code != 200:
            raise Exception(f"Failed to upload audio: {upload_response.text}")

        audio_url = upload_response.json().get('upload_url')
        if not audio_url:
            raise Exception("Upload response does not contain an upload URL.")

        transcript_request = {
            "audio_url": audio_url,
            "speaker_labels": True,
            "language_code": self.language
        }

        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            json=transcript_request,
            headers=headers
        )

        if transcript_response.status_code != 200:
            raise Exception(f"Transcription request failed: {transcript_response.text}")

        transcript_id = transcript_response.json().get('id')
        if not transcript_id:
            raise Exception("Transcription response does not contain an ID.")

        while True:
            transcript_result = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers
            )
            result = transcript_result.json()
            status = result['status']

            if status == 'completed':
                # Process utterances with speaker labels
                utterances = result.get('utterances', [])
                if utterances:
                    formatted_transcript = []
                    current_speaker = None

                    for utterance in utterances:
                        start_time = utterance.get('start', 0)
                        speaker = f"Speaker {utterance.get('speaker', '1')}"
                        text = utterance.get('text', '')

                        # Only add speaker label if it changes
                        if speaker != current_speaker:
                            formatted_transcript.append(f"\n[{self.format_timestamp(start_time)}] {speaker}:")
                            current_speaker = speaker
                        else:
                            formatted_transcript.append(f"[{self.format_timestamp(start_time)}]")

                        formatted_transcript.append(f" {text}")

                    return " ".join(formatted_transcript)
                else:
                    # Fallback for non-diarized response
                    return f"[00:00] Speaker 1: {result['text']}"

            elif status == 'failed':
                raise Exception("Transcription failed.")

            time.sleep(5)

    def analyze_audio(self, transcription):
        """
        Analyze transcribed text using SambaNova AI with language-specific responses
        """
        api_url = "https://api.sambanova.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
            "Content-Type": "application/json",
        }

        # Language-specific system prompts
        language_prompts = {
            'uz': """Siz matn mazmunini tahlil qilib beradigan AI yordamchisisiz. Quyidagilarni taqdim eting:
            1. Mazmunning asosiy mavzusini yoki g'oyasini eng yaxshi tavsiflaydigan aniq kategoriya.
            2. Mazmunning qisqacha xulosasi.

            Javobingizni aynan shu formatda bering:
            CATEGORY: [siz aniqlagan kategoriya]
            SUMMARY: [mazmun xulosasi]""",

            'en': """You are an AI assistant that analyzes text content and provides:
            1. A specific category that best describes the content's main topic or theme.
            2. A brief summary of the content.

            Please provide your response in English using this exact format:
            CATEGORY: [your determined category]
            SUMMARY: [your summary of the content]""",

            'ru': """Вы - ИИ-ассистент, который анализирует текстовый контент и предоставляет:
            1. Конкретную категорию, которая лучше всего описывает основную тему или идею контента.
            2. Краткое содержание контента.

            Предоставьте ответ на русском языке в точном формате:
            CATEGORY: [определенная вами категория]
            SUMMARY: [краткое содержание]""",

            'kq': """Siz tekst mazmunın talqılaw ushin járdem beretuǵın AI assistentisiz. Tómendegilerdi keltiriń:
            1. Mazmunnıń tiykarǵı temasın yamasa ideyasın eń jaqsı súwretleytuǵın kategoriya.
            2. Mazmunnıń qısqasha juwmaǵı.

            Juwabıńızdı usı formatta beriń:
            CATEGORY: [siz anıqlaǵan kategoriya]
            SUMMARY: [mazmun juwmaǵı]"""
        }

        # Default to English if language not found
        system_prompt = language_prompts.get(self.language, language_prompts['en'])

        # Default responses for errors
        default_responses = {
            'uz': {'category': 'Tasniflanmagan', 'summary': 'Xulosa mavjud emas'},
            'en': {'category': 'Uncategorized', 'summary': 'Summary not available'},
            'ru': {'category': 'Без категории', 'summary': 'Сводка недоступна'},
            'kq': {'category': 'Kategoriyasız', 'summary': 'Juwmaq joq'}
        }

        data = {
            "model": "Meta-Llama-3.1-8B-Instruct",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",
                 "content": f"Please analyze this text and determine its category and provide a summary: {transcription}"}
            ],
            "temperature": 0.7,
            "top_p": 0.9
        }

        try:
            response = requests.post(api_url, headers=headers, json=data)
            response.raise_for_status()

            analysis_result = response.json()
            result_text = analysis_result.get('choices')[0]['message']['content'].strip()

            lines = result_text.split('\n')
            category = None
            summary = None

            for line in lines:
                if line.startswith('CATEGORY:'):
                    category = line.replace('CATEGORY:', '').strip()
                elif line.startswith('SUMMARY:'):
                    summary = line.replace('SUMMARY:', '').strip()

            return {
                'category': category or default_responses[self.language]['category'],
                'summary': summary or default_responses[self.language]['summary']
            }

        except Exception as e:
            print(f"Error in analysis: {e}")
            error_messages = {
                'uz': f"Tahlil qilishda xatolik: {str(e)}",
                'en': f"Error analyzing content: {str(e)}",
                'ru': f"Ошибка при анализе: {str(e)}",
                'kq': f"Talqılaw waqtında qátelik: {str(e)}"
            }
            return {
                'category': default_responses[self.language]['category'],
                'summary': error_messages.get(self.language, error_messages['en'])
            }



