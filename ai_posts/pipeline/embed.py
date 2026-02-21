"""
Stage 1: Embed all raw comments that don't have embeddings yet.
"""

from sqlalchemy import select

from ai_posts.db.engine import get_session
from ai_posts.db.models import RawComment
from ai_posts.llm.client import embed
from rich.progress import track


def run(batch_size: int = 100) -> int:
    """Embed all un-embedded comments. Returns count of newly embedded."""
    session = get_session()
    try:
        # Find comments without embeddings
        stmt = select(RawComment).where(RawComment.embedding.is_(None))
        comments = session.execute(stmt).scalars().all()

        if not comments:
            return 0

        total = 0
        for i in range(0, len(comments), batch_size):
            batch = comments[i : i + batch_size]
            texts = [c.text for c in batch]

            embeddings = embed(texts)
            for comment, emb in zip(batch, embeddings):
                comment.embedding = emb

            session.commit()
            total += len(batch)

        return total
    finally:
        session.close()
