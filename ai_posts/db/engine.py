"""
SQLAlchemy engine and session factory.

Uses Neon Postgres via the DATABASE_URL from config.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from ai_posts.config import settings

engine = create_engine(
    settings.database_url,
    echo=False,  # set True for SQL debugging
    pool_pre_ping=True,  # handle Neon cold starts gracefully
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    """Get a new database session. Use as context manager:

    with get_session() as session:
        ...
    """
    return SessionLocal()
