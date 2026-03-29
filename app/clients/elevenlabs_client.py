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
from elevenlabs.client import ElevenLabs

APP_ID = "SeniorCapstone_Anki"

class ElevenLabsClient:
    ALLOWED_VOICES = {
        "U9jmr7kY6mMqS39kfA01", "rixsIpPlTphvsJd2mI03", 
        "ZCh4e9eZSUf41K4cmCEL", "7TOiNISMahmVww93K9Xo"
    }

    def __init__(self, username):
        self.username = username
        api_key = keyring.get_password(APP_ID, f"{username}_elevenlabs")
        if not api_key:
            raise ValueError(f"No ElevenLabs key found for {username}")
        self.client = ElevenLabs(api_key=api_key)

    def generate_audio(self, text, output_path, filename, voice_id):
        if voice_id not in self.ALLOWED_VOICES:
            raise ValueError("Unauthorized voice ID")
        if voice_id is None:
            voice_id = "U9jmr7kY6mMqS39kfA01"  # default voice

        audio_generator = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_flash_v2_5",
            output_format="mp3_44100_128",
        )

        os.makedirs(output_path, exist_ok=True)
        full_path = os.path.join(output_path, filename)
        save(audio_generator, full_path)
        return full_path