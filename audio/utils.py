# import assemblyai as aai
# import time
#
# # Dinamik yorlig'i va tilni qo'llab-quvvatlash bilan AssemblyAI yordamida nutqni matnga aylantirish funktsiyasi
# def assemblyai_speech_to_text(audio_file_path, language):
#     transcriber = aai.Transcriber()
#
#     # Configure the transcription with speaker labels and language
#     config = aai.TranscriptionConfig(speaker_labels=True, language=language)
#
#     # Start transcription with the provided config
#     transcript = transcriber.transcribe(audio_file_path, config=config)
#
#     # Wait for the transcription to complete
#     while transcript.status not in ["completed", "failed"]:
#         time.sleep(5)
#         transcript = transcriber.get_transcript(transcript.id)
#
#     # Check if the transcription was completed successfully
#     if transcript.status == "completed":
#         transcribed_text = ""
#
#         # Format speaker-specific utterances with bullet points and spacing
#         if transcript.utterances:
#             transcribed_text = "\n\n".join([f"• Speaker {utt.speaker}: {utt.text}" for utt in transcript.utterances])
#         else:
#             transcribed_text = transcript.text
#
#         return transcribed_text
#     else:
#         return "Transcription failed."
# O'zbek tili uchun o'zimiz yaratgan STT url ni ham qo'shmoqchiman. Agar foydalanuvchi o'zbek tilini tanlasa va o'zbek tilida matn tashlasa shu STT url bo'yicha trascript, summary qilib, categoryga ajratish kerak o'zbek tilida