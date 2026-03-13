"""
Models Package

This package defines the database schema for the application.

Each model file represents one core entity stored in the database.
Models describe the shape of the data: fields/columns, relationships,
and constraints.

How to think about these entities:
- Vocab: the shared, seeded vocabulary dataset (global content).
- ReviewState: a user-specific scheduling state for a vocab item (SM-2 fields + counters).
- GeneratedCard: a generated sentence/translation/audio bundle attached to a ReviewState.
- User: account identity and authentication fields.
- ReviewLog: append-only event history for reviews (used by stats, not by the scheduler).

Models are used by the service layer to store and retrieve application state.
They do not implement application workflows themselves.
"""
