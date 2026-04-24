"""
ElevenLabs Client

Thin wrapper around the ElevenLabs text-to-speech API.

Responsibilities:
- Send text to the TTS service.
- Return generated audio data or metadata.

It is a transport layer only.
"""

import os
import keyring
from elevenlabs import save
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

APP_ID = "SeniorCapstone_Anki"

DEFAULT_VOICE_ID = "U9jmr7kY6mMqS39kfA01"

VOICE_OPTIONS = [
    {"id": "U9jmr7kY6mMqS39kfA01", "name": "Alex - Deep, Resonant, and Confident"},
    {"id": "rixsIpPlTphvsJd2mI03", "name": "Isabel - Neutral, Balanced, and Calm"},
    {"id": "ZCh4e9eZSUf41K4cmCEL", "name": "Emilio - Warm, Solid, and Convincing"},
    {"id": "7TOiNISMahmVww93K9Xo", "name": "Eva - Soft, Relaxed, and Intimate"},
    {"id": "B8gJV1IhpuegLxdpXFOE", "name": "Kuon - Cheerful, Clearl, and Steady"},
    {"id": "fUjY9K2nAIwlALOwSiwc", "name": "Yui - Warm, Clear, and Natural"},
]


class ElevenLabsClient:
    VOICE_OPTIONS = VOICE_OPTIONS
    DEFAULT_VOICE_ID = DEFAULT_VOICE_ID

    def __init__(self, username):
        self.username = username
        api_key = keyring.get_password(APP_ID, f"{username}_elevenlabs")
        if not api_key:
            raise ValueError(f"No ElevenLabs key found for {username}")
        self.client = ElevenLabs(api_key=api_key)

    def generate_audio(self, text, output_path, filename, voice_id, voice_speed):
        if voice_id is None:
            voice_id = self.DEFAULT_VOICE_ID

        audio_generator = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
            # Optional voice settings
            voice_settings=VoiceSettings(
                speed=voice_speed if voice_speed is not None else 1.0,
                stability=0.5,           # Neutral: Not too expressive, not too monotone
                similarity_boost=0.75,   # Neutral: Standard clarity
                style=0.0,               # Off
                use_speaker_boost=True   # Recommended default for high quality
            )
        )

        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, filename)
        save(audio_generator, full_path)
        return full_path