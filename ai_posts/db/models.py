"""
Database models — SQLAlchemy ORM with pgvector.

Tables:
  raw_comments  — collected source material
  clusters      — HDBSCAN groupings of comments
  cluster_items — many-to-many: cluster ↔ comment
  insights      — distilled human truths from clusters
  angles        — narrative frames for each insight
  hooks         — opening lines with structured scores
  posts         — final generated posts
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from pgvector.sqlalchemy import Vector

from ai_posts.config import settings

EMBEDDING_DIM = settings.embedding_dimensions


class Base(DeclarativeBase):
    pass


# ── Raw Comments ──────────────────────────────────────────────────────────


class RawComment(Base):
    __tablename__ = "raw_comments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False, index=True)  # youtube, reddit, hn
    source_id = Column(String(255), nullable=True, unique=True)  # dedup key
    text = Column(Text, nullable=False)
    author = Column(String(255), nullable=True)
    metadata_ = Column("metadata", JSON, nullable=True)  # likes, url, etc.
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    collected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cluster_items = relationship("ClusterItem", back_populates="comment")

    __table_args__ = (
        Index("ix_raw_comments_source_id", "source_id"),
    )


# ── Clusters ──────────────────────────────────────────────────────────────


class Cluster(Base):
    __tablename__ = "clusters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(Integer, nullable=False)  # HDBSCAN label
    size = Column(Integer, nullable=False, default=0)
    cross_source_count = Column(Integer, nullable=False, default=0)
    score = Column(Float, nullable=False, default=0.0)
    representative_text = Column(Text, nullable=True)  # human-readable summary
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    items = relationship("ClusterItem", back_populates="cluster")
    insights = relationship("Insight", back_populates="cluster")


class ClusterItem(Base):
    __tablename__ = "cluster_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False)
    comment_id = Column(Integer, ForeignKey("raw_comments.id", ondelete="CASCADE"), nullable=False)

    cluster = relationship("Cluster", back_populates="items")
    comment = relationship("RawComment", back_populates="cluster_items")


# ── Insights ──────────────────────────────────────────────────────────────


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(Integer, ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True)
    text = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    cluster = relationship("Cluster", back_populates="insights")
    angles = relationship("Angle", back_populates="insight")


# ── Angles ────────────────────────────────────────────────────────────────


class Angle(Base):
    __tablename__ = "angles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    insight_id = Column(Integer, ForeignKey("insights.id", ondelete="CASCADE"), nullable=False)
    frame_type = Column(String(50), nullable=False)  # contrarian, story, data, etc.
    text = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    insight = relationship("Insight", back_populates="angles")
    hooks = relationship("Hook", back_populates="angle")


# ── Hooks ─────────────────────────────────────────────────────────────────


class Hook(Base):
    __tablename__ = "hooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    angle_id = Column(Integer, ForeignKey("angles.id", ondelete="CASCADE"), nullable=False)
    text = Column(Text, nullable=False)

    # Structured scoring rubric (each 1-5)
    score_curiosity = Column(Float, nullable=True)
    score_clarity = Column(Float, nullable=True)
    score_specificity = Column(Float, nullable=True)
    score_emotional = Column(Float, nullable=True)
    score_contrarian = Column(Float, nullable=True)
    score_shareability = Column(Float, nullable=True)

    weighted_score = Column(Float, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    angle = relationship("Angle", back_populates="hooks")
    posts = relationship("Post", back_populates="hook")


# ── Posts ──────────────────────────────────────────────────────────────────


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hook_id = Column(Integer, ForeignKey("hooks.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIM), nullable=True)

    # Scores
    predicted_score = Column(Float, nullable=True)  # pipeline ranking score

    # Publishing
    posted = Column(Boolean, default=False, nullable=False)
    posted_at = Column(DateTime(timezone=True), nullable=True)

    # Engagement (filled in by `learn` command later)
    real_likes = Column(Integer, nullable=True)
    real_comments = Column(Integer, nullable=True)
    real_shares = Column(Integer, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    hook = relationship("Hook", back_populates="posts")
