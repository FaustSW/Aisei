"""
generation_service.py

Manages the lifecycle of AI-generated content for review cards
(example sentences, translations, and audio).

Primary Responsibilities:
- Determine whether generated content is needed for a card.
- Apply regeneration rules (based on success_streak and interval thresholds).
- Construct prompts for LLM generation.
- Call external API clients (gpt_client, elevenlabs_client).
- Validate and normalize responses.
- Persist generated content to the database (caching results).
- Return a display-ready content bundle to the calling service.

Regeneration Policy:
Regeneration rules are currently defined and enforced within this service.
If regeneration logic becomes more complex or reused elsewhere, it may
be extracted into a dedicated service.

It SHOULD NOT:
- Handle HTTP routing or Flask request/response logic (blueprints handle that).
- Implement scheduling math (scheduler_adapter handles that).
- Select which card to review (review_service / queue_service handle that).
- Contain raw API transport logic (clients handle external requests).
- Define database schema (models handle that).

Architectural Position:

Blueprint → review_service → generation_service → clients (GPT/TTS)
                                                → models (GeneratedCard persistence)
"""
