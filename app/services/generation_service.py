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