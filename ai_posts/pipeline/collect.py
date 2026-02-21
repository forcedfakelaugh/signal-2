"""
Collect stage: ingest raw comments from sources into the database.
"""

from sqlalchemy.dialects.postgresql import insert as pg_insert

from ai_posts.db.engine import get_session
from ai_posts.db.models import RawComment
from ai_posts.sources.youtube import collect_video_comments, collect_channel_comments


def collect_youtube_video(video_id: str, max_comments: int = 1000) -> int:
    """Collect comments from a YouTube video. Returns count of new comments."""
    comments = collect_video_comments(video_id, max_comments=max_comments)
    return _save_comments(comments)


def collect_youtube_channel(channel_id: str, max_videos: int = 10) -> int:
    """Collect comments from a YouTube channel. Returns count of new comments."""
    comments = collect_channel_comments(channel_id, max_videos=max_videos)
    return _save_comments(comments)


def _save_comments(comments: list[dict]) -> int:
    """Upsert comments into DB. Returns count of newly inserted."""
    if not comments:
        return 0

    session = get_session()
    try:
        new_count = 0
        for comment in comments:
            # Upsert: skip if source_id already exists
            stmt = pg_insert(RawComment).values(
                source=comment["source"],
                source_id=comment["source_id"],
                text=comment["text"],
                author=comment.get("author"),
                metadata_=comment.get("metadata"),
            ).on_conflict_do_nothing(index_elements=["source_id"])

            result = session.execute(stmt)
            if result.rowcount > 0:
                new_count += 1

        session.commit()
        return new_count
    finally:
        session.close()
