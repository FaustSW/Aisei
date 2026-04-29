"""
generation_service.py

Owns AI-generated review content creation
(example sentences, translations, and audio).

Current responsibilities:
- Generate initial sentence/translation content for a vocab item.
- Validate generated card content before saving it.
- Retry strict generation when output fails validation or the API call fails.
- Fall back to a relaxed generation pass if strict generation cannot produce usable content.
- Create and persist a GeneratedCard for a ReviewState when needed.
- Provide ElevenLabs audio generation for on-card playback.
- Decide whether a card should be marked for regeneration.

Generation behavior:
- Normal generation uses structured JSON output plus stricter validation.
- If all normal attempts fail, relaxed fallback generation runs once.
- Relaxed fallback only requires basic usable structure: sentence + translation.
- If both normal generation and relaxed fallback fail, the caller handles the failure.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from typing import Optional

from sqlmodel import select

from app.clients.elevenlabs_client import ElevenLabsClient
from app.clients.gpt_client import GPTClient
from app.models.generated_card import GeneratedCard
from app.models.review_state import ReviewState
from app.models.vocab import Vocab

DEFAULT_GENERATION_MODEL = "gpt-5.4-nano"
GENERATION_MAX_ATTEMPTS = 3
GENERATION_RETRY_DELAY_SECONDS = 0.75
GENERATION_TEMPERATURE = 0
RELAXED_GENERATION_TEMPERATURE = 0.4
GENERATION_MAX_OUTPUT_TOKENS = 120
AUDIO_MAX_ATTEMPTS = 3
AUDIO_RETRY_DELAY_SECONDS = 0.5
MIN_SENTENCE_WORDS = 4
MAX_SENTENCE_WORDS = 10

CARD_CONTENT_SCHEMA = {
    "type": "json_schema",
    "name": "flashcard_card_content",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "sentence": {
                "type": "string",
                "description": (
                    "One beginner-friendly Spanish sentence using the target term "
                    "in a simple everyday context."
                ),
            },
            "translation": {
                "type": "string",
                "description": (
                    "A direct natural English translation of the Spanish sentence."
                ),
            },
        },
        "required": ["sentence", "translation"],
        "additionalProperties": False,
    },
}

# Regen thresholds for testing. To be changed later.
REGEN_SUCCESS_STREAK_THRESHOLD = 1
REGEN_INTERVAL_THRESHOLD_DAYS = 1


def _retry_with_backoff(
    operation_name: str,
    func,
    *,
    max_attempts: int,
    retry_delay_seconds: float,
):
    """
    Run an operation with a small linear backoff and re-raise the last error.

    This is intentionally local to generation_service so transport clients stay
    thin and all user-facing generation workflows share one retry policy.
    """
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            return func()
        except Exception as e:
            last_error = e
            if attempt == max_attempts:
                break

            sleep_seconds = retry_delay_seconds * attempt
            print(
                f"[generation_service] {operation_name} attempt "
                f"{attempt}/{max_attempts} failed: {e}. Retrying in "
                f"{sleep_seconds:.2f}s"
            )
            time.sleep(sleep_seconds)

    raise RuntimeError(
        f"{operation_name} failed after {max_attempts} attempts: {last_error}"
    ) from last_error


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


def _normalize_for_duplicate_check(text: str) -> str:
    """
    Normalize text for exact-duplicate comparison.

    Lowercases, strips punctuation, and collapses whitespace.
    """
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s]", "", normalized, flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _build_prior_versions_block(prior_versions: list[dict]) -> str:
    """
    Format all previous GeneratedCard versions into a readable prompt block.
    """
    if not prior_versions:
        return "[]"

    lines = []
    for version in prior_versions:
        sentence = str(version.get("sentence") or "").strip()
        translation = str(version.get("translation") or "").strip()
        generation_number = version.get("generation_number")

        lines.append(
            json.dumps({
                "generation_number": generation_number,
                "sentence": sentence,
                "translation": translation,
            }, ensure_ascii=False)
        )

    return "[\n" + ",\n".join(lines) + "\n]"


def _count_words(text: str) -> int:
    """Return the number of whitespace-delimited words in text."""
    return len(re.findall(r"\S+", text))


def _validate_basic_card_content(data: dict, term: str) -> dict:
    """
    Validate only the minimum structure needed to display a generated card.
    """
    sentence = str(data.get("sentence", "")).strip()
    translation = str(data.get("translation", "")).strip()

    if not sentence:
        raise ValueError(f"Generated sentence was empty for term {term!r}")

    if not translation:
        raise ValueError(f"Generated translation was empty for term {term!r}")

    if "```" in sentence or "```" in translation:
        raise ValueError("Generated content contained markdown/code fences")

    sentence = re.sub(r"\s+", " ", sentence).strip()
    translation = re.sub(r"\s+", " ", translation).strip()

    return {
        "sentence": sentence,
        "translation": translation,
    }


def _validate_strict_card_content(
    data: dict,
    term: str,
    prior_normalized_sentences: set[str],
    prior_normalized_translations: set[str],
) -> dict:
    """
    Validate generated card content against the normal strict generation rules.
    """
    allowed_keys = {"sentence", "translation"}
    actual_keys = set(data.keys())
    if actual_keys != allowed_keys:
        raise ValueError(
            f"Model returned unexpected keys. Expected {allowed_keys}, got {actual_keys}"
        )

    validated = _validate_basic_card_content(data, term)
    sentence = validated["sentence"]
    translation = validated["translation"]

    if "\n" in sentence or "\n" in translation:
        raise ValueError("Generated content must stay on one line")

    sentence_word_count = _count_words(sentence)
    if not MIN_SENTENCE_WORDS <= sentence_word_count <= MAX_SENTENCE_WORDS:
        raise ValueError(
            f"Generated sentence must contain {MIN_SENTENCE_WORDS}-"
            f"{MAX_SENTENCE_WORDS} words, got {sentence_word_count}: {sentence!r}"
        )

    if sentence.count("?") or sentence.count("!") or translation.count("?") or translation.count("!"):
        raise ValueError("Generated content must not include questions or exclamations")

    normalized_new_sentence = _normalize_for_duplicate_check(sentence)
    if normalized_new_sentence in prior_normalized_sentences:
        raise ValueError(
            "Generated sentence duplicated a previous version for term "
            f"{term!r}: {sentence!r}"
        )

    normalized_new_translation = _normalize_for_duplicate_check(translation)
    if normalized_new_translation in prior_normalized_translations:
        raise ValueError(
            "Generated translation duplicated a previous version for term "
            f"{term!r}: {translation!r}"
        )

    return validated


def generate_card_content_for_vocab(
    username: str,
    term: str,
    english_gloss: str,
    model: str = DEFAULT_GENERATION_MODEL,
    prior_versions: list[dict] | None = None,
) -> dict:
    """
    Generate one natural Spanish sentence and one English translation
    for the provided vocab term.

    If prior_versions are provided, the model is instructed not to reuse
    or lightly rephrase previously used content.
    """
    client = GPTClient(username)
    prior_versions = prior_versions or []

    prior_versions_block = _build_prior_versions_block(prior_versions)

    system_prompt = """
You generate Spanish flashcard content for a beginner language learner.

Return one JSON object that matches the provided schema exactly.

Hard rules:
- The Spanish sentence must be exactly one sentence.
- The Spanish sentence must be between 4 and 10 words.
- Use beginner-friendly Spanish in a clear everyday context.
- Conjugated or inflected forms of the target term are allowed when natural.
- Avoid idioms, metaphors, slang, and proper nouns.
- Avoid exclamation marks, questions, lists, dialogue, and multiple clauses.
- The English translation must closely match the Spanish sentence and stay natural.
- Do not include commentary, markdown, or any keys beyond the schema.
""".strip()

    user_prompt = f"""
Target Spanish vocab term: {term}
English gloss: {english_gloss}

Generate one short, beginner-friendly, natural Spanish sentence using this vocabulary item in context,
plus a natural English translation.

Forbidden prior card versions for this vocab item:
{prior_versions_block}

Regeneration constraints:
- Do not reuse or closely paraphrase any prior sentence.
- Do not reuse the same English translation as a prior version.
- Pick a clearly different everyday scenario from prior versions.

Output only the schema-matching JSON object.
""".strip()

    relaxed_system_prompt = """
You generate Spanish flashcard content for a beginner language learner.

Return one JSON object with exactly these fields:
- sentence
- translation

The Spanish sentence should be simple, natural, and beginner-friendly.
The English translation should clearly match the Spanish sentence.
Do not include commentary or markdown.
""".strip()

    relaxed_user_prompt = f"""
Target Spanish vocab term: {term}
English gloss: {english_gloss}

Generate a natural beginner-friendly Spanish example sentence using the target term,
plus a direct English translation.

Previous card versions for this vocab item:
{prior_versions_block}

Prefer a sentence that is different from previous versions, but prioritize producing
a usable natural sentence.

Output only JSON with "sentence" and "translation".
""".strip()

    prior_normalized_sentences = {
        _normalize_for_duplicate_check(str(version.get("sentence") or ""))
        for version in prior_versions
        if version.get("sentence")
    }
    prior_normalized_translations = {
        _normalize_for_duplicate_check(str(version.get("translation") or ""))
        for version in prior_versions
        if version.get("translation")
    }

    def _attempt_strict_generation() -> dict:
        raw_text = client.generate_text(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            text_format=CARD_CONTENT_SCHEMA,
            temperature=GENERATION_TEMPERATURE,
            max_output_tokens=GENERATION_MAX_OUTPUT_TOKENS,
        )

        data = _extract_json_object(raw_text)

        return _validate_strict_card_content(
            data=data,
            term=term,
            prior_normalized_sentences=prior_normalized_sentences,
            prior_normalized_translations=prior_normalized_translations,
        )

    def _attempt_relaxed_generation() -> dict:
        raw_text = client.generate_text(
            prompt=relaxed_user_prompt,
            system_prompt=relaxed_system_prompt,
            model=model,
            text_format=CARD_CONTENT_SCHEMA,
            temperature=RELAXED_GENERATION_TEMPERATURE,
            max_output_tokens=GENERATION_MAX_OUTPUT_TOKENS,
        )

        data = _extract_json_object(raw_text)

        return _validate_basic_card_content(data=data, term=term)

    try:
        return _retry_with_backoff(
            operation_name=f"strict card content generation for term {term!r}",
            func=_attempt_strict_generation,
            max_attempts=GENERATION_MAX_ATTEMPTS,
            retry_delay_seconds=GENERATION_RETRY_DELAY_SECONDS,
        )
    except RuntimeError as strict_error:
        print(
            f"[generation_service] strict generation failed for term {term!r}. "
            f"Trying relaxed fallback. Last strict error: {strict_error}"
        )

        try:
            return _attempt_relaxed_generation()
        except Exception as relaxed_error:
            raise RuntimeError(
                f"relaxed card content fallback failed for term {term!r}: {relaxed_error}"
            ) from relaxed_error


def should_regenerate(review_state: ReviewState) -> bool:
    """
    Return True if this card should be marked for regeneration.

    MVP test rule:
    - success_streak >= 1
    - interval >= 1 day

    Later, tighten this to your real production/demo threshold
    (for example streak >= 3 and interval >= 21).
    """
    if review_state.needs_regeneration:
        return False

    return (
        review_state.success_streak >= REGEN_SUCCESS_STREAK_THRESHOLD
        and review_state.interval >= REGEN_INTERVAL_THRESHOLD_DAYS
    )


def ensure_generated_card_for_review_state(
    db_session,
    username: str,
    review_state: ReviewState,
    model: str = DEFAULT_GENERATION_MODEL,
    force: bool = False,
) -> Optional[GeneratedCard]:
    """
    Ensure a ReviewState has an active GeneratedCard.

    force=False:
        - return existing active GeneratedCard when available
        - otherwise generate one

    force=True:
        - always generate a fresh GeneratedCard
        - update current_generated_card_id to the new generation
        - clear needs_regeneration on success
    """
    if not force and review_state.current_generated_card_id is not None:
        existing = db_session.get(GeneratedCard, review_state.current_generated_card_id)
        if existing is not None:
            return existing

    vocab = db_session.get(Vocab, review_state.vocab_id)
    if vocab is None:
        raise ValueError(f"Vocab {review_state.vocab_id} not found")

    existing_generations = db_session.exec(
        select(GeneratedCard)
        .where(GeneratedCard.review_state_id == review_state.id)
        .order_by(GeneratedCard.generation_number.asc())
    ).all()

    next_generation_number = (
        max((gc.generation_number for gc in existing_generations), default=0) + 1
    )

    prior_versions = [
        {
            "generation_number": gc.generation_number,
            "sentence": gc.sentence,
            "translation": gc.translation,
        }
        for gc in existing_generations
    ]

    content = generate_card_content_for_vocab(
        username=username,
        term=vocab.term,
        english_gloss=vocab.english_gloss,
        model=model,
        prior_versions=prior_versions,
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
    review_state.needs_regeneration = False
    db_session.add(review_state)
    db_session.commit()
    db_session.refresh(generated_card)

    return generated_card


def handle_audio_generation(username: str, text: str, voice_id: str | None):
    """
    Coordinates between application logic and the ElevenLabs transport layer.
    """
    voice_key = voice_id or ElevenLabsClient.DEFAULT_VOICE_ID
    cache_key = f"{voice_key}|{text}"
    text_hash = hashlib.md5(cache_key.encode()).hexdigest()
    filename = f"{voice_key}_{text_hash}.mp3"
    
    # 2. Define the public-facing directory
    output_dir = "app/static/audio/generated"
    
    def _attempt_audio_generation() -> None:
        # Initialize the client inside the retry loop so transient auth/network
        # setup issues get a fresh SDK/client state on the next attempt.
        client = ElevenLabsClient(username)
        client.generate_audio(
            text=text,
            output_path=output_dir,
            filename=filename,
            voice_id=voice_id,
        )

    _retry_with_backoff(
        operation_name=f"audio generation for voice {voice_key!r}",
        func=_attempt_audio_generation,
        max_attempts=AUDIO_MAX_ATTEMPTS,
        retry_delay_seconds=AUDIO_RETRY_DELAY_SECONDS,
    )

    # 5. Return the URL path that the browser can actually use
    return f"/static/audio/generated/{filename}"
