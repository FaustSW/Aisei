"""
generation_service.py

Planned service for AI-generated review content
(example sentences, translations, and audio).

Intended responsibilities:
- Determine whether generated content is needed for a card.
- Apply regeneration rules (based on success_streak and interval thresholds).
- Construct prompts for LLM generation.
- Call external API clients (gpt_client, elevenlabs_client).
- Validate and normalize responses.
- Persist generated content to the database.
- Return a display-ready content bundle to the calling service.

Status:
- Stub only; generation logic is not yet implemented.
"""


# elevenlabs_client testing
import hashlib
from app.clients.elevenlabs_client import ElevenLabsClient

def handle_audio_generation(username, text, voice_id):
    """
    Coordinates between the application logic and the ElevenLabs transport.
    """
    # 1. Create a unique filename based on a hash of the text 
    # This prevents creating duplicate files for the exact same sentence
    text_hash = hashlib.md5(text.encode()).hexdigest()
    filename = f"{text_hash}.mp3"
    
    # 2. Define the public-facing directory
    output_dir = "app/static/audio/generated"
    
    # 3. Initialize the client (which handles Keyring/SDK)
    client = ElevenLabsClient(username)
    
    # 4. Generate the file
    client.generate_audio(
        text=text,
        output_path=output_dir,
        filename=filename,
        voice_id=voice_id
    )
    
    # 5. Return the URL path that the browser can actually use
    return f"/static/audio/generated/{filename}"