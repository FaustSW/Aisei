"""
Service Layer Overview

This package contains the core business logic of the application.

Services are responsible for implementing application behavior and workflows.
They are called by blueprints (web layer) and may read/write models (database layer).
They may also call external API clients when needed.

Current services:
    review_service     — end-to-end review loop (card payload, rating, counters, logging)
    queue_service      — card selection, queue classification, simulated time helpers
    scheduler_adapter  — translation layer between ReviewState and the anki-sm-2 library
    auth_service       — login, profile management, user creation/deletion
    stats_service      — progress metrics and session statistics
    generation_service — AI sentence/audio lifecycle (stub, not yet implemented)

Services SHOULD NOT:
- Handle HTTP requests or Flask routing logic (blueprints handle that).
- Render templates or return Flask response objects.
- Contain raw third-party API request code (use clients for that).
- Define database schema (models handle that).
- Implement low-level SM-2 math (use scheduler_adapter).

Architectural Flow:

Blueprints (web layer)
    ↓
Services (business logic)
    ↓
Models (database) + Clients (external APIs)
"""
