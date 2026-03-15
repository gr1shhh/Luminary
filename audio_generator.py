from google.cloud import texttospeech
from config import VOICE_NAME, SPEAKING_RATE


def init_tts():
    return texttospeech.TextToSpeechClient()


def generate_scene_audio(tts_client, scene_text, filename):
    synthesis_input = texttospeech.SynthesisInput(text=scene_text)

    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name=VOICE_NAME
    )

    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=SPEAKING_RATE
    )

    response = tts_client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    with open(filename, "wb") as out:
        out.write(response.audio_content)