"""
db.py

Single source of truth for database connectivity.

Three things live here:
    engine      — the shared SQLModel engine (connects to SQLite)
    get_session — returns a new database session
    init_db     — creates all tables

Everything that touches the database (blueprints, services, scripts)
imports from here. Do not call create_engine() anywhere else.
"""

from sqlmodel import SQLModel, create_engine, Session

DB_URL = "sqlite:///./data/app.db"

engine = create_engine(DB_URL, echo=True)


def get_session():
    """
    Return a new database session.

    Caller is responsible for committing and closing.

    Usage:
        session = get_session()
        try:
            session.add(some_record)
            session.commit()
        finally:
            session.close()
    """
    return Session(engine)


def init_db():
    """
    Create all tables defined by SQLModel subclasses.

    Models must be imported before calling create_all so that
    SQLModel registers their table definitions in metadata.
    Safe to call multiple times — existing tables are not recreated.
    """
    # These imports look unused, but they're required.
    # SQLModel only knows about a table if the model class has been
    # imported into Python's memory. Without these, create_all
    # silently creates zero tables. Don't remove them.
    import app.models.user           # noqa: F401 – registers "user" table
    import app.models.vocab          # noqa: F401 – registers "vocab" table
    import app.models.review_state   # noqa: F401 – registers "review_state" table
    import app.models.generated_card # noqa: F401 – registers "generated_card" table
    import app.models.review_log     # noqa: F401 – registers "review_log" table

    SQLModel.metadata.create_all(engine)
