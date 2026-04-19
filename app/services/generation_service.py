"""
generation_service.py

Owns AI-generated review content creation
(example sentences, translations, and audio).

Current responsibilities:
- Generate initial sentence/translation content for a vocab item.
- Create and persist a GeneratedCard for a ReviewState when needed.
- Provide ElevenLabs audio generation for on-card playback.

Later responsibilities:
- Regeneration rules based on success_streak / interval thresholds
- Validation refinement / retry logic
- Optional TTS generation during card creation
"""

from __future__ import annotations

import hashlib
import json
from typing import Optional

from sqlmodel import select

from app.clients.elevenlabs_client import ElevenLabsClient
from app.clients.gpt_client import GPTClient
from app.models.generated_card import GeneratedCard
from app.models.review_state import ReviewState
from app.models.vocab import Vocab

DEFAULT_GENERATION_MODEL = "gpt-5.4-nano"


def _extract_json_object(raw_text: str) -> dict:
    """
    Parse a model response that is expected to contain one JSON object.

    Handles plain JSON and simple fenced-json responses.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Model returned empty output")

    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```JSON")
        cleaned = cleaned.removeprefix("```")
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Model did not return valid JSON: {raw_text}") from e

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object, got: {type(parsed).__name__}")

    return parsed


def generate_card_content_for_vocab(
    username: str,
    term: str,
    english_gloss: str,
    model: str = DEFAULT_GENERATION_MODEL,
) -> dict:
    """
    Generate one natural Spanish sentence and one English translation
    for the provided vocab term.
    """
    client = GPTClient(username)

    system_prompt = """
You generate Spanish flashcard content for a beginner language learner.

Return exactly one valid JSON object with these keys only:
{
  "sentence": "...",
  "translation": "..."
}

Requirements:
- Write one short, natural Spanish sentence using the target vocabulary item in context.
- Conjugated or inflected forms are allowed when appropriate.
- Prefer clear, concrete, everyday sentences that a beginner could understand.
- Use the most natural phrasing a real person would normally say, not an overly literal construction.
- Avoid awkward, overly specific, or unnatural combinations of details.
- Also provide a natural English translation.
- Return JSON only with no extra text.
""".strip()

    user_prompt = f"""
Target Spanish vocab term: {term}
English gloss: {english_gloss}

Generate one short, beginner-friendly, natural Spanish sentence using this vocabulary item in context,
plus a natural English translation.

Return JSON only.
""".strip()

    raw_text = client.generate_text(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model=model,
    )

    data = _extract_json_object(raw_text)

    allowed_keys = {"sentence", "translation"}
    actual_keys = set(data.keys())
    if actual_keys != allowed_keys:
        raise ValueError(
            f"Model returned unexpected keys. Expected {allowed_keys}, got {actual_keys}"
        )

    sentence = str(data.get("sentence", "")).strip()
    translation = str(data.get("translation", "")).strip()

    if not sentence:
        raise ValueError(f"Generated sentence was empty for term {term!r}")

    if not translation:
        raise ValueError(f"Generated translation was empty for term {term!r}")

    if "```" in sentence or "```" in translation:
        raise ValueError("Generated content contained markdown/code fences")
    
    return {
        "sentence": sentence,
        "translation": translation,
    }


def ensure_generated_card_for_review_state(
    db_session,
    username: str,
    review_state: ReviewState,
    model: str = DEFAULT_GENERATION_MODEL,
) -> Optional[GeneratedCard]:
    """
    Ensure a ReviewState has an active GeneratedCard.

    Returns:
        - existing GeneratedCard if one is already linked and found
        - newly created GeneratedCard if generation succeeds
        - None if generation could not be completed
    """
    if review_state.current_generated_card_id is not None:
        existing = db_session.get(GeneratedCard, review_state.current_generated_card_id)
        if existing is not None:
            return existing

    vocab = db_session.get(Vocab, review_state.vocab_id)
    if vocab is None:
        raise ValueError(f"Vocab {review_state.vocab_id} not found")

    existing_generations = db_session.exec(
        select(GeneratedCard).where(GeneratedCard.review_state_id == review_state.id)
    ).all()
    next_generation_number = (
        max((gc.generation_number for gc in existing_generations), default=0) + 1
    )

    content = generate_card_content_for_vocab(
        username=username,
        term=vocab.term,
        english_gloss=vocab.english_gloss,
        model=model,
    )

    generated_card = GeneratedCard(
        review_state_id=review_state.id,
        term_snapshot=vocab.term,
        english_gloss_snapshot=vocab.english_gloss,
        sentence=content["sentence"],
        translation=content["translation"],
        generation_number=next_generation_number,
    )
    db_session.add(generated_card)
    db_session.flush()

    review_state.current_generated_card_id = generated_card.id
    db_session.add(review_state)
    db_session.commit()
    db_session.refresh(generated_card)

    return generated_card


def handle_audio_generation(username: str, text: str, voice_id: str | None):
    """
    Coordinates between application logic and the ElevenLabs transport layer.
    """
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