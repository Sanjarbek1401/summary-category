from django.db import models
import os
import requests
import time
from dotenv import load_dotenv
from django.core.exceptions import ValidationError
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")
SAMBANOVA_API_KEY = '67b1dd10-0091-41ed-8279-297a5ac47944'
UZBEK_STT_API_KEY = 'B0gZm7U9.pZo5NJKQ1CTrKpAxhjBgE4q8NPnWnY9O'
UZBEK_STT_URL = "https://back.aisha.group/api/v1/stt/post/"


def validate_audio_format(value):
    """Validate audio file format"""
    valid_formats = ['.mp3', '.wav', '.m4a']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in valid_formats:
        raise ValidationError(
            f'Unsupported file format. Allowed formats are: {", ".join(valid_formats)}'
        )
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


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
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    processing_status = models.CharField(max_length=20, default='pending')
    error_message = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title or "No title"

    def format_timestamp(self, milliseconds):
        """Convert milliseconds to minutes:seconds format"""
        try:
            total_seconds = int(milliseconds / 1000)
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        except Exception as e:
            logger.error(f"Error formatting timestamp: {e}")
            return "00:00"

    def clean(self):
        """Additional model validation"""
        super().clean()
        if self.audio_file:
            try:
                ext = os.path.splitext(self.audio_file.name)[1].lower()
                format_map = {'.mp3': 'mp3', '.wav': 'wav', '.m4a': 'm4a'}
                self.file_format = format_map.get(ext)

                if hasattr(self.audio_file, 'size'):
                    self.file_size = self.audio_file.size
            except Exception as e:
                logger.error(f"Error in clean method: {e}")
                raise ValidationError("Error processing audio file")

    def save(self, *args, **kwargs):
        """Override save method to handle audio processing"""
        try:
            self.clean()

            # First save to ensure we have an ID and the file is stored
            super().save(*args, **kwargs)

            # Only process if we have an audio file and need processing
            if self.audio_file and self.processing_status == 'pending':
                self.processing_status = 'processing'
                super().save(*args, **kwargs)

                try:
                    # Get transcription based on language
                    if self.language == 'uz':
                        self.transcription = self.transcribe_audio_uzbek(self.audio_file.path)
                    else:
                        self.transcription = self.transcribe_audio_assemblyai(self.audio_file.path)

                    # Only analyze if we have transcription
                    if self.transcription:
                        result = self.analyze_audio(self.transcription)
                        if result:
                            self.summary = result.get('summary')
                            self.category = result.get('category')
                        self.processing_status = 'completed'
                    else:
                        self.processing_status = 'failed'
                        self.error_message = 'Failed to get transcription'

                except Exception as e:
                    logger.error(f"Error in audio processing: {e}")
                    self.processing_status = 'failed'
                    self.error_message = str(e)

                # Final save with results
                super().save(*args, **kwargs)

        except Exception as e:
            logger.error(f"Error in save method: {e}")
            raise

    def transcribe_audio_uzbek(self, audio_file_path):
        """Transcribe audio using Uzbek STT service"""
        logger.info(f"Starting Uzbek transcription for file: {audio_file_path}")

        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        try:
            headers = {
                'x-api-key': UZBEK_STT_API_KEY,
                'Accept': 'application/json'
            }

            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'audio': ('audio.wav', audio_file, 'audio/wav'),
                    'diarization': (None, 'true')
                }

                logger.info("Sending request to Uzbek STT service")
                response = requests.post(
                    UZBEK_STT_URL,
                    headers=headers,
                    files=files
                )

                logger.info(f"Uzbek STT Response Status: {response.status_code}")
                logger.info(f"Uzbek STT Response: {response.text}")

                if response.status_code != 200:
                    error_msg = f"Uzbek STT error (Status {response.status_code}): {response.text}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                result = response.json()

                # Handle the 'transcript' key format
                if 'transcript' in result:
                    logger.info("Processing transcript from response")
                    return f"[00:00] Speaker 1: {result['transcript']}"
                # Keep the existing format handling as fallback
                elif 'segments' in result:
                    # Handle diarized response
                    formatted_transcript = []
                    current_speaker = None

                    for segment in result['segments']:
                        start_time = segment.get('start', 0)
                        speaker = f"Speaker {segment.get('speaker', '1')}"
                        text = segment.get('text', '')

                        if speaker != current_speaker:
                            formatted_transcript.append(f"\n[{self.format_timestamp(start_time)}] {speaker}:")
                            current_speaker = speaker
                        else:
                            formatted_transcript.append(f"[{self.format_timestamp(start_time)}]")

                        formatted_transcript.append(f" {text}")

                    return " ".join(formatted_transcript)
                elif 'text' in result:
                    # Handle non-diarized response
                    return f"[00:00] Speaker 1: {result['text']}"
                else:
                    error_msg = f"Unexpected response format. Response: {result}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error in Uzbek transcription: {e}")
            raise

    def transcribe_audio_assemblyai(self, audio_file_path):
        """Transcribe audio using AssemblyAI for non-Uzbek languages"""
        logger.info(f"Starting AssemblyAI transcription for file: {audio_file_path}")

        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            raise FileNotFoundError(f"File not found: {audio_file_path}")

        headers = {
            "authorization": ASSEMBLYAI_API_KEY,
            "content-type": "application/json"
        }

        try:
            # Upload audio file
            with open(audio_file_path, 'rb') as audio_file:
                logger.info("Uploading audio to AssemblyAI")
                upload_response = requests.post(
                    "https://api.assemblyai.com/v2/upload",
                    headers=headers,
                    data=audio_file
                )

            if upload_response.status_code != 200:
                error_msg = f"Failed to upload audio: {upload_response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            audio_url = upload_response.json().get('upload_url')
            if not audio_url:
                error_msg = "Upload response does not contain an upload URL"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Request transcription
            transcript_request = {
                "audio_url": audio_url,
                "speaker_labels": True,
                "language_code": self.language
            }

            logger.info("Requesting transcription from AssemblyAI")
            transcript_response = requests.post(
                "https://api.assemblyai.com/v2/transcript",
                json=transcript_request,
                headers=headers
            )

            if transcript_response.status_code != 200:
                error_msg = f"Transcription request failed: {transcript_response.text}"
                logger.error(error_msg)
                raise Exception(error_msg)

            transcript_id = transcript_response.json().get('id')
            if not transcript_id:
                error_msg = "Transcription response does not contain an ID"
                logger.error(error_msg)
                raise Exception(error_msg)

            # Poll for results
            while True:
                logger.info(f"Checking transcription status for ID: {transcript_id}")
                transcript_result = requests.get(
                    f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                    headers=headers
                )

                result = transcript_result.json()
                status = result.get('status')

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

                            if speaker != current_speaker:
                                formatted_transcript.append(f"\n[{self.format_timestamp(start_time)}] {speaker}:")
                                current_speaker = speaker
                            else:
                                formatted_transcript.append(f"[{self.format_timestamp(start_time)}]")

                            formatted_transcript.append(f" {text}")

                        return " ".join(formatted_transcript)
                    else:
                        # Fallback for non-diarized response
                        return f"[00:00] Speaker 1: {result.get('text', '')}"

                elif status == 'failed':
                    error_msg = f"AssemblyAI transcription failed: {result.get('error', 'Unknown error')}"
                    logger.error(error_msg)
                    raise Exception(error_msg)

                time.sleep(5)

        except Exception as e:
            logger.error(f"Error in AssemblyAI transcription: {e}")
            raise

    def analyze_audio(self, transcription):
        """Analyze transcribed text using SambaNova AI"""
        logger.info("Starting audio analysis")

        if not transcription:
            error_msg = "No transcription provided for analysis"
            logger.error(error_msg)
            raise ValueError(error_msg)

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

        # Default responses for errors
        default_responses = {
            'uz': {'category': 'Tasniflanmagan', 'summary': 'Xulosa mavjud emas'},
            'en': {'category': 'Uncategorized', 'summary': 'Summary not available'},
            'ru': {'category': 'Без категории', 'summary': 'Сводка недоступна'},
            'kq': {'category': 'Kategoriyasız', 'summary': 'Juwmaq joq'}
        }

        try:
            # Get appropriate system prompt for the language
            system_prompt = language_prompts.get(self.language, language_prompts['en'])

            # Prepare request data
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

            # Send request to SambaNova API
            logger.info("Sending request to SambaNova API")
            response = requests.post(
                "https://api.sambanova.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {SAMBANOVA_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=data
            )

            # Log response for debugging
            logger.info(f"SambaNova API Response Status: {response.status_code}")
            logger.info(f"SambaNova API Response: {response.text}")

            # Handle response
            response.raise_for_status()
            analysis_result = response.json()
            result_text = analysis_result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()

            if not result_text:
                logger.error("Empty response from SambaNova API")
                return default_responses[self.language]

            # Parse the response
            category = None
            summary = None

            for line in result_text.split('\n'):
                line = line.strip()
                if line.startswith('CATEGORY:'):
                    category = line.replace('CATEGORY:', '').strip()
                elif line.startswith('SUMMARY:'):
                    summary = line.replace('SUMMARY:', '').strip()

            # Return results, falling back to defaults if parsing failed
            return {
                'category': category or default_responses[self.language]['category'],
                'summary': summary or default_responses[self.language]['summary']
            }

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in analysis: {e}")
            return default_responses[self.language]
        except Exception as e:
            logger.error(f"Error in analysis: {e}")
            return default_responses[self.language]

