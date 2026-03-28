from google.cloud import texttospeech
from google.cloud import speech
from config import VOICE_NAME, SPEAKING_RATE
import base64


def init_tts():
    return texttospeech.TextToSpeechClient()


def generate_scene_audio(tts_client, scene_text, filename):
    synthesis_input = texttospeech.SynthesisInput(text=scene_text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=VOICE_NAME)
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=SPEAKING_RATE
    )
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(filename, "wb") as out:
        out.write(response.audio_content)


def generate_scene_audio_with_timings(tts_client, scene_text):
    # Step 1: Generate audio as LINEAR16 (WAV) for Speech-to-Text
    synthesis_input = texttospeech.SynthesisInput(text=scene_text)
    voice = texttospeech.VoiceSelectionParams(language_code="en-US", name=VOICE_NAME)

    audio_config_wav = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=SPEAKING_RATE,
        sample_rate_hertz=16000
    )
    response_wav = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config_wav
    )

    # Step 2: Send WAV to Speech-to-Text to get word timestamps
    stt_client = speech.SpeechClient()
    stt_audio = speech.RecognitionAudio(content=response_wav.audio_content)
    stt_config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_word_time_offsets=True,
    )
    stt_response = stt_client.recognize(config=stt_config, audio=stt_audio)

    # Extract word timings
    word_timings = []
    for result in stt_response.results:
        for word_info in result.alternatives[0].words:
            word_timings.append({
                "word": word_info.word,
                "time": round(word_info.start_time.total_seconds(), 3)
            })

    # Step 3: Generate MP3 for actual playback
    audio_config_mp3 = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=SPEAKING_RATE
    )
    response_mp3 = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config_mp3
    )
    audio_b64 = base64.b64encode(response_mp3.audio_content).decode("utf-8")

    # Fallback: if STT returns nothing, estimate timings
    if not word_timings:
        words = scene_text.split()
        time_per_word = 0.4 / SPEAKING_RATE
        word_timings = [
            {"word": w, "time": round(i * time_per_word, 3)}
            for i, w in enumerate(words)
        ]

    return audio_b64, word_timings